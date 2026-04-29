import requests
from backend.config_manager import get_config


def _normalize_field_map(raw):
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return [{'col': k, 'path': v} for k, v in raw.items() if v]
    return []


def _make_headers(config):
    token = config.get('api_token', '').strip()
    return {'X-Auth-Token': token} if token else {}


def _extract_json(json_data, json_path):
    val = json_data
    for key in (json_path or '').strip().split('.'):
        if not key:
            continue
        val = val.get(key, '') if isinstance(val, dict) else ''
    return str(val).strip() if val is not None else ''


def _extract_obj(json_data, path):
    val = json_data
    for key in (path or '').strip().split('.'):
        if not key:
            continue
        val = val.get(key, {}) if isinstance(val, dict) else {}
    return val if isinstance(val, dict) else {}


def _extract_list(json_data, path):
    val = json_data
    for key in (path or '').strip().split('.'):
        if not key:
            continue
        val = val.get(key, []) if isinstance(val, dict) else []
    return val if isinstance(val, list) else []


def fetch_voc(voc_number):
    config  = get_config()
    api_url = config.get('api_url_pattern', '').strip()
    if not api_url:
        return {'success': False, 'error': 'API URL 패턴이 설정되지 않았습니다. 설정 탭에서 입력해주세요.'}

    url     = api_url.replace('{number}', str(voc_number))
    headers = _make_headers(config)

    try:
        resp = requests.get(url, headers=headers, timeout=15, verify=False)
        resp.raise_for_status()
        json_data = resp.json()
    except requests.RequestException as e:
        return {'success': False, 'error': f'API 요청 실패: {e}'}
    except ValueError as e:
        return {'success': False, 'error': f'JSON 파싱 실패: {e}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

    # ── 부모 데이터 추출 (vocInfo)
    parent_path = config.get('api_parent_data_path', '').strip()
    parent_json = _extract_obj(json_data, parent_path) if parent_path else json_data

    field_map = _normalize_field_map(config.get('api_field_map', []))
    data = {'images': []}
    for item in field_map:
        col       = item.get('col', '').strip()
        json_path = item.get('path', '').strip()
        if not col or not json_path:
            continue
        data[col] = _extract_json(parent_json, json_path)

    # ── 단계 데이터 추출 (vocInfoList)
    list_path        = config.get('api_list_path', '').strip()
    child_field_map  = _normalize_field_map(config.get('api_child_field_map', []))
    stage_status_col = (config.get('api_stage_status_col', '') or 'stage_status').strip()

    stage_list = _extract_list(json_data, list_path) if list_path else []
    stages = []
    for i, stage_item in enumerate(stage_list):
        if not isinstance(stage_item, dict):
            continue
        stage_data = {}
        for m in child_field_map:
            col       = m.get('col', '').strip()
            json_path = m.get('path', '').strip()
            if not col or not json_path:
                continue
            stage_data[col] = _extract_json(stage_item, json_path)

        uppervocno   = str(stage_item.get('uppervocno', '') or '')
        stage_status = str(stage_data.get(stage_status_col, '') or '')

        stages.append({
            'stage_index':  i,
            'uppervocno':   uppervocno,
            'stage_status': stage_status,
            'stage_data':   stage_data,
        })

    if not any(v for k, v in data.items() if k != 'images') and not stages:
        return {'success': False, 'error': 'API 응답에서 데이터를 찾지 못했습니다. 필드 매핑을 확인하세요.'}

    return {'success': True, 'data': data, 'stages': stages}


# ── 상태 동기화 ─────────────────────────────────────────────────

_STATUS_KEYWORDS = [
    ('처리완료', 'resolved'),
    ('처리중',   'in_progress'),
    ('처리 중',  'in_progress'),
    ('진행중',   'in_progress'),
    ('진행 중',  'in_progress'),
    ('해결',     'resolved'),
    ('완료',     'resolved'),
    ('종료',     'closed'),
    ('취소',     'closed'),
    ('접수',     'open'),
    ('신규',     'open'),
    ('대기',     'open'),
]


def _map_status(text):
    t = text.strip()
    for keyword, status in _STATUS_KEYWORDS:
        if keyword in t:
            return status
    return None


def sync_statuses(voc_list):
    config  = get_config()
    api_url = config.get('api_url_pattern', '').strip()
    if not api_url:
        return {'success': False, 'error': 'API URL 패턴이 설정되지 않았습니다.'}

    field_map = _normalize_field_map(config.get('api_field_map', []))
    status_path = next((x.get('path', '') for x in field_map if x.get('col') == 'status'), '')
    if not status_path.strip():
        return {'success': False, 'error': 'status 필드 매핑이 설정되지 않았습니다.'}

    headers = _make_headers(config)
    updated, failed = [], []

    for item in voc_list:
        voc_number = item.get('voc_number') or str(item['id'])
        try:
            url  = api_url.replace('{number}', str(voc_number))
            resp = requests.get(url, headers=headers, timeout=15, verify=False)
            resp.raise_for_status()
            json_data  = resp.json()
            new_status = _map_status(_extract_json(json_data, status_path))

            if new_status and new_status != item['status']:
                updated.append({'id': item['id'], 'voc_number': voc_number,
                                 'old': item['status'], 'new': new_status})
            elif not new_status:
                failed.append(voc_number)
        except Exception:
            failed.append(voc_number)

    return {'success': True, 'updated': updated, 'failed': failed}
