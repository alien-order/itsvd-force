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
            ('knowledge',          'process_type',     'TEXT DEFAULT ""'),
        ]
        for table, col, definition in migrations:
            try:
                conn.execute(f'ALTER TABLE {table} ADD COLUMN {col} {definition}')
            except Exception:
                pass
