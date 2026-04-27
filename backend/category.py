from backend.db import get_conn

_TABLES = {'categories', 'process_types'}


def _tbl(type_name):
    if type_name not in _TABLES:
        raise ValueError(f'unknown type: {type_name}')
    return type_name


def get_items(type_name):
    tbl = _tbl(type_name)
    with get_conn() as conn:
        rows = conn.execute(f'SELECT * FROM {tbl} ORDER BY sort_order ASC, id ASC').fetchall()
    return [dict(r) for r in rows]


def add_item(type_name, name):
    tbl = _tbl(type_name)
    name = name.strip()
    if not name:
        return {'success': False, 'error': '이름을 입력하세요.'}
    try:
        with get_conn() as conn:
            max_order = conn.execute(f'SELECT COALESCE(MAX(sort_order),0) FROM {tbl}').fetchone()[0]
            conn.execute(f'INSERT INTO {tbl} (name, sort_order) VALUES (?, ?)', (name, max_order + 1))
        return {'success': True}
    except Exception:
        return {'success': False, 'error': '이미 존재하는 항목입니다.'}


def delete_item(type_name, item_id):
    tbl = _tbl(type_name)
    with get_conn() as conn:
        conn.execute(f'DELETE FROM {tbl} WHERE id=?', (item_id,))
    return {'success': True}


def update_order(type_name, order_list):
    tbl = _tbl(type_name)
    with get_conn() as conn:
        for item in order_list:
            conn.execute(f'UPDATE {tbl} SET sort_order=? WHERE id=?',
                         (item['sort_order'], item['id']))
    return {'success': True}


# Backward-compat wrappers used by main.py
def get_categories():
    return get_items('categories')

def add_category(name):
    return add_item('categories', name)

def delete_category(cat_id):
    return delete_item('categories', cat_id)

def update_category_order(order_list):
    return update_order('categories', order_list)
