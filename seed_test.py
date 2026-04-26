"""
테스트용 VOC 20건 생성 (배정 테스트용)
기존 VOC 데이터 초기화 후 미배정 상태로 생성
실행: python seed_test.py
"""
from backend.db import init_db, get_conn

init_db()

VOCS = [
    ('배송',       'VOC-T001', '배송 지연 문의',         '주문 후 7일이 지났으나 아직 배송이 되지 않았습니다.'),
    ('배송',       'VOC-T002', '배송지 변경 요청',       '배송 출발 전에 주소를 변경하고 싶습니다.'),
    ('결제',       'VOC-T003', '카드 결제 오류',         '결제 시도 시 승인 오류 메시지가 반복됩니다.'),
    ('결제',       'VOC-T004', '이중 결제 환불 요청',    '동일 주문이 두 번 결제되었습니다. 한 건 환불 부탁드립니다.'),
    ('반품/교환',  'VOC-T005', '제품 불량 교환 요청',    '수령 제품에 외관 불량이 있어 교환을 요청합니다.'),
    ('반품/교환',  'VOC-T006', '단순 변심 반품',         '색상이 마음에 들지 않아 반품을 원합니다.'),
    ('반품/교환',  'VOC-T007', '사이즈 교환 문의',       '주문 사이즈가 맞지 않아 다른 사이즈로 교환 요청합니다.'),
    ('품질',       'VOC-T008', '제품 오작동 신고',       '구매 후 1주일 만에 전원이 켜지지 않습니다.'),
    ('품질',       'VOC-T009', '설명서와 다른 스펙',     '광고 스펙과 실제 성능이 다르게 느껴집니다.'),
    ('앱/서비스',  'VOC-T010', '앱 로그인 불가',         '정상 비밀번호 입력 시에도 로그인이 되지 않습니다.'),
    ('앱/서비스',  'VOC-T011', '포인트 적립 누락',       '지난주 구매분 포인트가 적립되지 않았습니다.'),
    ('앱/서비스',  'VOC-T012', '쿠폰 적용 오류',         '유효기간 내 쿠폰인데 적용 시 오류가 납니다.'),
    ('배송',       'VOC-T013', '배송 중 파손',           '제품 수령 시 박스 및 내부 파손 상태였습니다.'),
    ('결제',       'VOC-T014', '영수증 재발행 요청',     '사업자 경비 처리용 영수증 재발행을 요청합니다.'),
    ('품질',       'VOC-T015', '이상한 냄새 민원',       '개봉 시 화학적 냄새가 납니다. 안전 확인 요청합니다.'),
    ('앱/서비스',  'VOC-T016', '회원 탈퇴 처리 요청',   '개인정보 삭제 포함 회원 탈퇴를 요청합니다.'),
    ('기타',       'VOC-T017', '매장 운영 시간 문의',    '주말 매장 운영 시간을 알고 싶습니다.'),
    ('기타',       'VOC-T018', '기업 구매 담당자 연결',  '대량 구매 관련 기업 영업 담당자 연결을 원합니다.'),
    ('배송',       'VOC-T019', '해외 배송 가능 여부',    '해외 주소로 배송이 가능한지 문의드립니다.'),
    ('결제',       'VOC-T020', '할부 변경 요청',         '일시불 결제 건을 할부로 변경할 수 있는지 문의합니다.'),
]

with get_conn() as conn:
    # VOC 관련 데이터만 초기화 (담당자는 유지)
    conn.execute('DELETE FROM voc_notes')
    conn.execute('DELETE FROM assignment_history')
    conn.execute('DELETE FROM voc_images')
    conn.execute('DELETE FROM vocs')
    conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('vocs','assignment_history','voc_notes','voc_images')")

    # 배정 상태 초기화 + 순번 재정렬
    conn.execute('UPDATE assignees SET hold_turns = 0')
    conn.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('last_auto_assigned_id', '0')")
    for i, (aid,) in enumerate(conn.execute('SELECT id FROM assignees ORDER BY id').fetchall()):
        conn.execute('UPDATE assignees SET turn_order = ? WHERE id = ?', (i, aid))

    for category, voc_number, title, content in VOCS:
        conn.execute('''
            INSERT INTO vocs (title, content, category, priority, status, voc_number, requester)
            VALUES (?, ?, ?, 'normal', 'open', ?, '테스트')
        ''', (title, content, category, voc_number))

with get_conn() as conn:
    total   = conn.execute('SELECT COUNT(*) FROM vocs').fetchone()[0]
    members = conn.execute('SELECT name, turn_order FROM assignees ORDER BY turn_order, id').fetchall()

print(f'VOC {total}건 생성 완료 (전원 미배정 open)')
print()
print('현재 담당자 순번:')
for name, order in members:
    print(f'  {order+1}. {name}')
print()
print('배정 포인터 초기화 완료. 다음 자동 배정은 순번 1번부터 시작합니다.')
