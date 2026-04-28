"""
테스트 VOC 데이터 생성 스크립트 (~50개)
현재 DB의 업무유형, 처리유형, 담당자를 사용합니다.
"""
import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'voc.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def main():
    with get_conn() as conn:
        # process_type 컬럼이 없으면 추가
        try:
            conn.execute('ALTER TABLE vocs ADD COLUMN process_type TEXT DEFAULT ""')
            print("process_type 컬럼 추가됨")
        except Exception:
            pass

        assignees = conn.execute(
            'SELECT id, name FROM assignees WHERE active=1'
        ).fetchall()

        all_cats = conn.execute(
            "SELECT id, name, parent_id FROM type_items WHERE group_code='category' ORDER BY sort_order"
        ).fetchall()

        process_types = conn.execute(
            "SELECT name, value FROM type_items WHERE group_code='process_type' ORDER BY sort_order"
        ).fetchall()

        voc_statuses = conn.execute(
            "SELECT name, value FROM type_items WHERE group_code='voc_status' ORDER BY sort_order"
        ).fetchall()

    print(f"담당자: {[a['name'] for a in assignees]}")
    print(f"카테고리: {[c['name'] for c in all_cats]}")
    print(f"처리유형: {[p['name'] for p in process_types]}")
    print(f"VOC상태: {[v['name'] for v in voc_statuses]}")

    # 자식 카테고리 우선, 없으면 부모
    parent_ids = {c['id'] for c in all_cats if not c['parent_id']}
    child_cats = [c for c in all_cats if c['parent_id']]
    parent_cats = [c for c in all_cats if not c['parent_id']]

    category_choices = [c['name'] for c in child_cats] if child_cats else [c['name'] for c in parent_cats]
    if not category_choices:
        category_choices = ['일반']

    pt_choices = [p['value'] or p['name'] for p in process_types] if process_types else ['처리']
    status_choices = [v['value'] or v['name'] for v in voc_statuses]
    if not status_choices:
        status_choices = ['open', 'in_progress', 'resolved', 'closed']
    assignee_ids = [a['id'] for a in assignees] or [None]

    titles = [
        "로그인 오류 문의", "결제 실패 문제", "앱 실행 안됨", "비밀번호 초기화 요청",
        "구독 취소 방법", "환불 처리 문의", "배송 지연 확인", "주문 취소 요청",
        "이메일 수신 안됨", "계정 잠김 해제", "상품 정보 오류", "포인트 미적립",
        "UI 버그 신고", "성능 저하 문의", "데이터 동기화 오류", "알림 설정 오류",
        "접근권한 오류", "파일 업로드 실패", "검색 결과 오류", "리포트 생성 실패",
        "API 연동 오류", "SMS 발송 안됨", "대용량 파일 처리 오류", "세션 만료 문제",
        "모바일 앱 크래시", "PC 앱 설치 오류", "DB 조회 속도 저하", "인증서 만료 오류",
        "팝업 차단 문제", "프린트 오류", "엑셀 다운로드 실패", "PDF 변환 오류",
        "화면 깨짐 현상", "다국어 표시 오류", "날짜 형식 오류", "소수점 계산 오류",
        "권한 없는 메뉴 접근", "중복 데이터 입력 오류", "삭제 후 복구 문의",
        "배치 처리 실패", "스케줄러 미동작 오류", "캐시 갱신 안됨", "CDN 이미지 로딩 오류",
        "소셜 로그인 오류", "OTP 인증 실패", "비밀번호 정책 문의", "신규 사용자 등록 오류",
        "그룹 권한 설정 오류", "라이선스 초과 경고 메시지",
    ]

    contents = [
        "버튼 클릭 시 오류 메시지가 표시됩니다. 재현 환경: Chrome 최신버전",
        "정상적으로 처리되지 않고 에러 페이지로 이동합니다.",
        "특정 조건에서만 발생하는 문제입니다. 다른 환경에서는 정상 동작합니다.",
        "어제부터 갑자기 발생하기 시작했습니다. 이전에는 정상이었습니다.",
        "재현 방법: 1. 로그인 2. 해당 기능 클릭 3. 오류 발생",
        "동일 환경에서 다른 사용자는 정상 동작합니다. 해당 계정에서만 발생합니다.",
        "로그 확인 결과 timeout 오류가 반복 발생합니다.",
        "캐시 삭제 및 재시작 후에도 동일 현상이 지속됩니다.",
        "특정 브라우저에서만 발생하고 다른 브라우저는 정상입니다.",
        "최신 업데이트 이후부터 발생한 것으로 추정됩니다.",
    ]

    priorities = ['normal', 'normal', 'normal', 'high', 'low', 'urgent', 'normal', 'high']
    base_date = datetime.now()

    with get_conn() as conn:
        created = 0
        for i in range(50):
            cat        = random.choice(category_choices)
            pt         = random.choice(pt_choices)
            status     = random.choice(status_choices)
            aid        = random.choice(assignee_ids)
            title      = titles[i % len(titles)]
            content    = random.choice(contents)
            priority   = random.choice(priorities)
            days_ago   = random.randint(0, 120)
            created_at = (base_date - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
            voc_num    = f'TEST{1000 + i}'

            try:
                conn.execute(
                    '''INSERT INTO vocs
                       (title, content, category, priority, status, assignee_id,
                        voc_number, process_type, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?)''',
                    (title, content, cat, priority, status, aid,
                     voc_num, pt, created_at, created_at)
                )
                created += 1
            except Exception as e:
                print(f"  [오류] {e}")

    print(f"\n[완료] {created}개 테스트 VOC 생성됨")


if __name__ == '__main__':
    main()
