import os
import requests
from io import BytesIO
from urllib.parse import urljoin

try:
    from PIL import Image
    import imagehash
    IMAGE_SUPPORT = True
except ImportError:
    IMAGE_SUPPORT = False

from backend.db import get_conn

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'images')
SIMILAR_THRESHOLD = 12  # Hamming distance (0=동일, 낮을수록 유사)


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def _download_image(url, save_path, base_url=''):
    if url.startswith('//'):
        url = 'https:' + url
    elif url.startswith('/') or not url.startswith('http'):
        if base_url:
            url = urljoin(base_url, url)
        else:
            return None
    try:
        resp = requests.get(url, timeout=10, verify=False, stream=True)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert('RGB')
        img.save(save_path, 'JPEG', quality=85)
        return img
    except Exception:
        return None


def extract_images(soup, img_selector, base_url, staging_key):
    """
    VOC 페이지에서 이미지를 추출·다운로드해 staging에 저장.
    반환: [{filename, phash, web_path}, ...]
    """
    if not IMAGE_SUPPORT:
        return []

    save_dir = _ensure_dir(os.path.join(IMAGES_DIR, 'staging', str(staging_key)))

    # 이전 staging 파일 정리
    for f in os.listdir(save_dir):
        try:
            os.remove(os.path.join(save_dir, f))
        except Exception:
            pass

    container = soup.select_one(img_selector) if img_selector else soup
    if not container:
        container = soup

    results = []
    for i, tag in enumerate(container.find_all('img')[:8]):
        src = tag.get('src') or tag.get('data-src') or tag.get('data-lazy-src')
        if not src:
            continue

        filename = f'img_{i}.jpg'
        img = _download_image(src, os.path.join(save_dir, filename), base_url)
        if img is None:
            continue

        phash = str(imagehash.phash(img))
        results.append({
            'filename': filename,
            'phash': phash,
            'web_path': f'/images/staging/{staging_key}/{filename}',
        })

    return results


def save_voc_images(voc_id, staging_key, image_data):
    """staging 이미지를 영구 경로로 이동하고 DB에 저장."""
    if not image_data:
        return

    staging_dir = os.path.join(IMAGES_DIR, 'staging', str(staging_key))
    perm_dir = _ensure_dir(os.path.join(IMAGES_DIR, str(voc_id)))

    with get_conn() as conn:
        for item in image_data:
            src = os.path.join(staging_dir, item['filename'])
            dst = os.path.join(perm_dir, item['filename'])
            try:
                if os.path.exists(src):
                    os.replace(src, dst)
            except Exception:
                continue
            conn.execute(
                'INSERT INTO voc_images (voc_id, filename, phash) VALUES (?, ?, ?)',
                (voc_id, item['filename'], item['phash'])
            )


def get_image_paths(voc_id):
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT filename FROM voc_images WHERE voc_id = ?', (voc_id,)
        ).fetchall()
    return [f'/images/{voc_id}/{row["filename"]}' for row in rows]


def find_similar(target_hashes, exclude_voc_id=None):
    """해시 목록을 기준으로 유사 이미지를 가진 과거 VOC 검색."""
    if not IMAGE_SUPPORT or not target_hashes:
        return []

    with get_conn() as conn:
        sql = '''
            SELECT vi.voc_id, vi.phash, v.title, v.status, v.voc_number,
                   v.due_date, v.content, a.name as assignee_name
            FROM voc_images vi
            JOIN vocs v ON vi.voc_id = v.id
            LEFT JOIN assignees a ON v.assignee_id = a.id
        '''
        params = []
        if exclude_voc_id:
            sql += ' WHERE vi.voc_id != ?'
            params.append(exclude_voc_id)
        rows = conn.execute(sql, params).fetchall()

    best = {}  # voc_id → {score, data}
    for row in rows:
        try:
            candidate = imagehash.hex_to_hash(row['phash'])
        except Exception:
            continue
        for th in target_hashes:
            try:
                dist = imagehash.hex_to_hash(th) - candidate
                if dist <= SIMILAR_THRESHOLD:
                    vid = row['voc_id']
                    score = SIMILAR_THRESHOLD - dist
                    if vid not in best or best[vid]['score'] < score:
                        best[vid] = {'score': score, 'data': dict(row)}
            except Exception:
                continue

    results = sorted(best.values(), key=lambda x: x['score'], reverse=True)
    return [r['data'] for r in results[:5]]


def support_status():
    return IMAGE_SUPPORT
