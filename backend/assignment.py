from datetime import datetime
from backend.db import get_conn


# ── 담당자 기본 CRUD ─────────────────────────────────────────────

def get_assignees():
    with get_conn() as conn:
        rows = conn.execute('SELECT * FROM assignees ORDER BY turn_order ASC, id ASC').fetchall()
    return [dict(r) for r in rows]


def add_assignee(name, knox_id='', ip_address=''):
    name      = name.strip()
    knox_id   = (knox_id or '').strip() or None
    ip_address = (ip_address or '').strip()
    if not name:
        return {'success': False, 'error': '이름을 입력하세요.'}
    try:
        with get_conn() as conn:
            max_order = conn.execute('SELECT COALESCE(MAX(turn_order),0) FROM assignees').fetchone()[0]
            conn.execute(
                'INSERT INTO assignees (name, turn_order, knox_id, ip_address) VALUES (?,?,?,?)',
                (name, max_order + 1, knox_id, ip_address)
            )
        return {'success': True}
    except Exception:
        return {'success': False, 'error': '이미 존재하는 이름 또는 KNOX ID입니다.'}


def delete_assignee(assignee_id):
    with get_conn() as conn:
        active = conn.execute(
            "SELECT COUNT(*) FROM vocs WHERE assignee_id=? AND status IN ('open','in_progress')",
            (assignee_id,)
        ).fetchone()[0]
        if active > 0:
            return {'success': False, 'error': f'처리중인 VOC가 {active}건 있어 삭제할 수 없습니다.'}
        conn.execute('DELETE FROM assignees WHERE id=?', (assignee_id,))
    return {'success': True}


def update_assignee(assignee_id, name, knox_id='', ip_address=''):
    name      = (name or '').strip()
    knox_id   = (knox_id or '').strip() or None
    ip_address = (ip_address or '').strip()
    if not name:
        return {'success': False, 'error': '이름을 입력하세요.'}
    try:
        with get_conn() as conn:
            conn.execute(
                'UPDATE assignees SET name=?, knox_id=?, ip_address=? WHERE id=?',
                (name, knox_id, ip_address, assignee_id)
            )
        return {'success': True}
    except Exception:
        return {'success': False, 'error': 'KNOX ID가 중복됩니다.'}


def get_assignee_by_ip(ip):
    if not ip:
        return None
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM assignees WHERE ip_address=? AND active=1", (ip,)
        ).fetchone()
    return dict(row) if row else None


def toggle_assignee(assignee_id):
    with get_conn() as conn:
        row = conn.execute('SELECT active FROM assignees WHERE id=?', (assignee_id,)).fetchone()
        if row:
            new_active = 1 - row['active']
            if new_active == 1:
                # 활성화: 1순번 우선권 부여
                conn.execute('UPDATE assignees SET active=1, priority_next=1 WHERE id=?', (assignee_id,))
            else:
                conn.execute('UPDATE assignees SET active=0 WHERE id=?', (assignee_id,))
    return {'success': True}


def update_turn_order(order_list):
    with get_conn() as conn:
        for item in order_list:
            conn.execute('UPDATE assignees SET turn_order=? WHERE id=?',
                         (item['turn_order'], item['id']))
    return {'success': True}


# ── 배정 규칙 (전담) ─────────────────────────────────────────────

def get_assignment_rules():
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT r.*, a.name as assignee_name
            FROM assignment_rules r
            JOIN assignees a ON r.assignee_id = a.id
            ORDER BY r.category
        ''').fetchall()
    return [dict(r) for r in rows]


def save_assignment_rule(category, assignee_id, note=''):
    category = category.strip()
    if not category:
        return {'success': False, 'error': '카테고리를 입력하세요.'}
    with get_conn() as conn:
        conn.execute('''
            INSERT INTO assignment_rules (category, assignee_id, note)
            VALUES (?, ?, ?)
            ON CONFLICT(category) DO UPDATE SET assignee_id=excluded.assignee_id, note=excluded.note
        ''', (category, int(assignee_id), note))
    return {'success': True}


def delete_assignment_rule(rule_id):
    with get_conn() as conn:
        conn.execute('DELETE FROM assignment_rules WHERE id=?', (rule_id,))
    return {'success': True}


# ── 휴가 관리 ────────────────────────────────────────────────────

def get_vacations():
    today = datetime.now().strftime('%Y-%m-%d')
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT v.*, a.name as assignee_name,
                   CASE WHEN v.vacation_date < ? THEN 1 ELSE 0 END as is_past
            FROM vacations v
            JOIN assignees a ON v.assignee_id = a.id
            ORDER BY v.vacation_date DESC, a.name
        ''', (today,)).fetchall()
    return [dict(r) for r in rows]


def add_vacation(assignee_id, vacation_date, vacation_type):
    if vacation_type not in ('연차', '오전반차', '오후반차'):
        return {'success': False, 'error': '잘못된 휴가 유형입니다.'}
    try:
        with get_conn() as conn:
            conn.execute(
                'INSERT INTO vacations (assignee_id, vacation_date, vacation_type) VALUES (?, ?, ?)',
                (int(assignee_id), vacation_date, vacation_type)
            )
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def delete_vacation(vacation_id):
    with get_conn() as conn:
        conn.execute('DELETE FROM vacations WHERE id=?', (vacation_id,))
    return {'success': True}


# ── 휴가 내부 헬퍼 ────────────────────────────────────────────────

def _get_absent_ids(conn):
    """현재 시각 기준 휴가/반차 중인 assignee_id 집합"""
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    hour = now.hour

    absent = set()
    rows = conn.execute(
        "SELECT assignee_id, vacation_type FROM vacations WHERE vacation_date=? AND processed=0",
        (today,)
    ).fetchall()
    for r in rows:
        vt = r['vacation_type']
        if vt == '연차':
            absent.add(r['assignee_id'])
        elif vt == '오전반차' and hour < 12:
            absent.add(r['assignee_id'])
        elif vt == '오후반차' and hour >= 13:
            absent.add(r['assignee_id'])
    return absent


def _process_ended_vacations(conn):
    """종료된 휴가를 처리하고 배정을 놓쳤으면 priority_next 부여"""
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    hour = now.hour

    # 과거 날짜의 미처리 휴가 (연차/오전반차/오후반차 모두)
    past = conn.execute(
        "SELECT * FROM vacations WHERE vacation_date < ? AND processed=0", (today,)
    ).fetchall()

    # 오늘 오전반차인데 이미 오후가 된 경우
    ended_morning = conn.execute(
        "SELECT * FROM vacations WHERE vacation_date=? AND vacation_type='오전반차' AND processed=0",
        (today,)
    ).fetchall() if hour >= 12 else []

    for v in list(past) + list(ended_morning):
        if v['assignments_missed'] > 0:
            conn.execute('UPDATE assignees SET priority_next=1 WHERE id=?', (v['assignee_id'],))
        conn.execute('UPDATE vacations SET processed=1 WHERE id=?', (v['id'],))


# ── 순번 상태 ────────────────────────────────────────────────────

def _get_last_assigned_id(conn):
    row = conn.execute(
        "SELECT value FROM system_config WHERE key='last_auto_assigned_id'"
    ).fetchone()
    return int(row['value']) if row else 0


def _set_last_assigned_id(conn, assignee_id):
    conn.execute(
        "INSERT OR REPLACE INTO system_config (key, value) VALUES ('last_auto_assigned_id', ?)",
        (str(assignee_id),)
    )


def get_next_up():
    with get_conn() as conn:
        _process_ended_vacations(conn)
        absent_ids = _get_absent_ids(conn)

        candidates = [dict(c) for c in conn.execute('''
            SELECT a.*,
                   COUNT(CASE WHEN v.status IN ('open','in_progress') THEN 1 END) as active_count
            FROM assignees a
            LEFT JOIN vocs v ON v.assignee_id = a.id
            WHERE a.active = 1
            GROUP BY a.id
            ORDER BY a.turn_order ASC, a.id ASC
        ''').fetchall()]

        rules = {r['category']: r['assignee_id'] for r in conn.execute(
            'SELECT category, assignee_id FROM assignment_rules'
        ).fetchall()}

        last_id = _get_last_assigned_id(conn)

    dedicated_ids = set(rules.values())
    regular = [c for c in candidates if c['id'] not in dedicated_ids and c['id'] not in absent_ids]

    if not regular:
        return {
            'next_assignee': None, 'candidates': candidates,
            'dedicated_ids': list(dedicated_ids), 'absent_ids': list(absent_ids),
        }

    # priority_next 먼저
    priority_pool = [c for c in regular if c.get('priority_next', 0) == 1]
    if priority_pool:
        next_person = priority_pool[0]
    else:
        last_idx = next((i for i, c in enumerate(regular) if c['id'] == last_id), -1)
        n = len(regular)
        next_person = None
        for offset in range(1, n + 1):
            c = regular[(last_idx + offset) % n]
            if c['hold_turns'] == 0:
                next_person = c
                break
        if next_person is None and regular:
            next_person = regular[(last_idx + 1) % n]

    return {
        'next_assignee': next_person,
        'candidates': candidates,
        'dedicated_ids': list(dedicated_ids),
        'absent_ids': list(absent_ids),
    }


# ── 자동 배정 핵심 ───────────────────────────────────────────────

def auto_assign(category=None):
    with get_conn() as conn:
        _process_ended_vacations(conn)
        absent_ids = _get_absent_ids(conn)
        today = datetime.now().strftime('%Y-%m-%d')

        # 전담 규칙 확인 (전담자가 휴가 중이면 일반 배정으로 fallback)
        if category and category.strip():
            rule = conn.execute(
                'SELECT r.assignee_id, a.name FROM assignment_rules r JOIN assignees a ON r.assignee_id=a.id WHERE r.category=?',
                (category.strip(),)
            ).fetchone()
            if rule and rule['assignee_id'] not in absent_ids:
                return {'assignee_id': rule['assignee_id'], 'type': 'dedicated', 'skipped': []}

        dedicated_ids = {r['assignee_id'] for r in conn.execute(
            'SELECT assignee_id FROM assignment_rules'
        ).fetchall()}

        all_active = [dict(c) for c in conn.execute(
            'SELECT * FROM assignees WHERE active=1 ORDER BY turn_order ASC, id ASC'
        ).fetchall() if c['id'] not in dedicated_ids]

        # 현재 가용 후보 (휴가 제외)
        candidates = [c for c in all_active if c['id'] not in absent_ids]
        if not candidates:
            # 전원 휴가인 예외 상황: 전체로 fallback
            candidates = all_active
        if not candidates:
            return {'assignee_id': None, 'type': None, 'skipped': []}

        last_id = _get_last_assigned_id(conn)
        skipped = []
        chosen = None

        # priority_next 우선 배정
        priority_pool = [c for c in candidates if c.get('priority_next', 0) == 1]
        if priority_pool:
            chosen = priority_pool[0]
            conn.execute('UPDATE assignees SET priority_next=0 WHERE id=?', (chosen['id'],))
        else:
            last_idx = next((i for i, c in enumerate(candidates) if c['id'] == last_id), -1)
            n = len(candidates)
            for offset in range(1, n + 1):
                c = candidates[(last_idx + offset) % n]
                if c['hold_turns'] > 0:
                    skipped.append({'id': c['id'], 'name': c['name']})
                else:
                    chosen = c
                    break
            if chosen is None and candidates:
                chosen = candidates[(last_idx + 1) % n]
                skipped = [{'id': c['id'], 'name': c['name']}
                           for c in candidates if c['id'] != chosen['id'] and c['hold_turns'] > 0]

        # 보류 차감
        for s in skipped:
            conn.execute('UPDATE assignees SET hold_turns=MAX(0, hold_turns-1) WHERE id=?', (s['id'],))

        _set_last_assigned_id(conn, chosen['id'])

        # 휴가 중인 담당자 assignments_missed 증가
        for aid in absent_ids:
            conn.execute(
                'UPDATE vacations SET assignments_missed=assignments_missed+1 WHERE assignee_id=? AND vacation_date=? AND processed=0',
                (aid, today)
            )

    return {'assignee_id': chosen['id'], 'type': 'auto', 'skipped': skipped}


def add_hold(assignee_id):
    with get_conn() as conn:
        conn.execute('UPDATE assignees SET hold_turns=hold_turns+1 WHERE id=?', (assignee_id,))


# ── 배정 이력 & 재배정 ────────────────────────────────────────────

def get_workload():
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    hour = now.hour

    with get_conn() as conn:
        rows = conn.execute('''
            SELECT
                a.id, a.name, a.active, a.turn_order, a.hold_turns, a.priority_next,
                COUNT(CASE WHEN v.status='open'                   THEN 1 END) as open_count,
                COUNT(CASE WHEN v.status='in_progress'            THEN 1 END) as in_progress_count,
                COUNT(CASE WHEN v.status IN ('resolved','closed') THEN 1 END) as done_count,
                COUNT(v.id) as total_count
            FROM assignees a
            LEFT JOIN vocs v ON v.assignee_id = a.id
            GROUP BY a.id
            ORDER BY a.turn_order ASC, a.name
        ''').fetchall()

        today_vacs = {r['assignee_id']: r['vacation_type'] for r in conn.execute(
            "SELECT assignee_id, vacation_type FROM vacations WHERE vacation_date=? AND processed=0",
            (today,)
        ).fetchall()}

    result = []
    for row in rows:
        d = dict(row)
        vt = today_vacs.get(d['id'], '')
        d['vacation_type'] = vt
        if vt == '연차':
            d['is_absent'] = True
        elif vt == '오전반차' and hour < 12:
            d['is_absent'] = True
        elif vt == '오후반차' and hour >= 13:
            d['is_absent'] = True
        else:
            d['is_absent'] = False
        result.append(d)
    return result


def reassign(voc_id, assignee_id, note='', forced=False, assignment_type=None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE vocs SET assignee_id=?, updated_at=datetime('now','localtime') WHERE id=?",
            (assignee_id, voc_id)
        )
        atype = assignment_type or ('forced' if forced else 'manual')
        full_note = note or ('지정 배정' if forced else '재배정')
        if forced and not note:
            full_note += ' (다음 순번 1회 보류)'
        conn.execute(
            'INSERT INTO assignment_history (voc_id, assignee_id, note, assignment_type) VALUES (?,?,?,?)',
            (voc_id, assignee_id, full_note, atype)
        )
    if forced:
        add_hold(assignee_id)
    return {'success': True}


def auto_assign_voc(voc_id):
    """기존 미배정 VOC를 라운드로빈으로 자동 배정"""
    try:
        with get_conn() as conn:
            row = conn.execute('SELECT category FROM vocs WHERE id=?', (voc_id,)).fetchone()
            if not row:
                return {'success': False, 'error': 'VOC not found'}
            category = row['category']

        assign_result = auto_assign(category)
        if not assign_result['assignee_id']:
            return {'success': False, 'error': '배정 가능한 담당자가 없습니다.'}

        with get_conn() as conn:
            conn.execute(
                "UPDATE vocs SET assignee_id=?, updated_at=datetime('now','localtime') WHERE id=?",
                (assign_result['assignee_id'], voc_id)
            )
            conn.execute(
                'INSERT INTO assignment_history (voc_id, assignee_id, note, assignment_type) VALUES (?,?,?,?)',
                (voc_id, assign_result['assignee_id'], '자동 배정 (라운드로빈)', 'auto')
            )
            for s in assign_result.get('skipped', []):
                conn.execute(
                    'INSERT INTO assignment_history (voc_id, assignee_id, note, assignment_type) VALUES (?,?,?,?)',
                    (voc_id, s['id'], f'{s["name"]} 순번 보류', 'skipped')
                )

        return {'success': True, 'assign_info': assign_result}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_history(voc_id):
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT h.*, a.name as assignee_name
            FROM assignment_history h
            JOIN assignees a ON h.assignee_id = a.id
            WHERE h.voc_id = ?
            ORDER BY h.assigned_at
        ''', (voc_id,)).fetchall()
    return [dict(r) for r in rows]
