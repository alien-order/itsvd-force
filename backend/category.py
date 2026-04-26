from backend.db import get_conn


def get_categories():
    with get_conn() as conn:
        rows = conn.execute('SELECT * FROM categories ORDER BY sort_order ASC, id ASC').fetchall()
    return [dict(r) for r in rows]


def add_category(name):
    name = name.strip()
    if not name:
        return {'success': False, 'error': '유형명을 입력하세요.'}
    try:
        with get_conn() as conn:
            max_order = conn.execute('SELECT COALESCE(MAX(sort_order),0) FROM categories').fetchone()[0]
            conn.execute('INSERT INTO categories (name, sort_order) VALUES (?, ?)', (name, max_order + 1))
        return {'success': True}
    except Exception:
        return {'success': False, 'error': '이미 존재하는 유형입니다.'}


def delete_category(cat_id):
    with get_conn() as conn:
        conn.execute('DELETE FROM categories WHERE id=?', (cat_id,))
    return {'success': True}


def update_category_order(order_list):
    with get_conn() as conn:
        for item in order_list:
            conn.execute('UPDATE categories SET sort_order=? WHERE id=?',
                         (item['sort_order'], item['id']))
    return {'success': True}
