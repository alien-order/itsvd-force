"""
테스트 VOC 생성 스크립트 (3단계)
실행: python create_test_voc.py
"""
import sqlite3, os, sys

DB_PATH = os.path.join(os.path.dirname(__file__), 'voc.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def main():
    with get_conn() as conn:
        # 1. voc_status 항목 show_as_tab 활성화 (접수, 처리중, 해결)
        conn.execute(
            "UPDATE type_items SET show_as_tab=1 WHERE group_code='voc_status' AND value IN ('open','in_progress','resolved')"
        )
        print("show_as_tab 설정 완료 (접수, 처리중, 해결)")

        # 2. 담당자 확인
        assignee = conn.execute("SELECT id, name FROM assignees WHERE active=1 LIMIT 1").fetchone()
        assignee_id = assignee['id'] if assignee else None
        print(f"담당자: {assignee['name'] if assignee else '없음 (미배정)'}")

        # 3. VOC 생성
        cur = conn.execute(
            """INSERT INTO vocs (title, content, category, priority, status, assignee_id, voc_number, requester, due_date, process_type)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                '[테스트] 네트워크 접속 오류 문의',
                '안녕하세요. 사내 네트워크 접속 시 간헐적으로 오류가 발생합니다.\n'
                '증상: 오전 9~10시 사이에 인터넷 연결이 끊기는 현상이 반복됩니다.\n'
                '사용 환경: Windows 11, 유선 LAN\n'
                '시급히 해결 부탁드립니다.',
                '네트워크',
                'high',
                'in_progress',
                assignee_id,
                'TEST-2026-001',
                '홍길동',
                '2026-05-10',
                '장애처리',
            )
        )
        voc_id = cur.lastrowid
        print(f"VOC 생성: id={voc_id}")

        # 4. voc_info (부모 정보)
        cols = {r['name'] for r in conn.execute('PRAGMA table_info(voc_info)').fetchall()}
        row = {'voc_id': voc_id, 'vocno': 'TEST-2026-001'}
        row = {k: v for k, v in row.items() if k in cols}
        col_names = list(row.keys())
        conn.execute(
            f"INSERT OR REPLACE INTO voc_info ({','.join(col_names)}) VALUES ({','.join('?'*len(col_names))})",
            list(row.values())
        )
        print(f"voc_info 저장: {row}")

        # 5. voc_stage_info (3단계)
        stage_cols = {r['name'] for r in conn.execute('PRAGMA table_info(voc_stage_info)').fetchall()}
        stages = [
            {
                'stage_index': 0,
                'uppervocno':  'TEST-2026-001',
                'vocno':       'TEST-2026-001-01',
                'stage_status': 'open',   # 접수
                'stage_data': {
                    'title':   '[테스트] 네트워크 접속 오류 문의',
                    'content': '안녕하세요. 사내 네트워크 접속 시 간헐적으로 오류가 발생합니다.\n증상: 오전 9~10시 사이에 인터넷 연결이 끊기는 현상이 반복됩니다.\n사용 환경: Windows 11, 유선 LAN',
                }
            },
            {
                'stage_index': 1,
                'uppervocno':  'TEST-2026-001',
                'vocno':       'TEST-2026-001-02',
                'stage_status': 'in_progress',  # 처리중
                'stage_data': {
                    'title':   '네트워크 장애 원인 분석',
                    'content': '원인 파악 결과: 스위치 포트 설정 오류로 확인됨.\n조치 예정: 2026-05-02 오전 중 포트 재설정 진행 예정.',
                }
            },
            {
                'stage_index': 2,
                'uppervocno':  'TEST-2026-001',
                'vocno':       'TEST-2026-001-03',
                'stage_status': 'resolved',  # 해결
                'stage_data': {
                    'title':   '네트워크 장애 처리 완료',
                    'content': '스위치 포트 재설정 완료. 이후 정상 연결 확인.\n처리일시: 2026-05-02 10:30\n담당자: 김철수',
                }
            },
        ]

        conn.execute('DELETE FROM voc_stage_info WHERE voc_id=?', (voc_id,))
        for s in stages:
            row = {
                'voc_id':       voc_id,
                'stage_index':  s['stage_index'],
                'uppervocno':   s['uppervocno'],
                'stage_status': s['stage_status'],
            }
            if 'vocno' in stage_cols:
                row['vocno'] = s['vocno']
            for key, val in s['stage_data'].items():
                if key in stage_cols and key not in row:
                    row[key] = str(val or '')
            col_names = [c for c in row.keys() if c in stage_cols]
            vals = [row[c] for c in col_names]
            conn.execute(
                f"INSERT INTO voc_stage_info ({','.join(col_names)}) VALUES ({','.join('?'*len(col_names))})",
                vals
            )
            print(f"  단계{s['stage_index']+1} 저장: {s['stage_status']} ({s['vocno']})")

        # 6. 배정 이력
        if assignee_id:
            conn.execute(
                "INSERT INTO assignment_history (voc_id, assignee_id, note, assignment_type) VALUES (?,?,?,?)",
                (voc_id, assignee_id, '자동 배정 (라운드로빈)', 'auto')
            )

    print(f"\n완료! VOC id={voc_id}, VOC번호=TEST-2026-001")
    print("앱을 열어서 '처리중인 VOC' 또는 '전체 VOC' 에서 확인하세요.")

if __name__ == '__main__':
    main()
