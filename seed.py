"""
더미 데이터 생성 스크립트
실행: python seed.py
"""
import random
from datetime import datetime, timedelta
from backend.db import init_db, get_conn

init_db()

# ── 담당자 ───────────────────────────────────────────────
ASSIGNEES = ['김민수', '이지연', '박철호', '정소희', '최준혁']

# ── 카테고리별 VOC 샘플 ──────────────────────────────────
VOC_SAMPLES = [
    # (category, title, content)
    ('배송', '배송 지연 문의', '주문한 지 5일이 지났는데 아직 배송이 안 왔습니다. 빠른 확인 부탁드립니다.'),
    ('배송', '배송지 변경 요청', '주문 후 이사를 가게 되어 배송지를 변경하고 싶습니다. 가능한지 확인 부탁드립니다.'),
    ('배송', '배송 중 파손 신고', '제품이 도착했는데 박스가 찌그러지고 내부 제품이 파손되어 있습니다. 교환 요청합니다.'),
    ('배송', '해외 배송 가능 여부', '해외로 제품을 배송받을 수 있는지 문의드립니다. 가능하다면 배송 기간도 알고 싶습니다.'),
    ('결제', '카드 결제 오류', '결제 시도 중 오류 메시지가 발생하고 결제가 되지 않습니다. 확인 부탁드립니다.'),
    ('결제', '이중 결제 환불 요청', '동일한 건이 두 번 결제되었습니다. 한 건 환불 요청드립니다.'),
    ('결제', '결제 영수증 재발행', '세금계산서용 영수증을 재발행해주실 수 있나요? 기존 것을 분실했습니다.'),
    ('결제', '할부 변경 요청', '일시불로 결제했는데 할부로 변경이 가능한지 문의드립니다.'),
    ('반품/교환', '제품 불량 교환 요청', '수령한 제품에 스크래치가 있습니다. 새 제품으로 교환해 주세요.'),
    ('반품/교환', '단순 변심 반품', '색상이 마음에 들지 않아 반품하고 싶습니다. 반품 절차 안내 부탁드립니다.'),
    ('반품/교환', '사이즈 교환 문의', '주문한 사이즈가 맞지 않아 교환하고 싶습니다. 재고가 있는지 확인해주세요.'),
    ('품질', '제품 오작동 신고', '구매 일주일 만에 제품이 작동하지 않습니다. AS 접수 방법을 알고 싶습니다.'),
    ('품질', '제품 이상한 냄새', '제품에서 이상한 냄새가 납니다. 안전 문제가 있는지 확인이 필요합니다.'),
    ('품질', '설명서와 다른 스펙', '제품 설명서에 표기된 스펙과 실제 제품 성능이 다릅니다. 설명 부탁드립니다.'),
    ('앱/서비스', '앱 로그인 불가', '앱에서 로그인이 계속 실패합니다. 비밀번호도 맞는데 접속이 안 됩니다.'),
    ('앱/서비스', '포인트 적립 누락', '구매 후 포인트가 적립되지 않았습니다. 확인 및 수동 적립 요청드립니다.'),
    ('앱/서비스', '회원 탈퇴 처리 요청', '회원 탈퇴를 원합니다. 개인정보 삭제도 함께 요청드립니다.'),
    ('앱/서비스', '쿠폰 사용 오류', '쿠폰 코드를 입력했는데 적용이 안 됩니다. 유효기간은 남아있는 상태입니다.'),
    ('기타', '매장 운영 시간 문의', '가장 가까운 매장의 주말 운영 시간을 알고 싶습니다.'),
    ('기타', '기업 구매 담당자 연결 요청', '대량 구매를 위해 기업 영업 담당자와 연결하고 싶습니다.'),
]

REQUESTERS = ['홍길동', '김영희', '이철수', '박지민', '최수연', '정민준', '강하늘', '윤서연', '임도현', '조예진']
STATUSES = ['open', 'open', 'open', 'in_progress', 'in_progress', 'resolved', 'closed']
PRIORITIES = ['low', 'normal', 'normal', 'normal', 'high', 'urgent']

def random_date(days_back_max=60, days_forward_max=14):
    past = datetime.now() - timedelta(days=random.randint(0, days_back_max))
    return past.strftime('%Y-%m-%d')

def random_due_date():
    future = datetime.now() + timedelta(days=random.randint(1, 14))
    return future.strftime('%Y-%m-%d')

with get_conn() as conn:
    # 기존 데이터 초기화
    conn.execute('DELETE FROM voc_notes')
    conn.execute('DELETE FROM assignment_history')
    conn.execute('DELETE FROM vocs')
    conn.execute('DELETE FROM assignees')
    conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('vocs','assignees','assignment_history','voc_notes')")

    # 담당자 추가
    for name in ASSIGNEES:
        conn.execute('INSERT INTO assignees (name) VALUES (?)', (name,))

    assignee_ids = [row[0] for row in conn.execute('SELECT id FROM assignees').fetchall()]

    # VOC 생성 (30건)
    voc_count = 30
    samples = random.choices(VOC_SAMPLES, k=voc_count)

    for i, (category, title, content) in enumerate(samples):
        voc_num = f'VOC-{2025100 + i}'
        requester = random.choice(REQUESTERS)
        status = random.choice(STATUSES)
        priority = random.choice(PRIORITIES)
        due_date = random_due_date() if random.random() > 0.2 else ''
        created_at = (datetime.now() - timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d %H:%M:%S')

        # 담당자: open은 30% 확률로 미배정
        if status == 'open' and random.random() < 0.3:
            assignee_id = None
        else:
            assignee_id = random.choice(assignee_ids)

        conn.execute('''
            INSERT INTO vocs
            (title, content, category, priority, status, assignee_id,
             voc_number, requester, due_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, content, category, priority, status, assignee_id,
              voc_num, requester, due_date, created_at, created_at))

        voc_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

        # 배정 이력
        if assignee_id:
            conn.execute('''
                INSERT INTO assignment_history (voc_id, assignee_id, note, assigned_at)
                VALUES (?, ?, ?, ?)
            ''', (voc_id, assignee_id, '자동 배정', created_at))

            # 일부는 재배정 이력 추가
            if random.random() < 0.25:
                other = random.choice([a for a in assignee_ids if a != assignee_id])
                reassign_at = (datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S') + timedelta(hours=random.randint(1, 24))).strftime('%Y-%m-%d %H:%M:%S')
                conn.execute('''
                    INSERT INTO assignment_history (voc_id, assignee_id, note, assigned_at)
                    VALUES (?, ?, ?, ?)
                ''', (voc_id, other, '재배정', reassign_at))

        # 일부 VOC에 메모 추가
        if random.random() < 0.4:
            notes = [
                '고객에게 현황 안내 완료',
                '내부 담당 부서 확인 요청',
                '환불 처리 진행 중',
                '택배사 조회 결과 통보',
                '3영업일 내 처리 예정으로 안내',
            ]
            note_at = (datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S') + timedelta(hours=random.randint(1, 12))).strftime('%Y-%m-%d %H:%M:%S')
            conn.execute('''
                INSERT INTO voc_notes (voc_id, content, created_at) VALUES (?, ?, ?)
            ''', (voc_id, random.choice(notes), note_at))

print(f'담당자 {len(ASSIGNEES)}명 생성 완료')
print(f'VOC {voc_count}건 생성 완료')
print()

# 현황 출력
with get_conn() as conn:
    for name, cnt in conn.execute('''
        SELECT a.name, COUNT(v.id)
        FROM assignees a LEFT JOIN vocs v ON v.assignee_id = a.id
        GROUP BY a.id
    ''').fetchall():
        print(f'  {name}: {cnt}건')

    total = conn.execute('SELECT COUNT(*) FROM vocs').fetchone()[0]
    by_status = conn.execute("SELECT status, COUNT(*) FROM vocs GROUP BY status").fetchall()
    print(f'\n  전체 {total}건')
    for s, c in by_status:
        print(f'  {s}: {c}건')
