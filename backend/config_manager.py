import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')

_DEFAULT_SELECTORS = {
    'voc_number': '', 'title': '', 'content': '',
    'requester': '', 'due_date': '', 'status': '', 'images': '',
}

DEFAULT = {
    'api_url_pattern':     '',
    'api_token':           '',
    'api_list_path':       '',
    'api_field_map':       [],
    'api_child_field_map': [],
}


def _normalize_field_map(raw):
    """Dict(구형) 또는 list(신형) 모두 list[{col,path}] 형태로 정규화."""
    if isinstance(raw, list):
        return [x for x in raw if x.get('col')]
    if isinstance(raw, dict):
        return [{'col': k, 'path': v} for k, v in raw.items() if v]
    return []


def get_config():
    if not os.path.exists(CONFIG_PATH):
        return dict(DEFAULT)
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    config = dict(DEFAULT)
    config['api_url_pattern']     = data.get('api_url_pattern', '')
    config['api_token']           = data.get('api_token', '')
    config['api_list_path']       = data.get('api_list_path', '')
    config['api_field_map']       = _normalize_field_map(data.get('api_field_map', []))
    config['api_child_field_map'] = _normalize_field_map(data.get('api_child_field_map', []))
    return config


def save_config(data):
    if 'api_field_map' in data:
        data['api_field_map'] = _normalize_field_map(data['api_field_map'])
    if 'api_child_field_map' in data:
        data['api_child_field_map'] = _normalize_field_map(data['api_child_field_map'])
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {'success': True}


def get_voc_columns():
    from backend.db import get_conn
    _EXCLUDE = {'id', 'created_at', 'updated_at', 'assignee_id'}
    with get_conn() as conn:
        rows = conn.execute('PRAGMA table_info(vocs)').fetchall()
    return [r['name'] for r in rows if r['name'] not in _EXCLUDE]
