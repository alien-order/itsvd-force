import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'voc.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS assignees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS vocs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT DEFAULT '',
                priority TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'open',
                assignee_id INTEGER,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (assignee_id) REFERENCES assignees(id)
            );

            CREATE TABLE IF NOT EXISTS assignment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voc_id INTEGER NOT NULL,
                assignee_id INTEGER NOT NULL,
                assigned_at TEXT DEFAULT (datetime('now', 'localtime')),
                note TEXT DEFAULT '',
                FOREIGN KEY (voc_id) REFERENCES vocs(id),
                FOREIGN KEY (assignee_id) REFERENCES assignees(id)
            );

            CREATE TABLE IF NOT EXISTS voc_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voc_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (voc_id) REFERENCES vocs(id)
            );
        ''')
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS voc_images (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                voc_id     INTEGER NOT NULL,
                filename   TEXT NOT NULL,
                phash      TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (voc_id) REFERENCES vocs(id)
            );
        ''')
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL,
                content    TEXT NOT NULL,
                category   TEXT DEFAULT '',
                tags       TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS board_posts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL,
                content    TEXT NOT NULL,
                category   TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS board_files (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id       INTEGER NOT NULL,
                original_name TEXT NOT NULL,
                saved_name    TEXT NOT NULL,
                file_size     INTEGER DEFAULT 0,
                created_at    TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (post_id) REFERENCES board_posts(id)
            );
        ''')
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS voc_references (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                voc_id       INTEGER NOT NULL,
                knowledge_id INTEGER NOT NULL,
                created_at   TEXT DEFAULT (datetime('now', 'localtime')),
                UNIQUE(voc_id, knowledge_id),
                FOREIGN KEY (voc_id)       REFERENCES vocs(id),
                FOREIGN KEY (knowledge_id) REFERENCES knowledge(id)
            );
        ''')
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS assignment_rules (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category    TEXT NOT NULL UNIQUE,
                assignee_id INTEGER NOT NULL,
                note        TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (assignee_id) REFERENCES assignees(id)
            );

            CREATE TABLE IF NOT EXISTS system_config (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS vacations (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                assignee_id      INTEGER NOT NULL,
                vacation_date    TEXT NOT NULL,
                vacation_type    TEXT NOT NULL,
                assignments_missed INTEGER DEFAULT 0,
                processed        INTEGER DEFAULT 0,
                created_at       TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (assignee_id) REFERENCES assignees(id)
            );

            CREATE TABLE IF NOT EXISTS categories (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS process_types (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS type_groups (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                code       TEXT NOT NULL UNIQUE,
                label      TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS type_items (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                group_code TEXT NOT NULL,
                name       TEXT NOT NULL,
                value      TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                UNIQUE(group_code, name)
            );
        ''')
        # Seed default type groups
        for code, label, order in [('category','업무유형',1),('process_type','VOC유형',2),('voc_status','VOC 상태',3)]:
            try:
                conn.execute('INSERT OR IGNORE INTO type_groups (code,label,sort_order) VALUES (?,?,?)',(code,label,order))
            except Exception:
                pass
        # Seed voc_status items only if the group is completely empty
        existing_count = conn.execute(
            "SELECT COUNT(*) FROM type_items WHERE group_code='voc_status'"
        ).fetchone()[0]
        if existing_count == 0:
            for name, value, order in [('접수','open',1),('처리중','in_progress',2),('해결','resolved',3),('종료','closed',4)]:
                try:
                    conn.execute('INSERT INTO type_items (group_code,name,value,sort_order) VALUES (?,?,?,?)',('voc_status',name,value,order))
                except Exception:
                    pass
        conn.executescript('')  # flush
        # 마이그레이션: '카테고리' → '업무유형', '처리유형' → 'VOC유형'
        conn.execute("UPDATE type_groups SET label='업무유형' WHERE code='category' AND label='카테고리'")
        conn.execute("UPDATE type_groups SET label='VOC유형' WHERE code='process_type' AND label='처리유형'")
        # voc_type 그룹 제거 (process_type이 VOC유형으로 통합됨)
        conn.execute("DELETE FROM type_groups WHERE code='voc_type'")
        # voc_info: VOC 부모 기본정보 테이블 (API vocInfo → 여기 저장)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS voc_info (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                voc_id INTEGER NOT NULL UNIQUE,
                vocno  TEXT DEFAULT '',
                FOREIGN KEY (voc_id) REFERENCES vocs(id)
            )
        ''')
        # voc_stage_info: VOC 단계별 정보 테이블 (API vocInfoList → 여기 저장)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS voc_stage_info (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                voc_id       INTEGER NOT NULL,
                stage_index  INTEGER DEFAULT 0,
                vocno        TEXT DEFAULT '',
                uppervocno   TEXT DEFAULT '',
                stage_status TEXT DEFAULT '',
                FOREIGN KEY (voc_id) REFERENCES vocs(id)
            )
        ''')
        # voc_stages: 이전 호환용 (사용 중단, voc_stage_info로 대체)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS voc_stages (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                voc_id       INTEGER NOT NULL,
                stage_index  INTEGER DEFAULT 0,
                uppervocno   TEXT DEFAULT '',
                stage_status TEXT DEFAULT '',
                stage_data   TEXT DEFAULT '{}',
                FOREIGN KEY (voc_id) REFERENCES vocs(id)
            )
        ''')
        # migration: add new columns to existing tables
        migrations = [
            ('vocs',               'voc_number',       'TEXT DEFAULT ""'),
            ('vocs',               'requester',        'TEXT DEFAULT ""'),
            ('vocs',               'due_date',         'TEXT DEFAULT ""'),
            ('assignees',          'turn_order',       'INTEGER DEFAULT 0'),
            ('assignees',          'hold_turns',       'INTEGER DEFAULT 0'),
            ('assignees',          'priority_next',    'INTEGER DEFAULT 0'),
            ('assignment_history', 'assignment_type',  'TEXT DEFAULT "auto"'),
            ('voc_notes',          'note_date',        'TEXT DEFAULT ""'),
            ('voc_notes',          'work_minutes',     'INTEGER DEFAULT 0'),
            ('voc_notes',          'note_type',        'TEXT DEFAULT "answer"'),
            ('knowledge',          'process_type',     'TEXT DEFAULT ""'),
            ('knowledge',          'voc_type',         'TEXT DEFAULT ""'),
            ('knowledge',          'sub_category',     'TEXT DEFAULT ""'),
            ('type_items',         'parent_id',        'INTEGER DEFAULT NULL'),
            ('assignees',          'knox_id',          'TEXT DEFAULT NULL'),
            ('assignees',          'ip_address',       'TEXT DEFAULT ""'),
            ('assignees',          'avatar',           'TEXT DEFAULT ""'),
            ('vocs',               'process_type',     'TEXT DEFAULT ""'),
            ('type_items',         'show_as_tab',      'INTEGER DEFAULT 0'),
            ('type_items',         'is_active',        'INTEGER DEFAULT 0'),
            # voc_info 추가 컬럼
            ('voc_info',           'sysbizcode',       'TEXT DEFAULT ""'),
            ('voc_info',           'sysbizcode1',      'TEXT DEFAULT ""'),
            ('voc_info',           'register_singleid','TEXT DEFAULT ""'),
            ('voc_info',           'writer_singleid',  'TEXT DEFAULT ""'),
            ('voc_info',           'endplandate',      'TEXT DEFAULT ""'),
            ('voc_info',           'endplantime',      'TEXT DEFAULT ""'),
            ('voc_info',           'vocstatuscode',    'TEXT DEFAULT ""'),
            ('voc_info',           'vocstatusnm',      'TEXT DEFAULT ""'),
            ('voc_info',           'voctypecode',      'TEXT DEFAULT ""'),
            # voc_stage_info 추가 컬럼
            ('voc_stage_info',     'vocstatusname',    'TEXT DEFAULT ""'),
            ('voc_stage_info',     'voctypename',      'TEXT DEFAULT ""'),
            ('voc_stage_info',     'voctypecode',      'TEXT DEFAULT ""'),
            # vocs 추가 컬럼 (리스트 카드 표시용)
            ('vocs',               'sysbizcode',       'TEXT DEFAULT ""'),
            ('vocs',               'sysbizcode1',      'TEXT DEFAULT ""'),
        ]
        for table, col, definition in migrations:
            try:
                conn.execute(f'ALTER TABLE {table} ADD COLUMN {col} {definition}')
            except Exception:
                pass
        # type_items UNIQUE 제약 완화: (group_code, name) → (group_code, name, parent_id)로 마이그레이션
        # 마커 테이블로 중복 실행 방지
        marker = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='_ti_constraint_v2'"
        ).fetchone()[0]
        if not marker:
            try:
                conn.execute('''
                    CREATE TABLE type_items_v2 (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        group_code  TEXT NOT NULL,
                        name        TEXT NOT NULL,
                        value       TEXT DEFAULT '',
                        sort_order  INTEGER DEFAULT 0,
                        created_at  TEXT DEFAULT (datetime('now','localtime')),
                        parent_id   INTEGER DEFAULT NULL,
                        show_as_tab INTEGER DEFAULT 0,
                        is_active   INTEGER DEFAULT 0
                    )
                ''')
                conn.execute('INSERT INTO type_items_v2 SELECT * FROM type_items')
                conn.execute('DROP TABLE type_items')
                conn.execute('ALTER TABLE type_items_v2 RENAME TO type_items')
                conn.execute('CREATE TABLE _ti_constraint_v2 (done INTEGER DEFAULT 1)')
            except Exception:
                try:
                    conn.execute('DROP TABLE IF EXISTS type_items_v2')
                except Exception:
                    pass

        # assignee_categories: 담당자별 담당 업무유형 (parent category)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS assignee_categories (
                assignee_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                PRIMARY KEY (assignee_id, category_id),
                FOREIGN KEY (assignee_id) REFERENCES assignees(id)
            )
        ''')

        # vacation_type_config: 휴가 유형별 배정 설정
        conn.execute('''
            CREATE TABLE IF NOT EXISTS vacation_type_config (
                vacation_type  TEXT PRIMARY KEY,
                time_start     TEXT DEFAULT '00:00',
                time_end       TEXT DEFAULT '23:59',
                n_rounds       INTEGER DEFAULT 0,
                assign_during  INTEGER DEFAULT 0
            )
        ''')
        for vt, ts, te in [('연차','00:00','23:59'), ('오전반차','00:00','12:00'), ('오후반차','13:00','23:59')]:
            conn.execute(
                'INSERT OR IGNORE INTO vacation_type_config (vacation_type,time_start,time_end) VALUES (?,?,?)',
                (vt, ts, te)
            )

        # vacations: cat_counts 컬럼 추가
        try:
            conn.execute("ALTER TABLE vacations ADD COLUMN cat_counts TEXT DEFAULT '{}'")
        except Exception:
            pass

        # voc_stage_info: stage_status → vocstatuscode (API 원본 키 그대로 사용)
        try:
            conn.execute('ALTER TABLE voc_stage_info RENAME COLUMN stage_status TO vocstatuscode')
        except Exception:
            pass

        # vocs: title/content NOT NULL → DEFAULT '' 로 변경 (config 기반 동적 INSERT 지원)
        _vocs_needs_migrate = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='_vocs_default_v1'"
        ).fetchone()[0] == 0
        if _vocs_needs_migrate:
            try:
                conn.execute('PRAGMA foreign_keys=OFF')
                conn.execute('''
                    CREATE TABLE vocs_new (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        title        TEXT NOT NULL DEFAULT '',
                        content      TEXT NOT NULL DEFAULT '',
                        category     TEXT DEFAULT '',
                        priority     TEXT DEFAULT 'normal',
                        status       TEXT DEFAULT 'open',
                        assignee_id  INTEGER,
                        created_at   TEXT DEFAULT (datetime('now','localtime')),
                        updated_at   TEXT DEFAULT (datetime('now','localtime')),
                        voc_number   TEXT DEFAULT '',
                        requester    TEXT DEFAULT '',
                        due_date     TEXT DEFAULT '',
                        process_type TEXT DEFAULT '',
                        sysbizcode   TEXT DEFAULT '',
                        sysbizcode1  TEXT DEFAULT ''
                    )
                ''')
                conn.execute('''
                    INSERT INTO vocs_new
                    SELECT id,
                           COALESCE(title,''), COALESCE(content,''), COALESCE(category,''),
                           COALESCE(priority,'normal'), COALESCE(status,'open'), assignee_id,
                           created_at, updated_at,
                           COALESCE(voc_number,''), COALESCE(requester,''),
                           COALESCE(due_date,''), COALESCE(process_type,''),
                           COALESCE(sysbizcode,''), COALESCE(sysbizcode1,'')
                    FROM vocs
                ''')
                conn.execute('DROP TABLE vocs')
                conn.execute('ALTER TABLE vocs_new RENAME TO vocs')
                conn.execute('CREATE TABLE _vocs_default_v1 (done INTEGER DEFAULT 1)')
                conn.execute('PRAGMA foreign_keys=ON')
            except Exception:
                try:
                    conn.execute('DROP TABLE IF EXISTS vocs_new')
                    conn.execute('PRAGMA foreign_keys=ON')
                except Exception:
                    pass

        # Migration: voc_info becomes the main table keyed by vocno (TEXT PK)
        _vocno_main_exists = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='_vocno_main_v1'"
        ).fetchone()[0]
        if not _vocno_main_exists:
            try:
                conn.execute('PRAGMA foreign_keys=OFF')
                conn.execute('''
                    CREATE TABLE voc_info_main (
                        vocno             TEXT PRIMARY KEY,
                        assignee_id       INTEGER,
                        priority          TEXT DEFAULT 'normal',
                        status            TEXT DEFAULT '',
                        created_at        TEXT DEFAULT (datetime('now','localtime')),
                        updated_at        TEXT DEFAULT (datetime('now','localtime')),
                        title             TEXT DEFAULT '',
                        content           TEXT DEFAULT '',
                        category          TEXT DEFAULT '',
                        requester         TEXT DEFAULT '',
                        due_date          TEXT DEFAULT '',
                        process_type      TEXT DEFAULT '',
                        vocstatuscode     TEXT DEFAULT '',
                        vocstatusnm       TEXT DEFAULT '',
                        voctypecode       TEXT DEFAULT '',
                        sysbizcode        TEXT DEFAULT '',
                        sysbizcode1       TEXT DEFAULT '',
                        register_singleid TEXT DEFAULT '',
                        writer_singleid   TEXT DEFAULT '',
                        endplandate       TEXT DEFAULT '',
                        endplantime       TEXT DEFAULT '',
                        bizNmDept         TEXT DEFAULT ''
                    )
                ''')
                try:
                    conn.execute('''
                        INSERT OR IGNORE INTO voc_info_main
                            (vocno, assignee_id, created_at, updated_at, title, content,
                             category, requester, due_date, process_type, status)
                        SELECT COALESCE(NULLIF(v.voc_number,''), CAST(v.id AS TEXT)),
                               v.assignee_id, v.created_at, v.updated_at,
                               COALESCE(v.title,''), COALESCE(v.content,''),
                               COALESCE(v.category,''), COALESCE(v.requester,''),
                               COALESCE(v.due_date,''), COALESCE(v.process_type,''),
                               COALESCE(v.status,'')
                        FROM vocs v
                    ''')
                except Exception:
                    pass
                conn.execute('DROP TABLE IF EXISTS voc_info')
                conn.execute('ALTER TABLE voc_info_main RENAME TO voc_info')
                conn.execute('DROP TABLE IF EXISTS voc_stage_info')
                conn.execute('''
                    CREATE TABLE voc_stage_info (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        vocno         TEXT NOT NULL,
                        stage_index   INTEGER DEFAULT 0,
                        stage_vocno   TEXT DEFAULT '',
                        uppervocno    TEXT DEFAULT '',
                        vocstatuscode TEXT DEFAULT '',
                        vocstatusname TEXT DEFAULT '',
                        voctypename   TEXT DEFAULT '',
                        voctypecode   TEXT DEFAULT ''
                    )
                ''')
                conn.execute('DROP TABLE IF EXISTS voc_notes')
                conn.execute('''
                    CREATE TABLE voc_notes (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        vocno        TEXT NOT NULL,
                        content      TEXT NOT NULL,
                        created_at   TEXT DEFAULT (datetime('now','localtime')),
                        note_date    TEXT DEFAULT '',
                        work_minutes INTEGER DEFAULT 0,
                        note_type    TEXT DEFAULT 'answer'
                    )
                ''')
                conn.execute('DROP TABLE IF EXISTS assignment_history')
                conn.execute('''
                    CREATE TABLE assignment_history (
                        id              INTEGER PRIMARY KEY AUTOINCREMENT,
                        vocno           TEXT NOT NULL,
                        assignee_id     INTEGER NOT NULL,
                        assigned_at     TEXT DEFAULT (datetime('now','localtime')),
                        note            TEXT DEFAULT '',
                        assignment_type TEXT DEFAULT 'auto'
                    )
                ''')
                conn.execute('DROP TABLE IF EXISTS voc_images')
                conn.execute('''
                    CREATE TABLE voc_images (
                        id         INTEGER PRIMARY KEY AUTOINCREMENT,
                        vocno      TEXT NOT NULL,
                        filename   TEXT NOT NULL,
                        phash      TEXT NOT NULL,
                        created_at TEXT DEFAULT (datetime('now','localtime'))
                    )
                ''')
                conn.execute('DROP TABLE IF EXISTS voc_references')
                conn.execute('''
                    CREATE TABLE voc_references (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        vocno        TEXT NOT NULL,
                        knowledge_id INTEGER NOT NULL,
                        created_at   TEXT DEFAULT (datetime('now','localtime')),
                        UNIQUE(vocno, knowledge_id)
                    )
                ''')
                conn.execute('DROP TABLE IF EXISTS voc_stages')
                conn.execute('CREATE TABLE _vocno_main_v1 (done INTEGER DEFAULT 1)')
                conn.execute('PRAGMA foreign_keys=ON')
            except Exception:
                try:
                    conn.execute('DROP TABLE IF EXISTS voc_info_main')
                    conn.execute('PRAGMA foreign_keys=ON')
                except Exception:
                    pass

        # custom_menus table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS custom_menus (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                label        TEXT NOT NULL,
                icon_color   TEXT DEFAULT '#6366f1',
                source_type  TEXT DEFAULT 'url',
                source_value TEXT DEFAULT '',
                section      TEXT DEFAULT '',
                sort_order   INTEGER DEFAULT 0,
                active       INTEGER DEFAULT 1,
                protected    INTEGER DEFAULT 0
            )
        ''')
        # add columns to existing custom_menus if missing
        for col, dflt in [('section', "TEXT DEFAULT ''"), ('protected', 'INTEGER DEFAULT 0')]:
            try:
                conn.execute(f'ALTER TABLE custom_menus ADD COLUMN {col} {dflt}')
            except Exception:
                pass
        # Migrate old 'builtin' source_type → 'file' with .html extension
        conn.execute(
            "UPDATE custom_menus SET source_type='file', source_value=source_value||'.html' "
            "WHERE source_type='builtin' AND source_value NOT LIKE '%.html'"
        )
        # Seed default page menus (once per page file)
        _defaults = [
            ('allvoc.html',    '전체 VOC',     '#6366f1', 'VOC',    1),
            ('active.html',    '처리중인 VOC', '#6366f1', 'VOC',    2),
            ('stats.html',     'VOC 통계',     '#6366f1', 'VOC',    3),
            ('knowledge.html', '레퍼런스',     '#8b5cf6', '지식',   4),
            ('board.html',     '공유문서',     '#8b5cf6', '지식',   5),
            ('settings.html',  '설정',         '#64748b', '시스템', 6),
        ]
        for sval, label, color, section, order in _defaults:
            exists = conn.execute(
                "SELECT COUNT(*) FROM custom_menus WHERE source_type='file' AND source_value=?", (sval,)
            ).fetchone()[0]
            if not exists:
                conn.execute(
                    'INSERT INTO custom_menus (label,icon_color,source_type,source_value,section,sort_order,active) VALUES (?,?,?,?,?,?,1)',
                    (label, color, 'file', sval, section, order)
                )
