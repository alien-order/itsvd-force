from backend.db import get_conn

_PROTECTED = {'category', 'process_type', 'voc_status'}


def get_groups():
    with get_conn() as conn:
        rows = conn.execute('SELECT * FROM type_groups ORDER BY sort_order ASC, id ASC').fetchall()
    return [dict(r) for r in rows]


def add_group(code, label):
    code  = code.strip().lower().replace(' ', '_')
    label = label.strip()
    if not code or not label:
        return {'success': False, 'error': '코드와 이름을 모두 입력하세요.'}
    try:
        with get_conn() as conn:
            max_order = conn.execute('SELECT COALESCE(MAX(sort_order),0) FROM type_groups').fetchone()[0]
            conn.execute('INSERT INTO type_groups (code, label, sort_order) VALUES (?,?,?)', (code, label, max_order + 1))
        return {'success': True}
    except Exception:
        return {'success': False, 'error': '이미 존재하는 코드입니다.'}


def delete_group(group_id):
    with get_conn() as conn:
        row = conn.execute('SELECT code FROM type_groups WHERE id=?', (group_id,)).fetchone()
        if row and row['code'] in _PROTECTED:
            return {'success': False, 'error': '기본 그룹은 삭제할 수 없습니다.'}
        if row:
            conn.execute('DELETE FROM type_items WHERE group_code=?', (row['code'],))
        conn.execute('DELETE FROM type_groups WHERE id=?', (group_id,))
    return {'success': True}


def update_group_order(order_list):
    with get_conn() as conn:
        for item in order_list:
            conn.execute('UPDATE type_groups SET sort_order=? WHERE id=?', (item['sort_order'], item['id']))
    return {'success': True}


def get_items(group_code):
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM type_items WHERE group_code=? ORDER BY sort_order ASC, id ASC',
            (group_code,)
        ).fetchall()
    return [dict(r) for r in rows]


def add_item(group_code, name, value='', parent_id=None):
    name  = name.strip()
    value = (value or '').strip()
    if not name:
        return {'success': False, 'error': '이름을 입력하세요.'}
    parent_id = int(parent_id) if parent_id else None
    try:
        with get_conn() as conn:
            max_order = conn.execute(
                'SELECT COALESCE(MAX(sort_order),0) FROM type_items WHERE group_code=? AND (parent_id IS ? OR parent_id=?)',
                (group_code, parent_id, parent_id)
            ).fetchone()[0]
            conn.execute(
                'INSERT INTO type_items (group_code, name, value, sort_order, parent_id) VALUES (?,?,?,?,?)',
                (group_code, name, value, max_order + 1, parent_id)
            )
        return {'success': True}
    except Exception:
        return {'success': False, 'error': '이미 존재하는 항목입니다.'}


def update_item(item_id, name, value=''):
    name  = name.strip()
    value = (value or '').strip()
    if not name:
        return {'success': False, 'error': '이름을 입력하세요.'}
    with get_conn() as conn:
        conn.execute('UPDATE type_items SET name=?, value=? WHERE id=?', (name, value, item_id))
    return {'success': True}


def delete_item(item_id):
    with get_conn() as conn:
        conn.execute('DELETE FROM type_items WHERE id=?', (item_id,))
    return {'success': True}


def update_item_order(order_list):
    with get_conn() as conn:
        for item in order_list:
            conn.execute('UPDATE type_items SET sort_order=? WHERE id=?', (item['sort_order'], item['id']))
    return {'success': True}
