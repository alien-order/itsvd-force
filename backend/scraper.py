import requests
from bs4 import BeautifulSoup
from backend.config_manager import get_config
from backend import image_search


def fetch_voc(voc_number):
    config = get_config()
    fetch_method = config.get('fetch_method', 'static')
    if fetch_method == 'static' and config.get('dynamic', False):
        fetch_method = 'xpath'

    if fetch_method == 'api_cookie':
        return _fetch_api_cookie(voc_number, config)

    url_pattern = config.get('url_pattern', '').strip()
    if not url_pattern:
        return {'success': False, 'error': 'URL 패턴이 설정되지 않았습니다. 설정 탭에서 입력해주세요.'}
    url = url_pattern.replace('{number}', str(voc_number))

    if fetch_method == 'xpath':
        return _fetch_xpath(url, config, voc_number)
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


def _fetch_xpath(url, config, voc_number):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            'success': False,
            'error': 'playwright가 설치되지 않았습니다.\n터미널에서 실행:\npip install playwright\nplaywright install chromium',
        }

    wait_ms    = int(config.get('xpath_wait_seconds', 3)) * 1000
    xpath_sels = config.get('xpath_selectors', {})

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page()
            page.goto(url, timeout=30000)
            if wait_ms > 0:
                page.wait_for_timeout(wait_ms)

            def extract_xpath(key):
                xp = xpath_sels.get(key, '').strip()
                if not xp:
                    return ''
                try:
                    return (page.locator(f'xpath={xp}').first.text_content() or '').strip()
                except Exception:
                    return ''

            data = {
                'voc_number': extract_xpath('voc_number'),
                'title':      extract_xpath('title'),
                'content':    extract_xpath('content'),
                'requester':  extract_xpath('requester'),
                'due_date':   extract_xpath('due_date'),
                'images':     [],
            }
            browser.close()

        if not any(v for k, v in data.items() if k != 'images'):
            return {'success': False, 'error': '데이터를 찾지 못했습니다. XPath 셀렉터를 확인하세요.'}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'success': False, 'error': f'XPath 스크래핑 실패: {e}'}


def _fetch_api_cookie(voc_number, config):
    api_url = config.get('api_url_pattern', '').strip()
    if not api_url:
        return {'success': False, 'error': 'API URL 패턴이 설정되지 않았습니다.'}

    url     = api_url.replace('{number}', str(voc_number))
    cookies = {c['key']: c['value'] for c in config.get('api_cookies', []) if c.get('key', '').strip()}

    try:
        resp = requests.get(url, cookies=cookies, timeout=15, verify=False)
        resp.raise_for_status()
        json_data = resp.json()
    except requests.RequestException as e:
        return {'success': False, 'error': f'API 요청 실패: {e}'}
    except ValueError as e:
        return {'success': False, 'error': f'JSON 파싱 실패: {e}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

    field_map = config.get('api_field_map', {})
    data      = {'images': []}
    for voc_field, json_path in field_map.items():
        if not (json_path or '').strip():
            continue
        val = json_data
        for key in json_path.strip().split('.'):
            val = val.get(key, '') if isinstance(val, dict) else ''
        data[voc_field] = str(val).strip() if val is not None else ''

    if not any(v for k, v in data.items() if k != 'images'):
        return {'success': False, 'error': 'API 응답에서 데이터를 찾지 못했습니다. 필드 매핑을 확인하세요.'}
    return {'success': True, 'data': data}


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

    img_selector = selectors.get('images', '').strip()
    content_sel  = selectors.get('content', '').strip()
    search_root  = img_selector or content_sel or None
    images       = image_search.extract_images(soup, search_root, base_url, str(voc_number))
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
    config       = get_config()
    fetch_method = config.get('fetch_method', 'static')
    if fetch_method == 'static' and config.get('dynamic', False):
        fetch_method = 'xpath'

    url_pattern = config.get('url_pattern', '').strip()

    if fetch_method == 'api_cookie':
        if not config.get('api_url_pattern', '').strip():
            return {'success': False, 'error': 'API URL 패턴이 설정되지 않았습니다.'}
        if not config.get('api_field_map', {}).get('status', '').strip():
            return {'success': False, 'error': 'status 필드 매핑이 설정되지 않았습니다.'}
    elif fetch_method == 'xpath':
        if not url_pattern:
            return {'success': False, 'error': 'URL 패턴이 설정되지 않았습니다.'}
        if not config.get('xpath_selectors', {}).get('status', '').strip():
            return {'success': False, 'error': 'XPath status 셀렉터가 설정되지 않았습니다.'}
    else:
        if not url_pattern:
            return {'success': False, 'error': 'URL 패턴이 설정되지 않았습니다.'}
        if not config.get('selectors', {}).get('status', '').strip():
            return {'success': False, 'error': '상태 셀렉터가 설정되지 않았습니다. 설정에서 status 셀렉터를 입력하세요.'}

    updated = []
    failed  = []

    for item in voc_list:
        voc_number = item.get('voc_number') or str(item['id'])
        try:
            new_status = None

            if fetch_method == 'api_cookie':
                api_url = config['api_url_pattern'].replace('{number}', str(voc_number))
                cookies = {c['key']: c['value'] for c in config.get('api_cookies', []) if c.get('key', '').strip()}
                resp = requests.get(api_url, cookies=cookies, timeout=15, verify=False)
                resp.raise_for_status()
                json_data = resp.json()
                json_path = config['api_field_map']['status']
                val = json_data
                for key in json_path.strip().split('.'):
                    val = val.get(key, '') if isinstance(val, dict) else ''
                new_status = _map_status(str(val))

            elif fetch_method == 'xpath':
                from playwright.sync_api import sync_playwright
                url     = url_pattern.replace('{number}', str(voc_number))
                wait_ms = int(config.get('xpath_wait_seconds', 3)) * 1000
                xp      = config['xpath_selectors']['status'].strip()
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page    = browser.new_page()
                    page.goto(url, timeout=30000)
                    if wait_ms > 0:
                        page.wait_for_timeout(wait_ms)
                    text = (page.locator(f'xpath={xp}').first.text_content() or '').strip()
                    browser.close()
                new_status = _map_status(text)

            else:
                url  = url_pattern.replace('{number}', str(voc_number))
                resp = requests.get(url, timeout=15, verify=False)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or 'utf-8'
                soup     = BeautifulSoup(resp.text, 'html.parser')
                status_sel = config['selectors']['status']
                el       = soup.select_one(status_sel)
                new_status = _map_status(el.get_text(strip=True)) if el else None

            if new_status and new_status != item['status']:
                updated.append({'id': item['id'], 'voc_number': voc_number,
                                 'old': item['status'], 'new': new_status})
            elif not new_status:
                failed.append(voc_number)

        except Exception:
            failed.append(voc_number)

    return {'success': True, 'updated': updated, 'failed': failed}
