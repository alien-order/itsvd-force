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
def create_voc(data, stages=None):
    return voc.create_voc(data, stages or [])

@eel.expose
def update_voc_status(vocno, status):
    return voc.update_status(vocno, status)

@eel.expose
def get_similar_vocs(title, content, limit=5):
    return voc.get_similar(title, content, limit)

@eel.expose
def add_voc_note(vocno, content, note_date='', work_minutes=0, note_type='answer'):
    return voc.add_note(vocno, content, note_date, work_minutes, note_type)

@eel.expose
def get_voc_notes(vocno, note_type=None):
    return voc.get_notes(vocno, note_type)

@eel.expose
def get_daily_report():
    return voc.get_daily_report()

@eel.expose
def sync_voc_statuses():
    return voc.sync_statuses()

@eel.expose
def sync_single_voc(vocno):
    vocno = str(vocno).strip()
    result = scraper.fetch_voc(vocno)
    if not result['success']:
        return result
    return voc.update_from_sync(vocno, result['data'], result.get('stages'))

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
def update_assignee_avatar(assignee_id, b64_data):
    return assignment.update_avatar(assignee_id, b64_data)

@eel.expose
def toggle_assignee(assignee_id):
    return assignment.toggle_assignee(assignee_id)

@eel.expose
def get_assignee_categories(assignee_id):
    return assignment.get_assignee_categories(assignee_id)

@eel.expose
def set_assignee_categories(assignee_id, category_ids):
    return assignment.set_assignee_categories(assignee_id, category_ids)

@eel.expose
def get_all_assignee_categories():
    return assignment.get_all_assignee_categories()

@eel.expose
def get_workload():
    return assignment.get_workload()

@eel.expose
def reassign_voc(vocno, assignee_id, note='', forced=False):
    return assignment.reassign(vocno, assignee_id, note, forced)

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
def get_assignment_history(vocno):
    return assignment.get_history(vocno)

@eel.expose
def auto_assign_voc(vocno):
    return assignment.auto_assign_voc(vocno)

@eel.expose
def get_vacation_type_config():
    return assignment.get_vacation_type_config()

@eel.expose
def save_vacation_type_config(vacation_type, time_start, time_end, n_rounds, assign_during):
    return assignment.save_vacation_type_config(vacation_type, time_start, time_end, n_rounds, assign_during)

@eel.expose
def get_vacations(year=None, month=None):
    return assignment.get_vacations(year, month)

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
def get_voc_images(vocno):
    return image_search.get_image_paths(vocno)

@eel.expose
def check_image_support():
    return image_search.support_status()


# ── 레퍼런스 (지식베이스) ─────────────────────────────────────────
@eel.expose
def get_knowledge(search=None, category=None, process_type=None, voc_type=None, sub_category=None):
    return knowledge.get_all(search, category, process_type, voc_type, sub_category)

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
def link_knowledge_to_voc(knowledge_id, vocno):
    return knowledge.link_voc(knowledge_id, vocno)

@eel.expose
def unlink_knowledge_from_voc(knowledge_id, vocno):
    return knowledge.unlink_voc(knowledge_id, vocno)

@eel.expose
def get_voc_knowledge(vocno):
    return knowledge.get_voc_knowledge(vocno)

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

@eel.expose
def set_type_item_tab(item_id, show_as_tab):
    return type_manager.set_show_as_tab(item_id, show_as_tab)

@eel.expose
def set_type_item_active(item_id, is_active):
    return type_manager.set_is_active(item_id, is_active)


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
def get_voc_info(vocno):
    return voc.get_voc_info(vocno)

@eel.expose
def get_voc_stages(vocno):
    return voc.get_voc_stages(vocno)

@eel.expose
def batch_upsert_voc(voc_number):
    vocno = str(voc_number).strip()
    if not vocno:
        return {'success': False, 'error': '번호 없음', 'action': 'skip'}
    from backend.db import get_conn as _gc
    with _gc() as conn:
        row = conn.execute('SELECT vocno FROM voc_info WHERE vocno=?', (vocno,)).fetchone()
    if row:
        result = scraper.fetch_voc(vocno)
        if not result['success']:
            return {**result, 'action': 'failed'}
        update_result = voc.update_from_sync(vocno, result['data'], result.get('stages'))
        return {**update_result, 'action': 'updated', 'voc_number': vocno}
    else:
        result = scraper.fetch_voc(vocno)
        if not result['success']:
            return {**result, 'action': 'failed'}
        data   = result['data']
        stages = result.get('stages', [])
        data['voc_number'] = vocno
        create_result = voc.create_voc(data, stages)
        return {**create_result, 'action': 'created', 'voc_number': vocno}


@eel.expose
def create_test_data():
    from backend.db import get_conn as _gc
    import json as _json
    from datetime import datetime as _dt, timedelta as _td
    with _gc() as conn:
        # 실제 설정된 코드로 테스트 데이터 생성
        cats  = [dict(r) for r in conn.execute(
            "SELECT * FROM type_items WHERE group_code='category' AND parent_id IS NULL ORDER BY sort_order LIMIT 6"
        ).fetchall()]
        child_cats = [dict(r) for r in conn.execute(
            "SELECT * FROM type_items WHERE group_code='category' AND parent_id IS NOT NULL ORDER BY sort_order LIMIT 10"
        ).fetchall()]
        statuses = [dict(r) for r in conn.execute(
            "SELECT * FROM type_items WHERE group_code='voc_status' ORDER BY sort_order"
        ).fetchall()]
        proc_types = [dict(r) for r in conn.execute(
            "SELECT * FROM type_items WHERE group_code='process_type' ORDER BY sort_order LIMIT 8"
        ).fetchall()]
        assignees = [dict(r) for r in conn.execute(
            "SELECT * FROM assignees WHERE active=1 ORDER BY turn_order"
        ).fetchall()]

    if not cats or not statuses or not assignees:
        return {'success': False, 'error': '카테고리, 상태, 담당자 설정을 먼저 완료하세요.'}

    import random as _random
    _random.seed(42)

    samples = [
        ('VERS DX 사용자 계정 생성 요청',    'VERS(DX) 시스템에 신규 사용자 계정 생성을 요청합니다. 부서 이동으로 인한 권한 재설정 필요.'),
        ('MRO 데이터 조회 오류 문의',         'MRO2.0 시스템에서 자재 데이터 조회 시 에러 메시지가 표시됩니다. 스크린샷 첨부.'),
        ('구매 신청 결재선 변경 요청',         '구매 신청 시 결재선이 자동으로 잘못 설정되는 문제. 담당 부서 변경 사항 반영 요청.'),
        ('글로벌 마케팅 시스템 접속 불가',     '해외 사용자가 VPN 연결 후에도 시스템 접속이 안 됩니다. IP 허용 목록 확인 필요.'),
        ('IT 인프라 모니터링 데이터 제공 요청','서버 성능 데이터(CPU, 메모리) 주간 리포트 제공 요청합니다.'),
        ('서비스 관련 DB 정보 수정 요청',      '서비스 이력 테이블에서 잘못 입력된 데이터 3건 수정 요청. 상세 내용 본문 참조.'),
        ('경영관리 시스템 가이드 제공',         '신규 입사자 온보딩을 위한 경영관리 시스템 사용 가이드 및 매뉴얼 요청.'),
        ('제조 라인 데이터 등록 처리',          '신규 제조 라인 코드 등록 및 초기 데이터 세팅 요청. 생산팀과 협의 완료됨.'),
        ('공사 시스템 사용자 삭제 요청',        '퇴사자 계정 삭제 요청입니다. 총 2개 계정 처리 요망.'),
        ('개발 환경 설정 안내 요청',            '개발 신규 입사자 로컬 환경 세팅 가이드 요청. Docker, DB 접속 정보 포함 필요.'),
        ('Vietnam MRO 접속 속도 저하',          '베트남 사무소에서 MRO 시스템 접속 속도가 현저히 느립니다. 네트워크 점검 요청.'),
        ('SDC 전용 기능 개선 요청',             '삼성디스플레이 사용자 전용 화면에서 필터 기능이 누락되어 있습니다. 개선 요청.'),
    ]

    today = _dt.now()
    created = 0
    with _gc() as conn:
        for i, (title, content) in enumerate(samples):
            cat    = cats[i % len(cats)]
            status = statuses[i % len(statuses)]
            pt     = proc_types[i % len(proc_types)] if proc_types else None
            asn    = assignees[i % len(assignees)]
            child  = next((c for c in child_cats if c['parent_id']==cat['id']), None)
            date   = (today - _td(days=i*3)).strftime('%Y-%m-%d %H:%M:%S')
            voc_no = f"VOC{today.strftime('%Y%m')}{i+1:04d}"

            existing = conn.execute('SELECT vocno FROM voc_info WHERE vocno=?', (voc_no,)).fetchone()
            if existing:
                continue

            conn.execute('''
                INSERT INTO voc_info (vocno, title, content, category, process_type, status, assignee_id, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            ''', (
                voc_no, title, content,
                child['name'] if child else cat['name'],
                pt['name'] if pt else '',
                status['value'],
                asn['id'],
                date, date
            ))
            created += 1
    return {'success': True, 'created': created}


if __name__ == '__main__':
    try:
        eel.start('index.html', size=(1440, 900), mode='edge')
    except Exception:
        eel.start('index.html', size=(1440, 900))
