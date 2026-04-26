import base64
import os
import uuid

from backend.db import get_conn

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'uploads')


def get_posts(search=None, category=None):
    q = '''
        SELECT p.*, COUNT(f.id) as file_count
        FROM board_posts p
        LEFT JOIN board_files f ON f.post_id = p.id
        WHERE 1=1
    '''
    params = []
    if search and search.strip():
        q += ' AND (p.title LIKE ? OR p.content LIKE ?)'
        s = f'%{search.strip()}%'
        params.extend([s, s])
    if category and category != 'all':
        q += ' AND p.category = ?'
        params.append(category)
    q += ' GROUP BY p.id ORDER BY p.created_at DESC'
    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()
    return [dict(r) for r in rows]


def get_post(post_id):
    with get_conn() as conn:
        post = conn.execute('SELECT * FROM board_posts WHERE id = ?', (post_id,)).fetchone()
        if not post:
            return None
        files = conn.execute('SELECT * FROM board_files WHERE post_id = ?', (post_id,)).fetchall()
    result = dict(post)
    result['files'] = [dict(f) for f in files]
    return result


def create_post(data):
    title = data.get('title', '').strip()
    if not title:
        return {'success': False, 'error': '제목을 입력하세요.'}
    with get_conn() as conn:
        cur = conn.execute(
            'INSERT INTO board_posts (title, content, category) VALUES (?, ?, ?)',
            (title, data.get('content', ''), data.get('category', ''))
        )
    return {'success': True, 'id': cur.lastrowid}


def update_post(post_id, data):
    with get_conn() as conn:
        conn.execute(
            "UPDATE board_posts SET title=?, content=?, category=?, updated_at=datetime('now','localtime') WHERE id=?",
            (data.get('title', ''), data.get('content', ''), data.get('category', ''), post_id)
        )
    return {'success': True}


def delete_post(post_id):
    with get_conn() as conn:
        files = conn.execute('SELECT saved_name FROM board_files WHERE post_id = ?', (post_id,)).fetchall()
        for f in files:
            try:
                os.remove(os.path.join(UPLOADS_DIR, f['saved_name']))
            except Exception:
                pass
        conn.execute('DELETE FROM board_files WHERE post_id = ?', (post_id,))
        conn.execute('DELETE FROM board_posts WHERE id = ?', (post_id,))
    return {'success': True}


def upload_file(post_id, filename, b64_data):
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    ext = os.path.splitext(filename)[1]
    saved_name = uuid.uuid4().hex + ext
    file_bytes = base64.b64decode(b64_data)
    with open(os.path.join(UPLOADS_DIR, saved_name), 'wb') as f:
        f.write(file_bytes)
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO board_files (post_id, original_name, saved_name, file_size) VALUES (?, ?, ?, ?)',
            (post_id, filename, saved_name, len(file_bytes))
        )
    return {'success': True, 'path': f'/uploads/{saved_name}', 'original_name': filename}


def delete_file(file_id):
    with get_conn() as conn:
        row = conn.execute('SELECT saved_name FROM board_files WHERE id = ?', (file_id,)).fetchone()
        if row:
            try:
                os.remove(os.path.join(UPLOADS_DIR, row['saved_name']))
            except Exception:
                pass
            conn.execute('DELETE FROM board_files WHERE id = ?', (file_id,))
    return {'success': True}


def get_categories():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM board_posts WHERE category != '' ORDER BY category"
        ).fetchall()
    return [r[0] for r in rows]


def format_size(size):
    if size < 1024:
        return f'{size}B'
    if size < 1024 * 1024:
        return f'{size//1024}KB'
    return f'{size//(1024*1024)}MB'
