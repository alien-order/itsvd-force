import json
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
        active_vals = [r['value'] for r in conn.execute(
            "SELECT value FROM type_items WHERE group_code='voc_status' AND is_active=1 AND value!=''"
        ).fetchall()]
        if not active_vals:
            active_vals = ['open', 'in_progress']
        placeholders = ','.join('?' * len(active_vals))
        active = conn.execute(
            f'SELECT COUNT(*) FROM vocs WHERE assignee_id=? AND status IN ({placeholders})',
            [assignee_id] + active_vals
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


def update_avatar(assignee_id, b64_data):
    with get_conn() as conn:
        conn.execute('UPDATE assignees SET avatar=? WHERE id=?', (b64_data or '', assignee_id))
    return {'success': True}


def toggle_assignee(assignee_id):
    with get_conn() as conn:
        row = conn.execute('SELECT active FROM assignees WHERE id=?', (assignee_id,)).fetchone()
        if row:
            new_active = 1 - row['active']
            if new_active == 1:
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


# ── 휴가 유형 설정 ────────────────────────────────────────────────

def get_vacation_type_config():
    with get_conn() as conn:
        rows = conn.execute('SELECT * FROM vacation_type_config ORDER BY vacation_type').fetchall()
    order = {'연차': 0, '오전반차': 1, '오후반차': 2}
    result = [dict(r) for r in rows]
    result.sort(key=lambda x: order.get(x['vacation_type'], 9))
    return result


def save_vacation_type_config(vacation_type, time_start, time_end, n_rounds, assign_during):
    if vacation_type not in ('연차', '오전반차', '오후반차'):
        return {'success': False, 'error': '잘못된 휴가 유형입니다.'}
    try:
        with get_conn() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO vacation_type_config
                (vacation_type, time_start, time_end, n_rounds, assign_during)
                VALUES (?,?,?,?,?)
            ''', (vacation_type, time_start or '00:00', time_end or '23:59',
                  max(0, int(n_rounds or 0)), 1 if assign_during else 0))
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ── 휴가 관리 ────────────────────────────────────────────────────

def get_vacations(year=None, month=None):
    today = datetime.now().strftime('%Y-%m-%d')
    with get_conn() as conn:
        if year and month:
            prefix = f'{int(year):04d}-{int(month):02d}'
            rows = conn.execute('''
                SELECT v.*, a.name as assignee_name,
                       CASE WHEN v.vacation_date < ? THEN 1 ELSE 0 END as is_past
                FROM vacations v
                JOIN assignees a ON v.assignee_id = a.id
                WHERE v.vacation_date LIKE ?
                ORDER BY v.vacation_date DESC, a.name
            ''', (today, prefix + '%')).fetchall()
        elif year:
            prefix = f'{int(year):04d}'
            rows = conn.execute('''
                SELECT v.*, a.name as assignee_name,
                       CASE WHEN v.vacation_date < ? THEN 1 ELSE 0 END as is_past
                FROM vacations v
                JOIN assignees a ON v.assignee_id = a.id
                WHERE v.vacation_date LIKE ?
                ORDER BY v.vacation_date DESC, a.name
            ''', (today, prefix + '%')).fetchall()
        else:
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

def _load_vacation_type_config(conn):
    rows = conn.execute('SELECT * FROM vacation_type_config').fetchall()
    return {r['vacation_type']: dict(r) for r in rows}


def _get_active_vacations(conn):
    """현재 시각 기준 휴가 중인 담당자 정보: {assignee_id: {'vac': dict, 'cfg': dict}}"""
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    now_hm = now.strftime('%H:%M')

    vtc = _load_vacation_type_config(conn)
    rows = conn.execute(
        "SELECT * FROM vacations WHERE vacation_date=? AND processed=0", (today,)
    ).fetchall()

    result = {}
    for v in rows:
        cfg = vtc.get(v['vacation_type'], {
            'time_start': '00:00', 'time_end': '23:59', 'n_rounds': 0, 'assign_during': 0
        })
        ts = cfg.get('time_start', '00:00')
        te = cfg.get('time_end', '23:59')
        if ts <= now_hm <= te:
            result[v['assignee_id']] = {'vac': dict(v), 'cfg': cfg}
    return result


def _get_absent_ids(conn):
    return set(_get_active_vacations(conn).keys())


def _finalize_vacation(conn, vac, cfg):
    assign_during = cfg.get('assign_during', 0)
    if assign_during == 0:
        cat_counts = json.loads(vac.get('cat_counts') or '{}')
        if any(c > 0 for c in cat_counts.values()):
            conn.execute('UPDATE assignees SET priority_next=1 WHERE id=?', (vac['assignee_id'],))


def _process_ended_vacations(conn):
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    now_hm = now.strftime('%H:%M')

    vtc = _load_vacation_type_config(conn)

    past = conn.execute(
        "SELECT * FROM vacations WHERE vacation_date < ? AND processed=0", (today,)
    ).fetchall()
    for v in past:
        cfg = vtc.get(v['vacation_type'], {'assign_during': 0})
        _finalize_vacation(conn, dict(v), cfg)
        conn.execute('UPDATE vacations SET processed=1 WHERE id=?', (v['id'],))

    today_all = conn.execute(
        "SELECT * FROM vacations WHERE vacation_date=? AND processed=0", (today,)
    ).fetchall()
    for v in today_all:
        cfg = vtc.get(v['vacation_type'], {'time_end': '23:59', 'assign_during': 0})
        te = cfg.get('time_end', '23:59')
        if now_hm > te:
            _finalize_vacation(conn, dict(v), cfg)
            conn.execute('UPDATE vacations SET processed=1 WHERE id=?', (v['id'],))


# ── 담당자 업무유형 매핑 ─────────────────────────────────────────

def get_assignee_categories(assignee_id):
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT category_id FROM assignee_categories WHERE assignee_id=?', (assignee_id,)
        ).fetchall()
    return [r['category_id'] for r in rows]


def set_assignee_categories(assignee_id, category_ids):
    with get_conn() as conn:
        conn.execute('DELETE FROM assignee_categories WHERE assignee_id=?', (assignee_id,))
        for cid in category_ids:
            try:
                conn.execute(
                    'INSERT INTO assignee_categories (assignee_id, category_id) VALUES (?,?)',
                    (assignee_id, int(cid))
                )
            except Exception:
                pass
    return {'success': True}


def get_all_assignee_categories():
    with get_conn() as conn:
        rows = conn.execute('SELECT assignee_id, category_id FROM assignee_categories').fetchall()
    result = {}
    for r in rows:
        result.setdefault(r['assignee_id'], []).append(r['category_id'])
    return result


# ── 카테고리 풀 기반 배정 헬퍼 ───────────────────────────────────

def _get_parent_cat_id(conn, category_name):
    if not category_name:
        return None
    row = conn.execute(
        "SELECT id, parent_id FROM type_items WHERE group_code='category' AND name=?",
        (category_name.strip(),)
    ).fetchone()
    if not row:
        return None
    return int(row['parent_id']) if row['parent_id'] else int(row['id'])


def _get_cat_last_assigned(conn, category_id):
    row = conn.execute(
        "SELECT value FROM system_config WHERE key=?", (f'rr_last:{category_id}',)
    ).fetchone()
    return int(row['value']) if row else 0


def _set_cat_last_assigned(conn, category_id, assignee_id):
    conn.execute(
        "INSERT OR REPLACE INTO system_config (key, value) VALUES (?,?)",
        (f'rr_last:{category_id}', str(assignee_id))
    )


def _get_category_pool(conn, parent_cat_id, absent_ids):
    all_active = [dict(r) for r in conn.execute(
        'SELECT * FROM assignees WHERE active=1 ORDER BY turn_order ASC, id ASC'
    ).fetchall()]

    if parent_cat_id is None:
        pool = [a for a in all_active if a['id'] not in absent_ids]
        return pool or all_active, None

    total_mapped = conn.execute('SELECT COUNT(*) FROM assignee_categories').fetchone()[0]
    if total_mapped == 0:
        pool = [a for a in all_active if a['id'] not in absent_ids]
        return pool or all_active, None

    handler_ids = {r['assignee_id'] for r in conn.execute(
        'SELECT assignee_id FROM assignee_categories WHERE category_id=?', (parent_cat_id,)
    ).fetchall()}

    if not handler_ids:
        pool = [a for a in all_active if a['id'] not in absent_ids]
        return pool or all_active, None

    pool = [a for a in all_active if a['id'] in handler_ids and a['id'] not in absent_ids]
    if not pool:
        pool = [a for a in all_active if a['id'] in handler_ids]

    return pool, parent_cat_id


def _should_auto_hold(conn, chosen_id, category_id):
    if not category_id:
        return False
    count = conn.execute('''
        SELECT COUNT(DISTINCT a.id) FROM assignees a
        WHERE a.id != :chosen AND a.active = 1
          AND EXISTS (
              SELECT 1 FROM assignee_categories ac_shared
              WHERE ac_shared.assignee_id = a.id
                AND ac_shared.category_id IN (
                    SELECT category_id FROM assignee_categories
                    WHERE assignee_id = :chosen AND category_id != :cat
                )
          )
          AND NOT EXISTS (
              SELECT 1 FROM assignee_categories
              WHERE assignee_id = a.id AND category_id = :cat
          )
    ''', {'chosen': chosen_id, 'cat': category_id}).fetchone()[0]
    return count > 0


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


def _get_active_status_vals(conn):
    rows = conn.execute(
        "SELECT value FROM type_items WHERE group_code='voc_status' AND is_active=1 AND value!=''"
    ).fetchall()
    vals = [r['value'] for r in rows]
    return vals if vals else ['open', 'in_progress']


def get_next_up():
    with get_conn() as conn:
        _process_ended_vacations(conn)
        absent_ids = _get_absent_ids(conn)
        active_vals = _get_active_status_vals(conn)
        in_clause = ','.join(f"'{v}'" for v in active_vals)

        candidates = [dict(c) for c in conn.execute(f'''
            SELECT a.*,
                   COUNT(CASE WHEN v.status IN ({in_clause}) THEN 1 END) as active_count
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
        today = datetime.now().strftime('%Y-%m-%d')

        active_vacs = _get_active_vacations(conn)
        absent_ids  = set(active_vacs.keys())

        # 명시적 전담 규칙
        if category and category.strip():
            rule = conn.execute(
                'SELECT assignee_id FROM assignment_rules WHERE category=?',
                (category.strip(),)
            ).fetchone()
            if rule and rule['assignee_id'] not in absent_ids:
                return {'assignee_id': rule['assignee_id'], 'type': 'dedicated', 'skipped': []}

        parent_cat_id = _get_parent_cat_id(conn, category) if category else None

        # 카테고리 담당 핸들러 ID 목록 (cat_counts 업데이트용)
        handler_ids_for_cat = set()
        if parent_cat_id:
            handler_ids_for_cat = {r['assignee_id'] for r in conn.execute(
                'SELECT assignee_id FROM assignee_categories WHERE category_id=?', (parent_cat_id,)
            ).fetchall()}

        # assign_during=1 이고 N바퀴 채워진 휴가자 → 이번 배정에 일시 포함
        triggered_ids = set()
        if parent_cat_id:
            for aid, info in active_vacs.items():
                cfg = info['cfg']
                if cfg.get('assign_during', 0) != 1:
                    continue
                if aid not in handler_ids_for_cat:
                    continue
                n_rounds = cfg.get('n_rounds', 0)
                if n_rounds <= 0:
                    continue
                cat_counts = json.loads(info['vac'].get('cat_counts') or '{}')
                count = cat_counts.get(str(parent_cat_id), 0)

                # 현재 휴가자를 제외한 활성 풀 크기
                placeholders = ','.join(str(x) for x in absent_ids) if absent_ids else '0'
                pool_size = conn.execute(
                    f'''SELECT COUNT(*) FROM assignees a
                        JOIN assignee_categories ac ON ac.assignee_id = a.id
                        WHERE a.active=1 AND ac.category_id=? AND a.id NOT IN ({placeholders})''',
                    (parent_cat_id,)
                ).fetchone()[0]

                if pool_size > 0 and count >= n_rounds * pool_size:
                    triggered_ids.add(aid)

        effective_absent = absent_ids - triggered_ids
        candidates, pool_cat_id = _get_category_pool(conn, parent_cat_id, effective_absent)

        if not candidates:
            return {'assignee_id': None, 'type': None, 'skipped': []}

        skipped = []
        chosen = None
        do_auto_hold = False

        priority_pool = [c for c in candidates if c.get('priority_next', 0) == 1]
        if priority_pool:
            chosen = priority_pool[0]
            conn.execute('UPDATE assignees SET priority_next=0 WHERE id=?', (chosen['id'],))
        else:
            last_id = (_get_cat_last_assigned(conn, pool_cat_id)
                       if pool_cat_id else _get_last_assigned_id(conn))
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

            if chosen and pool_cat_id:
                do_auto_hold = _should_auto_hold(conn, chosen['id'], pool_cat_id)

        for s in skipped:
            conn.execute('UPDATE assignees SET hold_turns=MAX(0, hold_turns-1) WHERE id=?', (s['id'],))

        if chosen:
            if pool_cat_id:
                _set_cat_last_assigned(conn, pool_cat_id, chosen['id'])
            _set_last_assigned_id(conn, chosen['id'])
            if do_auto_hold:
                conn.execute('UPDATE assignees SET hold_turns=hold_turns+1 WHERE id=?', (chosen['id'],))

        # cat_counts 업데이트 (휴가자별)
        if pool_cat_id and active_vacs:
            cat_key = str(pool_cat_id)
            for aid, info in active_vacs.items():
                if aid not in handler_ids_for_cat:
                    continue
                vac = info['vac']
                cat_counts = json.loads(vac.get('cat_counts') or '{}')
                if aid in triggered_ids:
                    # 이번에 풀에 포함됐으니 카운트 리셋
                    cat_counts[cat_key] = 0
                else:
                    cat_counts[cat_key] = cat_counts.get(cat_key, 0) + 1
                conn.execute(
                    "UPDATE vacations SET cat_counts=? WHERE id=?",
                    (json.dumps(cat_counts), vac['id'])
                )

        # 레거시 assignments_missed 업데이트
        for aid in absent_ids:
            conn.execute(
                'UPDATE vacations SET assignments_missed=assignments_missed+1 '
                'WHERE assignee_id=? AND vacation_date=? AND processed=0',
                (aid, today)
            )

    return {
        'assignee_id': chosen['id'] if chosen else None,
        'type': 'auto',
        'skipped': skipped,
        'auto_held': do_auto_hold,
    }


def add_hold(assignee_id):
    with get_conn() as conn:
        conn.execute('UPDATE assignees SET hold_turns=hold_turns+1 WHERE id=?', (assignee_id,))


# ── 배정 이력 & 재배정 ────────────────────────────────────────────

def get_workload():
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')

    with get_conn() as conn:
        active_vals = _get_active_status_vals(conn)
        in_active = ','.join(f"'{v}'" for v in active_vals)
        rows = conn.execute(f'''
            SELECT
                a.id, a.name, a.active, a.turn_order, a.hold_turns, a.priority_next,
                COUNT(CASE WHEN COALESCE(NULLIF(vi.vocstatuscode,''), vi.status) IN ({in_active}) THEN 1 END) as open_count,
                0 as in_progress_count,
                COUNT(CASE WHEN COALESCE(NULLIF(vi.vocstatuscode,''), vi.status) NOT IN ({in_active})
                           AND COALESCE(NULLIF(vi.vocstatuscode,''), vi.status) IS NOT NULL
                           AND COALESCE(NULLIF(vi.vocstatuscode,''), vi.status) != '' THEN 1 END) as done_count,
                COUNT(vi.vocno) as total_count
            FROM assignees a
            LEFT JOIN voc_info vi ON vi.assignee_id = a.id
            GROUP BY a.id
            ORDER BY a.turn_order ASC, a.name
        ''').fetchall()

        active_vacs = _get_active_vacations(conn)

    result = []
    for row in rows:
        d = dict(row)
        info = active_vacs.get(d['id'])
        if info:
            d['vacation_type'] = info['vac']['vacation_type']
            d['is_absent'] = True
        else:
            d['vacation_type'] = ''
            d['is_absent'] = False
        result.append(d)
    return result


def reassign(vocno, assignee_id, note='', forced=False, assignment_type=None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE voc_info SET assignee_id=?, updated_at=datetime('now','localtime') WHERE vocno=?",
            (assignee_id, vocno)
        )
        atype = assignment_type or ('forced' if forced else 'manual')
        full_note = note or ('지정 배정' if forced else '재배정')
        if forced and not note:
            full_note += ' (다음 순번 1회 보류)'
        conn.execute(
            'INSERT INTO assignment_history (vocno, assignee_id, note, assignment_type) VALUES (?,?,?,?)',
            (vocno, assignee_id, full_note, atype)
        )
    if forced:
        add_hold(assignee_id)
    return {'success': True}


def auto_assign_voc(vocno):
    try:
        with get_conn() as conn:
            row = conn.execute('SELECT category FROM voc_info WHERE vocno=?', (vocno,)).fetchone()
            if not row:
                return {'success': False, 'error': 'VOC not found'}
            category = row['category']

        assign_result = auto_assign(category)
        if not assign_result['assignee_id']:
            return {'success': False, 'error': '배정 가능한 담당자가 없습니다.'}

        with get_conn() as conn:
            conn.execute(
                "UPDATE voc_info SET assignee_id=?, updated_at=datetime('now','localtime') WHERE vocno=?",
                (assign_result['assignee_id'], vocno)
            )
            conn.execute(
                'INSERT INTO assignment_history (vocno, assignee_id, note, assignment_type) VALUES (?,?,?,?)',
                (vocno, assign_result['assignee_id'], '자동 배정 (라운드로빈)', 'auto')
            )
            for s in assign_result.get('skipped', []):
                conn.execute(
                    'INSERT INTO assignment_history (vocno, assignee_id, note, assignment_type) VALUES (?,?,?,?)',
                    (vocno, s['id'], f'{s["name"]} 순번 보류', 'skipped')
                )

        return {'success': True, 'assign_info': assign_result}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_history(vocno):
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT h.*, a.name as assignee_name
            FROM assignment_history h
            JOIN assignees a ON h.assignee_id = a.id
            WHERE h.vocno = ?
            ORDER BY h.assigned_at
        ''', (vocno,)).fetchall()
    return [dict(r) for r in rows]
