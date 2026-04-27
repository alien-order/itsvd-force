import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')

_DEFAULT_SELECTORS = {
    'voc_number': '', 'title': '', 'content': '',
    'requester': '', 'due_date': '', 'status': '', 'images': '',
}
_DEFAULT_FIELD_MAP = {
    'voc_number': '', 'title': '', 'content': '',
    'requester': '', 'due_date': '', 'status': '',
}

DEFAULT = {
    'fetch_method': 'static',
    'url_pattern': '',
    'dynamic': False,
    'selectors': dict(_DEFAULT_SELECTORS),
    'xpath_wait_seconds': 3,
    'xpath_selectors': dict(_DEFAULT_SELECTORS),
    'api_url_pattern': '',
    'api_cookies': [],
    'api_field_map': dict(_DEFAULT_FIELD_MAP),
}


def get_config():
    if not os.path.exists(CONFIG_PATH):
        return dict(DEFAULT)
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    config = dict(DEFAULT)
    skip = {'selectors', 'xpath_selectors', 'api_field_map'}
    config.update({k: v for k, v in data.items() if k not in skip})
    config['selectors']       = {**_DEFAULT_SELECTORS, **data.get('selectors', {})}
    config['xpath_selectors'] = {**_DEFAULT_SELECTORS, **data.get('xpath_selectors', {})}
    config['api_field_map']   = {**_DEFAULT_FIELD_MAP, **data.get('api_field_map', {})}
    # backward compat: dynamic=True without explicit fetch_method → xpath
    if 'fetch_method' not in data and data.get('dynamic', False):
        config['fetch_method'] = 'xpath'
    return config


def save_config(data):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {'success': True}
