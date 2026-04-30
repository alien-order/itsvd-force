import re
from datetime import datetime as _dt
from backend.db import get_conn
from backend import assignment as _asgn
from backend import image_search

_TYPE_NOTE = {
    'auto':      '자동 배정 (라운드로빈)',
    'dedicated': '전담 배정',
    'forced':    '지정 배정 (다음 순번 1회 보류)',
    'skipped':   '순번 보류',
}


def _update_status_from_last_stage(vocno, vocstatuscode):
    if not vocstatuscode:
        return
    with get_conn() as conn:
        item = conn.execute(
            "SELECT value FROM type_items WHERE group_code='voc_status' AND (name=? OR value=?)",
            (vocstatuscode, vocstatuscode)
        ).fetchone()
        mapped = item['value'] if item else ''
        conn.execute(
            "UPDATE voc_info SET status=?, updated_at=datetime('now','localtime') WHERE vocno=?",
            (mapped or vocstatuscode, vocno)
        )


def save_voc_info(vocno, data):
    _META = {'vocno', 'assignee_id', 'created_at', 'updated_at', 'images',
             'forced_assignee_id', 'voc_number'}
    with get_conn() as conn:
        existing_cols = {r['name'] for r in conn.execute('PRAGMA table_info(voc_info)').fetchall()}
        # Auto-add columns that api_field_map may reference but don't exist yet
        for key in data:
            if key not in _META and key not in existing_cols:
                try:
                    conn.execute(f"ALTER TABLE voc_info ADD COLUMN {key} TEXT DEFAULT ''")
                    existing_cols.add(key)
                except Exception:
                    pass
        row = {'vocno': vocno}
        for key, val in data.items():
            if key not in _META and key in existing_cols:
                row[key] = str(val or '').strip()
        if len(row) <= 1:
            return
        col_names = list(row.keys())
        placeholders = ','.join('?' * len(col_names))
        updates = ', '.join(f'{c}=excluded.{c}' for c in col_names if c != 'vocno')
        conn.execute(
            f'INSERT INTO voc_info ({",".join(col_names)}) VALUES ({placeholders}) '
            f'ON CONFLICT(vocno) DO UPDATE SET {updates}',
            list(row.values())
        )


def get_voc_info(vocno):
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM voc_info WHERE vocno=?', (vocno,)).fetchone()
    return dict(row) if row else {}


def save_voc_stages(vocno, stages):
    _META = {'id', 'vocno', 'stage_index', 'uppervocno', 'vocstatuscode', 'vocstatusname',
             'voctypename', 'voctypecode', 'created_at', 'stage_vocno'}
    with get_conn() as conn:
        stage_cols = {r['name'] for r in conn.execute('PRAGMA table_info(voc_stage_info)').fetchall()}
        conn.execute('DELETE FROM voc_stage_info WHERE vocno=?', (vocno,))
        for s in stages:
            row = {
                'vocno':         vocno,
                'stage_index':   s.get('stage_index', 0),
                'uppervocno':    s.get('uppervocno', ''),
                'vocstatuscode': s.get('vocstatuscode', ''),
                'vocstatusname': s.get('vocstatusname', ''),
                'voctypename':   s.get('voctypename', ''),
                'voctypecode':   s.get('voctypecode', ''),
            }
            stage_data = s.get('stage_data', {})
            if 'stage_vocno' in stage_cols and 'vocno' in stage_data:
                row['stage_vocno'] = str(stage_data.get('vocno', '') or '')
            for key, val in stage_data.items():
                if key in stage_cols and key not in row:
                    row[key] = str(val or '').strip()
            col_names = [c for c in row.keys() if c in stage_cols]
            vals = [row[c] for c in col_names]
            conn.execute(
                f'INSERT INTO voc_stage_info ({",".join(col_names)}) VALUES ({",".join("?"*len(col_names))})',
                vals
            )
    if stages:
        last = stages[-1]
        save_voc_info(vocno, {
            'vocstatuscode': last.get('vocstatuscode', ''),
            'vocstatusnm':   last.get('vocstatusname', ''),
        })


def get_voc_stages(vocno):
    _META = {'id', 'vocno', 'stage_index', 'uppervocno', 'vocstatuscode', 'vocstatusname',
             'voctypename', 'voctypecode', 'stage_vocno'}
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM voc_stage_info WHERE vocno=? ORDER BY stage_index ASC',
            (vocno,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d['stage_data'] = {k: v for k, v in d.items() if k not in _META}
        result.append(d)
    return result


def create_voc(data, stages=None):
    images             = data.get('images', [])
    forced_assignee_id = data.get('forced_assignee_id')
    category           = str(data.get('category', '') or '').strip()
    vocno              = str(data.get('voc_number', '') or '').strip()

    if not vocno:
        vocno = 'VOC_' + _dt.now().strftime('%Y%m%d%H%M%S%f')[:20]

    if forced_assignee_id:
        assign_result = {'assignee_id': int(forced_assignee_id), 'type': 'forced', 'skipped': []}
        _asgn.add_hold(int(forced_assignee_id))
    else:
        assign_result = _asgn.auto_assign(category)

    assignee_id = assign_result['assignee_id']

    _SKIP = {'vocno', 'assignee_id', 'created_at', 'updated_at',
             'images', 'forced_assignee_id', 'voc_number', 'id', 'voc_id'}

    with get_conn() as conn:
        valid_cols = {r['name'] for r in conn.execute('PRAGMA table_info(voc_info)').fetchall()}

        insert_cols = ['vocno', 'assignee_id']
        insert_vals = [vocno, assignee_id]
        for key, val in data.items():
            if key in _SKIP or key not in valid_cols:
                continue
            insert_cols.append(key)
            insert_vals.append(str(val or '').strip())

        placeholders = ','.join('?' * len(insert_cols))
        conn.execute(
            f"INSERT OR REPLACE INTO voc_info ({','.join(insert_cols)}) VALUES ({placeholders})",
            insert_vals
        )

        if assignee_id:
            conn.execute(
                'INSERT INTO assignment_history (vocno, assignee_id, note, assignment_type) VALUES (?,?,?,?)',
                (vocno, assignee_id,
                 _TYPE_NOTE.get(assign_result['type'], '배정'),
                 assign_result['type'])
            )

        for skipped in assign_result.get('skipped', []):
            conn.execute(
                'INSERT INTO assignment_history (vocno, assignee_id, note, assignment_type) VALUES (?,?,?,?)',
                (vocno, skipped['id'],
                 f'{skipped["name"]} 순번 보류 (지정 배정 패널티)',
                 'skipped')
            )

        row = conn.execute('''
            SELECT vi.*, a.name as assignee_name, a.avatar as assignee_avatar
            FROM voc_info vi LEFT JOIN assignees a ON vi.assignee_id = a.id
            WHERE vi.vocno = ?
        ''', (vocno,)).fetchone()

    if images:
        image_search.save_voc_images(vocno, vocno, images)

    save_voc_info(vocno, data)

    if stages:
        save_voc_stages(vocno, stages)
        _update_status_from_last_stage(vocno, stages[-1].get('vocstatuscode', ''))

    return {'success': True, 'voc': dict(row), 'assign_info': assign_result}


def get_vocs(status=None, search=None, assignee_id=None, category=None,
             date_from=None, date_to=None, category_parent=None, process_type=None):
    query = '''
        SELECT vi.*, a.name as assignee_name, a.avatar as assignee_avatar
        FROM voc_info vi LEFT JOIN assignees a ON vi.assignee_id = a.id
        WHERE 1=1
    '''
    params = []

    if status == 'active':
        with get_conn() as _c:
            _rows = _c.execute(
                "SELECT value FROM type_items WHERE group_code='voc_status' AND is_active=1 AND value!=''"
            ).fetchall()
        _vals = [r['value'] for r in _rows]
        if _vals:
            ph = ','.join('?' * len(_vals))
            query += f" AND COALESCE(NULLIF(vi.vocstatuscode,''), vi.status) IN ({ph})"
            params.extend(_vals)
        else:
            query += " AND COALESCE(NULLIF(vi.vocstatuscode,''), vi.status) IN ('open','in_progress')"
    elif status and status != 'all':
        query += " AND COALESCE(NULLIF(vi.vocstatuscode,''), vi.status) = ?"
        params.append(status)

    if search and search.strip():
        query += ' AND (vi.title LIKE ? OR vi.content LIKE ? OR vi.category LIKE ? OR vi.vocno LIKE ?)'
        s = f'%{search.strip()}%'
        params.extend([s, s, s, s])

    if date_from:
        query += " AND DATE(vi.created_at) >= ?"
        params.append(date_from)

    if date_to:
        query += " AND DATE(vi.created_at) <= ?"
        params.append(date_to)

    if category and category != 'all':
        query += ' AND vi.category = ?'
        params.append(category)
    elif category_parent and category_parent != 'all':
        query += '''
            AND vi.category IN (
                SELECT ti.name FROM type_items ti
                WHERE ti.group_code='category' AND (
                    ti.name=? OR ti.parent_id=(
                        SELECT id FROM type_items WHERE group_code='category' AND name=? AND parent_id IS NULL
                    )
                )
            )
        '''
        params.extend([category_parent, category_parent])

    if process_type and process_type != 'all':
        query += ' AND vi.process_type = ?'
        params.append(process_type)

    if assignee_id and assignee_id != 'all':
        if assignee_id == 'unassigned':
            query += ' AND vi.assignee_id IS NULL'
        else:
            query += ' AND vi.assignee_id = ?'
            params.append(int(assignee_id))

    query += ' ORDER BY vi.created_at DESC'

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
            "SELECT DISTINCT strftime('%Y', created_at) as yr FROM voc_info ORDER BY yr DESC"
        ).fetchall()
    return [r['yr'] for r in rows if r['yr']]


def update_status(vocno, status):
    with get_conn() as conn:
        conn.execute(
            "UPDATE voc_info SET status=?, vocstatuscode=?, updated_at=datetime('now','localtime') WHERE vocno=?",
            (status, status, vocno)
        )
    return {'success': True}


def _strip_html(text):
    return re.sub(r'<[^>]+>', ' ', str(text or ''))


def get_similar(title, content, limit=5, exclude_vocno=None):
    text = f'{_strip_html(title)} {_strip_html(content)}'
    words = set(re.findall(r'[가-힣a-zA-Z0-9]{2,}', text))

    if not words:
        return []

    with get_conn() as conn:
        if exclude_vocno:
            rows = conn.execute('''
                SELECT vi.*, a.name as assignee_name, a.avatar as assignee_avatar
                FROM voc_info vi LEFT JOIN assignees a ON vi.assignee_id = a.id
                WHERE vi.vocno != ?
            ''', (exclude_vocno,)).fetchall()
        else:
            rows = conn.execute('''
                SELECT vi.*, a.name as assignee_name, a.avatar as assignee_avatar
                FROM voc_info vi LEFT JOIN assignees a ON vi.assignee_id = a.id
            ''').fetchall()

    scored = []
    for row in rows:
        row_words = set(re.findall(r'[가-힣a-zA-Z0-9]{2,}', f'{_strip_html(row["title"])} {_strip_html(row["content"])}'))
        overlap = len(words & row_words)
        if overlap > 0:
            scored.append((overlap, dict(row)))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:limit]]


def add_note(vocno, content, note_date='', work_minutes=0, note_type='answer'):
    if not content.strip():
        return {'success': False, 'error': '내용을 입력하세요.'}
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO voc_notes (vocno, content, note_date, work_minutes, note_type) VALUES (?, ?, ?, ?, ?)',
            (vocno, content.strip(), note_date or '', int(work_minutes) if work_minutes else 0, note_type or 'answer')
        )
    return {'success': True}


def get_notes(vocno, note_type=None):
    with get_conn() as conn:
        if note_type:
            rows = conn.execute(
                'SELECT * FROM voc_notes WHERE vocno=? AND note_type=? ORDER BY created_at',
                (vocno, note_type)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM voc_notes WHERE vocno=? ORDER BY created_at',
                (vocno,)
            ).fetchall()
    return [dict(r) for r in rows]


def get_status_summary(assignee_id=None, date_from=None, date_to=None):
    query = '''
        SELECT COALESCE(NULLIF(vocstatuscode,''), status, 'unknown') as status,
               COUNT(*) as cnt
        FROM voc_info WHERE 1=1
    '''
    params = []
    if assignee_id and assignee_id != 'all':
        if assignee_id == 'unassigned':
            query += ' AND assignee_id IS NULL'
        else:
            query += ' AND assignee_id = ?'
            params.append(int(assignee_id))
    if date_from:
        query += ' AND DATE(created_at) >= ?'
        params.append(date_from)
    if date_to:
        query += ' AND DATE(created_at) <= ?'
        params.append(date_to)
    query += ' GROUP BY 1'
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    by_status = {r['status']: r['cnt'] for r in rows}
    return {'total': sum(by_status.values()), 'by_status': by_status}


def get_stats(period_type='monthly', date_from=None, date_to=None):
    if period_type == 'monthly':
        period_sql = "strftime('%Y-%m', created_at)"
    else:
        period_sql = "strftime('%Y-W%W', created_at)"

    where, params = [], []
    if date_from:
        where.append("DATE(created_at) >= ?"); params.append(date_from)
    if date_to:
        where.append("DATE(created_at) <= ?"); params.append(date_to)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    with get_conn() as conn:
        rows = conn.execute(f'''
            SELECT {period_sql} as period,
                   COALESCE(NULLIF(TRIM(category), ''), '기타') as cat,
                   COUNT(*) as cnt
            FROM voc_info
            {where_clause}
            GROUP BY period, cat
            ORDER BY period DESC, cnt DESC
        ''', params).fetchall()

    from collections import OrderedDict
    periods = OrderedDict()
    for r in rows:
        p = r['period']
        if p not in periods:
            periods[p] = {'period': p, 'total': 0, 'categories': []}
        periods[p]['total'] += r['cnt']
        periods[p]['categories'].append({'category': r['cat'], 'count': r['cnt']})

    return list(periods.values())


def get_assignee_stats(date_from=None, date_to=None):
    where, params = [], []
    if date_from:
        where.append("DATE(vi.created_at) >= ?"); params.append(date_from)
    if date_to:
        where.append("DATE(vi.created_at) <= ?"); params.append(date_to)
    extra = ("AND " + " AND ".join(where)) if where else ""

    with get_conn() as conn:
        asgns = conn.execute(
            'SELECT id, name, active, avatar FROM assignees ORDER BY turn_order ASC, name ASC'
        ).fetchall()
        rows = conn.execute(f'''
            SELECT vi.assignee_id,
                   COALESCE(NULLIF(vi.vocstatuscode,''), vi.status) as status,
                   COUNT(*) as cnt
            FROM voc_info vi
            WHERE vi.assignee_id IS NOT NULL {extra}
            GROUP BY vi.assignee_id, 2
        ''', params).fetchall()

    counts = {}
    all_statuses = []
    seen_statuses = set()
    for r in rows:
        aid = r['assignee_id']
        if aid not in counts:
            counts[aid] = {}
        counts[aid][r['status']] = r['cnt']
        if r['status'] not in seen_statuses:
            seen_statuses.add(r['status'])
            all_statuses.append(r['status'])

    result = []
    for a in asgns:
        d = dict(a)
        d['status_counts'] = counts.get(a['id'], {})
        d['total'] = sum(d['status_counts'].values())
        result.append(d)

    return {'assignees': result, 'all_statuses': all_statuses}


def sync_statuses():
    from backend import scraper as _scraper
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT vocno, COALESCE(NULLIF(vocstatuscode,''), status) as status FROM voc_info"
        ).fetchall()
    voc_list = [{'id': r['vocno'], 'voc_number': r['vocno'], 'status': r['status']} for r in rows]

    result = _scraper.sync_statuses(voc_list)
    if not result['success']:
        return result

    if result['updated']:
        with get_conn() as conn:
            for item in result['updated']:
                conn.execute(
                    "UPDATE voc_info SET status=?, updated_at=datetime('now','localtime') WHERE vocno=?",
                    (item['new'], item['id'])
                )
    return result


def update_from_sync(vocno, data, stages=None):
    _EXCLUDE = {'vocno', 'assignee_id', 'created_at', 'updated_at',
                'images', 'voc_number', 'id', 'voc_id'}
    with get_conn() as conn:
        col_rows = conn.execute('PRAGMA table_info(voc_info)').fetchall()
        valid_cols = {r['name'] for r in col_rows}

    fields, params = [], []
    for key, val in data.items():
        if key in _EXCLUDE or key not in valid_cols:
            continue
        fields.append(f'{key} = ?')
        params.append(str(val or '').strip())

    if fields:
        params.append(vocno)
        with get_conn() as conn:
            conn.execute(
                f"UPDATE voc_info SET {', '.join(fields)}, updated_at=datetime('now','localtime') WHERE vocno=?",
                params
            )

    save_voc_info(vocno, data)

    if stages is not None:
        save_voc_stages(vocno, stages)
        if stages:
            _update_status_from_last_stage(vocno, stages[-1].get('vocstatuscode', ''))

    if not fields and stages is None:
        return {'success': False, 'error': '업데이트할 데이터가 없습니다.'}
    return {'success': True}


def get_daily_report():
    from datetime import date
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT vi.vocno, vi.title, vi.due_date,
                   COALESCE(NULLIF(vi.vocstatuscode,''), vi.status) as status,
                   a.name as assignee_name
            FROM voc_info vi
            LEFT JOIN assignees a ON vi.assignee_id = a.id
            WHERE COALESCE(NULLIF(vi.vocstatuscode,''), vi.status) NOT IN ('closed')
            ORDER BY
                CASE WHEN vi.due_date = '' OR vi.due_date IS NULL THEN 1 ELSE 0 END,
                vi.due_date ASC,
                vi.created_at ASC
        ''').fetchall()

    today = date.today().strftime('%Y-%m-%d')
    lines = [f'[VOC 처리 현황] {today}', '']

    for r in rows:
        num = r['vocno'] or '-'
        due = r['due_date'] or '-'
        assignee = r['assignee_name'] or '미배정'
        lines.append(f'• [{num}] {r["title"]}')
        lines.append(f'  담당: {assignee}  |  완료요청: {due}  |  상태: {r["status"]}')

    lines.extend(['', f'총 {len(rows)}건'])
    return '\n'.join(lines)
