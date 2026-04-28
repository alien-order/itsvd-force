from backend.db import get_conn


def get_menus():
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM custom_menus ORDER BY sort_order'
        ).fetchall()
    return [dict(r) for r in rows]


def add_menu(label, icon_color='#6366f1', source_type='url', source_value='', section=''):
    label = label.strip()
    if not label:
        return {'success': False, 'error': '이름을 입력하세요.'}
    with get_conn() as conn:
        max_order = conn.execute(
            'SELECT COALESCE(MAX(sort_order),0) FROM custom_menus'
        ).fetchone()[0]
        conn.execute(
            'INSERT INTO custom_menus (label,icon_color,source_type,source_value,section,sort_order) VALUES (?,?,?,?,?,?)',
            (label, icon_color, source_type, source_value.strip(), section.strip(), max_order + 1)
        )
    return {'success': True}


def update_menu(menu_id, label, icon_color, source_type=None, source_value=None, section=None):
    with get_conn() as conn:
        conn.execute(
            'UPDATE custom_menus SET label=?,icon_color=?,source_type=?,source_value=?,section=? WHERE id=?',
            (label.strip(), icon_color, source_type, (source_value or '').strip(), (section or '').strip(), menu_id)
        )
    return {'success': True}


def toggle_menu(menu_id):
    with get_conn() as conn:
        conn.execute(
            'UPDATE custom_menus SET active = CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=?',
            (menu_id,)
        )
    return {'success': True}


def delete_menu(menu_id):
    with get_conn() as conn:
        conn.execute('DELETE FROM custom_menus WHERE id=?', (menu_id,))
    return {'success': True}


def update_menu_order(order_list):
    with get_conn() as conn:
        for item in order_list:
            conn.execute(
                'UPDATE custom_menus SET sort_order=? WHERE id=?',
                (item['sort_order'], item['id'])
            )
    return {'success': True}
