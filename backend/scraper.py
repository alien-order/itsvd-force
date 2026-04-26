import requests
from bs4 import BeautifulSoup
from backend.config_manager import get_config
from backend import image_search


def fetch_voc(voc_number):
    config = get_config()
    url_pattern = config.get('url_pattern', '').strip()

    if not url_pattern:
        return {'success': False, 'error': 'URL 패턴이 설정되지 않았습니다. 설정 탭에서 입력해주세요.'}

    url = url_pattern.replace('{number}', str(voc_number))

    if config.get('dynamic', False):
        return _fetch_dynamic(url, config, voc_number)
    return _fetch_static(url, config, voc_number)


def _fetch_static(url, config, voc_number):
    try:
        resp = requests.get(url, timeout=15, verify=False)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'utf-8'
        return _parse(BeautifulSoup(resp.text, 'html.parser'), config, voc_number, base_url=url)
    except requests.RequestException as e:
        return {'success': False, 'error': f'요청 실패: {e}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _fetch_dynamic(url, config, voc_number):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            'success': False,
            'error': 'playwright가 설치되지 않았습니다.\n터미널에서 실행:\npip install playwright\nplaywright install chromium'
        }
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='networkidle', timeout=30000)
            html = page.content()
            browser.close()
        return _parse(BeautifulSoup(html, 'html.parser'), config, voc_number, base_url=url)
    except Exception as e:
        return {'success': False, 'error': f'동적 페이지 로드 실패: {e}'}


def _parse(soup, config, voc_number, base_url=''):
    selectors = config.get('selectors', {})

    def extract(key):
        sel = selectors.get(key, '').strip()
        if not sel:
            return ''
        el = soup.select_one(sel)
        return el.get_text(strip=True) if el else ''

    data = {
        'voc_number': extract('voc_number'),
        'title':      extract('title'),
        'content':    extract('content'),
        'requester':  extract('requester'),
        'due_date':   extract('due_date'),
    }

    if not any(data.values()):
        return {'success': False, 'error': '데이터를 찾지 못했습니다. 설정 탭에서 CSS 셀렉터를 확인하세요.'}

    # 이미지 추출 (img_selector가 비어있으면 content 영역 전체에서 탐색)
    img_selector = selectors.get('images', '').strip()
    content_sel = selectors.get('content', '').strip()
    search_root = img_selector or content_sel or None

    images = image_search.extract_images(soup, search_root, base_url, str(voc_number))
    data['images'] = images

    return {'success': True, 'data': data}


# ── 상태 동기화 ────────────────────────────────────────────────

_STATUS_KEYWORDS = [
    ('처리완료', 'resolved'),
    ('처리중',   'in_progress'),
    ('처리 중',  'in_progress'),
    ('진행중',   'in_progress'),
    ('진행 중',  'in_progress'),
    ('해결',     'resolved'),
    ('완료',     'resolved'),
    ('종료',     'closed'),
    ('취소',     'closed'),
    ('접수',     'open'),
    ('신규',     'open'),
    ('대기',     'open'),
]


def _map_status(text):
    t = text.strip()
    for keyword, status in _STATUS_KEYWORDS:
        if keyword in t:
            return status
    return None


def sync_statuses(voc_list):
    """
    voc_list: [{id, voc_number, status}, ...]
    status 셀렉터가 설정된 경우에만 각 VOC를 fetch해서 상태를 매핑/반환.
    반환: {updated: [{id, voc_number, old, new}], failed: [voc_number], skipped: int}
    """
    config = get_config()
    url_pattern = config.get('url_pattern', '').strip()
    status_sel   = config.get('selectors', {}).get('status', '').strip()

    if not url_pattern:
        return {'success': False, 'error': 'URL 패턴이 설정되지 않았습니다.'}
    if not status_sel:
        return {'success': False, 'error': '상태 셀렉터가 설정되지 않았습니다. 설정에서 status 셀렉터를 입력하세요.'}

    updated = []
    failed  = []

    for item in voc_list:
        voc_number = item.get('voc_number') or str(item['id'])
        url = url_pattern.replace('{number}', str(voc_number))
        try:
            if config.get('dynamic', False):
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url, wait_until='networkidle', timeout=30000)
                    html = page.content()
                    browser.close()
                soup = BeautifulSoup(html, 'html.parser')
            else:
                resp = requests.get(url, timeout=15, verify=False)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or 'utf-8'
                soup = BeautifulSoup(resp.text, 'html.parser')

            el = soup.select_one(status_sel)
            if not el:
                failed.append(voc_number)
                continue

            new_status = _map_status(el.get_text(strip=True))
            if new_status and new_status != item['status']:
                updated.append({
                    'id': item['id'],
                    'voc_number': voc_number,
                    'old': item['status'],
                    'new': new_status,
                })
        except Exception:
            failed.append(voc_number)

    return {'success': True, 'updated': updated, 'failed': failed}
