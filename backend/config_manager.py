import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')

DEFAULT = {
    'url_pattern': '',
    'dynamic': False,
    'selectors': {
        'voc_number': '',
        'title': '',
        'content': '',
        'requester': '',
        'due_date': '',
        'status': '',
        'images': '',
    }
}


def get_config():
    if not os.path.exists(CONFIG_PATH):
        return dict(DEFAULT)
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    config = dict(DEFAULT)
    config.update(data)
    config['selectors'] = {**DEFAULT['selectors'], **data.get('selectors', {})}
    return config


def save_config(data):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {'success': True}
