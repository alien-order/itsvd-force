import re
from backend.db import get_conn
from backend import assignment as _asgn
from backend import image_search

_TYPE_NOTE = {
    'auto':      '자동 배정 (라운드로빈)',
    'dedicated': '전담 배정',
    'forced':    '지정 배정 (다음 순번 1회 보류)',
    'skipped':   '순번 보류',
}


def create_voc(data):
    title             = data.get('title', '').strip()
    content           = data.get('content', '').strip()
    category          = data.get('category', '').strip()
    priority          = data.get('priority', 'normal')
    voc_number        = data.get('voc_number', '').strip()
    requester         = data.get('requester', '').strip()
    due_date          = data.get('due_date', '').strip()
    images            = data.get('images', [])
    forced_assignee_id = data.get('forced_assignee_id')  # None = auto

    if not title or not content:
        return {'success': False, 'error': '제목과 내용은 필수입니다.'}

    if forced_assignee_id:
        assign_result = {'assignee_id': int(forced_assignee_id), 'type': 'forced', 'skipped': []}
        _asgn.add_hold(int(forced_assignee_id))
    else:
        assign_result = _asgn.auto_assign(category)

    assignee_id = assign_result['assignee_id']

    with get_conn() as conn:
        cur = conn.execute(
            '''INSERT INTO vocs
               (title, content, category, priority, assignee_id, voc_number, requester, due_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (title, content, category, priority, assignee_id, voc_number, requester, due_date)
        )
        voc_id = cur.lastrowid

        # 배정 이력 기록
        if assignee_id:
            conn.execute(
                'INSERT INTO assignment_history (voc_id, assignee_id, note, assignment_type) VALUES (?,?,?,?)',
                (voc_id, assignee_id,
                 _TYPE_NOTE.get(assign_result['type'], '배정'),
                 assign_result['type'])
            )

        # 보류된 담당자 이력 기록
        for skipped in assign_result.get('skipped', []):
            conn.execute(
                'INSERT INTO assignment_history (voc_id, assignee_id, note, assignment_type) VALUES (?,?,?,?)',
                (voc_id, skipped['id'],
                 f'{skipped["name"]} 순번 보류 (지정 배정 패널티)',
                 'skipped')
            )

        row = conn.execute('''
            SELECT v.*, a.name as assignee_name
            FROM vocs v LEFT JOIN assignees a ON v.assignee_id = a.id
            WHERE v.id = ?
        ''', (voc_id,)).fetchone()

    if images:
        image_search.save_voc_images(voc_id, voc_number or str(voc_id), images)

    return {'success': True, 'voc': dict(row), 'assign_info': assign_result}


def get_vocs(status=None, search=None, assignee_id=None, category=None, date_from=None, date_to=None):
    query = '''
        SELECT v.*, a.name as assignee_name
        FROM vocs v LEFT JOIN assignees a ON v.assignee_id = a.id
        WHERE 1=1
    '''
    params = []

    if status == 'active':
        query += " AND v.status IN ('open', 'in_progress')"
    elif status and status != 'all':
        query += ' AND v.status = ?'
        params.append(status)

    if search and search.strip():
        query += ' AND (v.title LIKE ? OR v.content LIKE ? OR v.category LIKE ? OR v.voc_number LIKE ?)'
        s = f'%{search.strip()}%'
        params.extend([s, s, s, s])

    if date_from:
        query += " AND DATE(v.created_at) >= ?"
        params.append(date_from)

    if date_to:
        query += " AND DATE(v.created_at) <= ?"
        params.append(date_to)

    if category and category != 'all':
        query += ' AND v.category = ?'
        params.append(category)

    if assignee_id and assignee_id != 'all':
        if assignee_id == 'unassigned':
            query += ' AND v.assignee_id IS NULL'
        else:
            query += ' AND v.assignee_id = ?'
            params.append(int(assignee_id))

    query += ' ORDER BY v.created_at DESC'

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_categories():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name FROM type_items WHERE group_code='category' ORDER BY sort_order ASC, id ASC"
        ).fetchall()
    return [r['name'] for r in rows]


def get_years():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT strftime('%Y', created_at) as yr FROM vocs ORDER BY yr DESC"
        ).fetchall()
    return [r['yr'] for r in rows if r['yr']]


def update_status(voc_id, status):
    with get_conn() as conn:
        conn.execute(
            "UPDATE vocs SET status = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (status, voc_id)
        )
    return {'success': True}


def get_similar(title, content, limit=5, exclude_id=None):
    text = f'{title} {content}'
    words = set(re.findall(r'[가-힣a-zA-Z0-9]{2,}', text))

    if not words:
        return []

    with get_conn() as conn:
        if exclude_id:
            rows = conn.execute('''
                SELECT v.*, a.name as assignee_name
                FROM vocs v LEFT JOIN assignees a ON v.assignee_id = a.id
                WHERE v.id != ?
            ''', (exclude_id,)).fetchall()
        else:
            rows = conn.execute('''
                SELECT v.*, a.name as assignee_name
                FROM vocs v LEFT JOIN assignees a ON v.assignee_id = a.id
            ''').fetchall()

    scored = []
    for row in rows:
        row_words = set(re.findall(r'[가-힣a-zA-Z0-9]{2,}', f'{row["title"]} {row["content"]}'))
        overlap = len(words & row_words)
        if overlap > 0:
            scored.append((overlap, dict(row)))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:limit]]


def add_note(voc_id, content, note_date='', work_minutes=0):
    if not content.strip():
        return {'success': False, 'error': '내용을 입력하세요.'}
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO voc_notes (voc_id, content, note_date, work_minutes) VALUES (?, ?, ?, ?)',
            (voc_id, content.strip(), note_date or '', int(work_minutes) if work_minutes else 0)
        )
    return {'success': True}


def get_notes(voc_id):
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM voc_notes WHERE voc_id = ? ORDER BY created_at',
            (voc_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats(period_type='monthly'):
    if period_type == 'monthly':
        period_sql = "strftime('%Y-%m', created_at)"
    else:
        period_sql = "strftime('%Y-W%W', created_at)"

    with get_conn() as conn:
        rows = conn.execute(f'''
            SELECT {period_sql} as period,
                   COALESCE(NULLIF(TRIM(category), ''), '기타') as cat,
                   COUNT(*) as cnt
            FROM vocs
            GROUP BY period, cat
            ORDER BY period DESC, cnt DESC
        ''').fetchall()

    from collections import OrderedDict
    periods = OrderedDict()
    for r in rows:
        p = r['period']
        if p not in periods:
            periods[p] = {'period': p, 'total': 0, 'categories': []}
        periods[p]['total'] += r['cnt']
        periods[p]['categories'].append({'category': r['cat'], 'count': r['cnt']})

    return list(periods.values())


def sync_statuses():
    from backend import scraper as _scraper
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, voc_number, status FROM vocs WHERE status NOT IN ('closed')"
        ).fetchall()
    voc_list = [dict(r) for r in rows]

    result = _scraper.sync_statuses(voc_list)
    if not result['success']:
        return result

    if result['updated']:
        with get_conn() as conn:
            for item in result['updated']:
                conn.execute(
                    "UPDATE vocs SET status=?, updated_at=datetime('now','localtime') WHERE id=?",
                    (item['new'], item['id'])
                )
    return result


def update_from_sync(voc_id, data):
    fields, params = [], []
    for key in ('title', 'content', 'requester', 'due_date'):
        val = (data.get(key) or '').strip()
        if val:
            fields.append(f'{key} = ?')
            params.append(val)
    if not fields:
        return {'success': False, 'error': '업데이트할 데이터가 없습니다.'}
    params.append(voc_id)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE vocs SET {', '.join(fields)}, updated_at=datetime('now','localtime') WHERE id=?",
            params
        )
    return {'success': True}


def get_daily_report():
    from datetime import date
    status_label = {'open': '접수', 'in_progress': '처리중', 'resolved': '해결', 'closed': '종료'}

    with get_conn() as conn:
        rows = conn.execute('''
            SELECT v.id, v.voc_number, v.title, v.due_date, v.status, a.name as assignee_name
            FROM vocs v
            LEFT JOIN assignees a ON v.assignee_id = a.id
            WHERE v.status NOT IN ('closed')
            ORDER BY
                CASE WHEN v.due_date = '' OR v.due_date IS NULL THEN 1 ELSE 0 END,
                v.due_date ASC,
                v.id ASC
        ''').fetchall()

    today = date.today().strftime('%Y-%m-%d')
    lines = [f'[VOC 처리 현황] {today}', '']

    for r in rows:
        num = r['voc_number'] or f'#{r["id"]}'
        due = r['due_date'] or '-'
        assignee = r['assignee_name'] or '미배정'
        status = status_label.get(r['status'], r['status'])
        lines.append(f'• [{num}] {r["title"]}')
        lines.append(f'  담당: {assignee}  |  완료요청: {due}  |  상태: {status}')

    lines.extend(['', f'총 {len(rows)}건'])
    return '\n'.join(lines)
