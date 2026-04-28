import eel
from backend.db import init_db
from backend import voc, assignment, scraper, config_manager, image_search, knowledge, board, category as category_mgr, type_manager, menu as menu_mgr

eel.init('web')
init_db()


# ── VOC ─────────────────────────────────────────────────────────
@eel.expose
def get_vocs(status=None, search=None, assignee_id=None, category=None, date_from=None, date_to=None, category_parent=None, process_type=None):
    return voc.get_vocs(status, search, assignee_id, category, date_from, date_to, category_parent, process_type)

@eel.expose
def get_years():
    return voc.get_years()

@eel.expose
def get_voc_categories():
    return voc.get_categories()

@eel.expose
def create_voc(data):
    return voc.create_voc(data)

@eel.expose
def update_voc_status(voc_id, status):
    return voc.update_status(voc_id, status)

@eel.expose
def get_similar_vocs(title, content, limit=5):
    return voc.get_similar(title, content, limit)

@eel.expose
def add_voc_note(voc_id, content, note_date='', work_minutes=0):
    return voc.add_note(voc_id, content, note_date, work_minutes)

@eel.expose
def get_voc_notes(voc_id):
    return voc.get_notes(voc_id)

@eel.expose
def get_daily_report():
    return voc.get_daily_report()

@eel.expose
def sync_voc_statuses():
    return voc.sync_statuses()

@eel.expose
def sync_single_voc(voc_id):
    from backend.db import get_conn
    with get_conn() as conn:
        row = conn.execute('SELECT voc_number FROM vocs WHERE id=?', (voc_id,)).fetchone()
    if not row:
        return {'success': False, 'error': 'VOC를 찾을 수 없습니다.'}
    voc_number = row['voc_number'] or str(voc_id)
    result = scraper.fetch_voc(voc_number)
    if not result['success']:
        return result
    return voc.update_from_sync(voc_id, result['data'])

@eel.expose
def get_status_summary(assignee_id=None, date_from=None, date_to=None):
    return voc.get_status_summary(assignee_id, date_from, date_to)

@eel.expose
def get_voc_stats(period_type='monthly', date_from=None, date_to=None):
    return voc.get_stats(period_type, date_from, date_to)

@eel.expose
def get_assignee_stats(date_from=None, date_to=None):
    return voc.get_assignee_stats(date_from, date_to)


# ── 배정 ─────────────────────────────────────────────────────────
@eel.expose
def get_assignees():
    return assignment.get_assignees()

@eel.expose
def add_assignee(name, knox_id='', ip_address=''):
    return assignment.add_assignee(name, knox_id, ip_address)

@eel.expose
def delete_assignee(assignee_id):
    return assignment.delete_assignee(assignee_id)

@eel.expose
def update_assignee(assignee_id, name, knox_id='', ip_address=''):
    return assignment.update_assignee(assignee_id, name, knox_id, ip_address)

@eel.expose
def get_assignee_by_ip(ip):
    return assignment.get_assignee_by_ip(ip)

@eel.expose
def toggle_assignee(assignee_id):
    return assignment.toggle_assignee(assignee_id)

@eel.expose
def get_workload():
    return assignment.get_workload()

@eel.expose
def reassign_voc(voc_id, assignee_id, note='', forced=False):
    return assignment.reassign(voc_id, assignee_id, note, forced)

@eel.expose
def update_turn_order(order_list):
    return assignment.update_turn_order(order_list)

@eel.expose
def get_next_up():
    return assignment.get_next_up()

@eel.expose
def get_assignment_rules():
    return assignment.get_assignment_rules()

@eel.expose
def save_assignment_rule(category, assignee_id, note=''):
    return assignment.save_assignment_rule(category, assignee_id, note)

@eel.expose
def delete_assignment_rule(rule_id):
    return assignment.delete_assignment_rule(rule_id)

@eel.expose
def get_assignment_history(voc_id):
    return assignment.get_history(voc_id)

@eel.expose
def auto_assign_voc(voc_id):
    return assignment.auto_assign_voc(voc_id)

@eel.expose
def get_vacations():
    return assignment.get_vacations()

@eel.expose
def add_vacation(assignee_id, vacation_date, vacation_type):
    return assignment.add_vacation(assignee_id, vacation_date, vacation_type)

@eel.expose
def delete_vacation(vacation_id):
    return assignment.delete_vacation(vacation_id)


# ── 스크래핑 & 설정 ───────────────────────────────────────────────
@eel.expose
def fetch_voc_data(voc_number):
    return scraper.fetch_voc(voc_number)

@eel.expose
def get_config():
    return config_manager.get_config()

@eel.expose
def save_config(data):
    return config_manager.save_config(data)

@eel.expose
def get_voc_columns():
    return config_manager.get_voc_columns()


# ── 이미지 ────────────────────────────────────────────────────────
@eel.expose
def get_similar_by_images(hashes):
    return image_search.find_similar(hashes)

@eel.expose
def get_voc_images(voc_id):
    return image_search.get_image_paths(voc_id)

@eel.expose
def check_image_support():
    return image_search.support_status()


# ── 레퍼런스 (지식베이스) ─────────────────────────────────────────
@eel.expose
def get_knowledge(search=None, category=None, process_type=None):
    return knowledge.get_all(search, category, process_type)

@eel.expose
def get_knowledge_one(kid):
    return knowledge.get_one(kid)

@eel.expose
def create_knowledge(data):
    return knowledge.create(data)

@eel.expose
def update_knowledge(kid, data):
    return knowledge.update(kid, data)

@eel.expose
def delete_knowledge(kid):
    return knowledge.delete(kid)

@eel.expose
def get_knowledge_categories():
    return knowledge.get_categories()

@eel.expose
def link_knowledge_to_voc(knowledge_id, voc_id):
    return knowledge.link_voc(knowledge_id, voc_id)

@eel.expose
def unlink_knowledge_from_voc(knowledge_id, voc_id):
    return knowledge.unlink_voc(knowledge_id, voc_id)

@eel.expose
def get_voc_knowledge(voc_id):
    return knowledge.get_voc_knowledge(voc_id)

@eel.expose
def get_knowledge_vocs(knowledge_id):
    return knowledge.get_knowledge_vocs(knowledge_id)


# ── 공유문서 (게시판) ─────────────────────────────────────────────
@eel.expose
def get_board_posts(search=None, category=None):
    return board.get_posts(search, category)

@eel.expose
def get_board_post(post_id):
    return board.get_post(post_id)

@eel.expose
def create_board_post(data):
    return board.create_post(data)

@eel.expose
def update_board_post(post_id, data):
    return board.update_post(post_id, data)

@eel.expose
def delete_board_post(post_id):
    return board.delete_post(post_id)

@eel.expose
def upload_board_file(post_id, filename, b64_data):
    return board.upload_file(post_id, filename, b64_data)

@eel.expose
def delete_board_file(file_id):
    return board.delete_file(file_id)

@eel.expose
def get_board_categories():
    return board.get_categories()


# ── 유형 관리 (카테고리 & 처리유형 공통) ──────────────────────────────
@eel.expose
def get_category_list():
    return category_mgr.get_categories()

@eel.expose
def add_category(name):
    return category_mgr.add_category(name)

@eel.expose
def delete_category(cat_id):
    return category_mgr.delete_category(cat_id)

@eel.expose
def update_category_order(order_list):
    return category_mgr.update_category_order(order_list)

@eel.expose
def get_process_type_list():
    return category_mgr.get_items('process_types')

@eel.expose
def add_process_type(name):
    return category_mgr.add_item('process_types', name)

@eel.expose
def delete_process_type(item_id):
    return category_mgr.delete_item('process_types', item_id)

@eel.expose
def update_process_type_order(order_list):
    return category_mgr.update_order('process_types', order_list)


# ── 유형 시스템 (type_groups / type_items) ──────────────────────────
@eel.expose
def get_type_groups():
    return type_manager.get_groups()

@eel.expose
def add_type_group(code, label):
    return type_manager.add_group(code, label)

@eel.expose
def delete_type_group(group_id):
    return type_manager.delete_group(group_id)

@eel.expose
def update_type_group_order(order_list):
    return type_manager.update_group_order(order_list)

@eel.expose
def get_type_items(group_code):
    return type_manager.get_items(group_code)

@eel.expose
def add_type_item(group_code, name, value='', parent_id=None):
    return type_manager.add_item(group_code, name, value, parent_id)

@eel.expose
def update_type_item(item_id, name, value=''):
    return type_manager.update_item(item_id, name, value)

@eel.expose
def delete_type_item(item_id):
    return type_manager.delete_item(item_id)

@eel.expose
def update_type_item_order(order_list):
    return type_manager.update_item_order(order_list)


# ── 커스텀 메뉴 ──────────────────────────────────────────────────
@eel.expose
def get_custom_menus():
    return menu_mgr.get_menus()

@eel.expose
def add_custom_menu(label, icon_color='#6366f1', source_type='url', source_value='', section=''):
    return menu_mgr.add_menu(label, icon_color, source_type, source_value, section)

@eel.expose
def update_custom_menu(menu_id, label, icon_color, source_type, source_value, section=''):
    return menu_mgr.update_menu(menu_id, label, icon_color, source_type, source_value, section)

@eel.expose
def delete_custom_menu(menu_id):
    return menu_mgr.delete_menu(menu_id)

@eel.expose
def toggle_custom_menu_active(menu_id):
    return menu_mgr.toggle_menu(menu_id)

@eel.expose
def update_custom_menu_order(order_list):
    return menu_mgr.update_menu_order(order_list)


# ── VOC 배치처리 ─────────────────────────────────────────────
@eel.expose
def parse_voc_numbers_from_excel(filename, b64_data):
    import base64, io, os as _os
    try:
        data = base64.b64decode(b64_data)
        ext  = _os.path.splitext(filename)[1].lower()
        voc_nums = []
        if ext in ('.xlsx', '.xls'):
            try:
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
                ws = wb.active
                for row in ws.iter_rows(values_only=True):
                    if row and row[0] is not None:
                        val = str(row[0]).strip()
                        if val:
                            voc_nums.append(val)
                wb.close()
            except ImportError:
                return {'success': False, 'error': 'openpyxl 미설치. pip install openpyxl 후 재시작하세요.'}
        elif ext == '.csv':
            import csv
            text = data.decode('utf-8-sig', errors='replace')
            for row in csv.reader(io.StringIO(text)):
                if row and row[0].strip():
                    voc_nums.append(row[0].strip())
        else:
            text = data.decode('utf-8-sig', errors='replace')
            for line in text.splitlines():
                val = line.strip().split(',')[0].strip()
                if val:
                    voc_nums.append(val)
        # Remove header if first value has no digits
        if voc_nums and not any(c.isdigit() for c in voc_nums[0]):
            voc_nums = voc_nums[1:]
        return {'success': True, 'voc_numbers': voc_nums}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def batch_upsert_voc(voc_number):
    voc_number = str(voc_number).strip()
    if not voc_number:
        return {'success': False, 'error': '번호 없음', 'action': 'skip'}
    from backend.db import get_conn as _gc
    with _gc() as conn:
        row = conn.execute('SELECT id FROM vocs WHERE voc_number=?', (voc_number,)).fetchone()
    if row:
        result = scraper.fetch_voc(voc_number)
        if not result['success']:
            return {**result, 'action': 'failed'}
        update_result = voc.update_from_sync(row['id'], result['data'])
        return {**update_result, 'action': 'updated', 'voc_number': voc_number}
    else:
        result = scraper.fetch_voc(voc_number)
        if not result['success']:
            return {**result, 'action': 'failed'}
        data = result['data']
        data['voc_number'] = voc_number
        create_result = voc.create_voc(data)
        return {**create_result, 'action': 'created', 'voc_number': voc_number}


if __name__ == '__main__':
    try:
        eel.start('index.html', size=(1440, 900), mode='edge')
    except Exception:
        eel.start('index.html', size=(1440, 900))
