import eel
from backend.db import init_db
from backend import voc, assignment, scraper, config_manager, image_search, knowledge, board, category as category_mgr

eel.init('web')
init_db()


# ── VOC ─────────────────────────────────────────────────────────
@eel.expose
def get_vocs(status=None, search=None, assignee_id=None, category=None, date_from=None, date_to=None):
    return voc.get_vocs(status, search, assignee_id, category, date_from, date_to)

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
def get_voc_stats(period_type='monthly'):
    return voc.get_stats(period_type)


# ── 배정 ─────────────────────────────────────────────────────────
@eel.expose
def get_assignees():
    return assignment.get_assignees()

@eel.expose
def add_assignee(name):
    return assignment.add_assignee(name)

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


# ── 유형 관리 ──────────────────────────────────────────────────────
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


if __name__ == '__main__':
    try:
        eel.start('index.html', size=(1440, 900), mode='edge')
    except Exception:
        eel.start('index.html', size=(1440, 900))
