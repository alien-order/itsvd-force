from backend.db import get_conn


def get_all(search=None, category=None, process_type=None, voc_type=None, sub_category=None):
    q = 'SELECT * FROM knowledge WHERE 1=1'
    params = []
    if search and search.strip():
        q += ' AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)'
        s = f'%{search.strip()}%'
        params.extend([s, s, s])
    if category and category != 'all':
        q += ' AND category = ?'
        params.append(category)
    if sub_category and sub_category != 'all':
        q += ' AND sub_category = ?'
        params.append(sub_category)
    if process_type and process_type != 'all':
        q += ' AND process_type = ?'
        params.append(process_type)
    if voc_type and voc_type != 'all':
        q += ' AND voc_type = ?'
        params.append(voc_type)
    q += ' ORDER BY updated_at DESC'
    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()
    return [dict(r) for r in rows]


def get_one(kid):
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM knowledge WHERE id = ?', (kid,)).fetchone()
    return dict(row) if row else None


def create(data):
    title = data.get('title', '').strip()
    if not title:
        return {'success': False, 'error': '제목을 입력하세요.'}
    with get_conn() as conn:
        cur = conn.execute(
            'INSERT INTO knowledge (title, content, category, sub_category, tags, process_type) VALUES (?, ?, ?, ?, ?, ?)',
            (title, data.get('content', ''), data.get('category', ''),
             data.get('sub_category', ''), data.get('tags', ''), data.get('process_type', ''))
        )
    return {'success': True, 'id': cur.lastrowid}


def update(kid, data):
    with get_conn() as conn:
        conn.execute(
            "UPDATE knowledge SET title=?, content=?, category=?, sub_category=?, tags=?, process_type=?, updated_at=datetime('now','localtime') WHERE id=?",
            (data.get('title', ''), data.get('content', ''), data.get('category', ''),
             data.get('sub_category', ''), data.get('tags', ''), data.get('process_type', ''), kid)
        )
    return {'success': True}


def delete(kid):
    with get_conn() as conn:
        conn.execute('DELETE FROM knowledge WHERE id = ?', (kid,))
    return {'success': True}


def get_categories():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM knowledge WHERE category != '' ORDER BY category"
        ).fetchall()
    return [r[0] for r in rows]


def link_voc(knowledge_id, vocno):
    try:
        with get_conn() as conn:
            conn.execute(
                'INSERT OR IGNORE INTO voc_references (vocno, knowledge_id) VALUES (?, ?)',
                (vocno, knowledge_id)
            )
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def unlink_voc(knowledge_id, vocno):
    with get_conn() as conn:
        conn.execute(
            'DELETE FROM voc_references WHERE vocno = ? AND knowledge_id = ?',
            (vocno, knowledge_id)
        )
    return {'success': True}


def get_voc_knowledge(vocno):
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT k.* FROM knowledge k
            JOIN voc_references r ON r.knowledge_id = k.id
            WHERE r.vocno = ?
            ORDER BY r.created_at DESC
        ''', (vocno,)).fetchall()
    return [dict(r) for r in rows]


def get_knowledge_vocs(knowledge_id):
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT vi.vocno, vi.title,
                   COALESCE(NULLIF(vi.vocstatuscode,''), vi.status) as status,
                   a.name as assignee_name
            FROM voc_references r
            JOIN voc_info vi ON r.vocno = vi.vocno
            LEFT JOIN assignees a ON vi.assignee_id = a.id
            WHERE r.knowledge_id = ?
            ORDER BY r.created_at DESC
        ''', (knowledge_id,)).fetchall()
    return [dict(r) for r in rows]
