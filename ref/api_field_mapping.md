# API JSON 필드 → DB 컬럼 매핑 참조

## voc_info 테이블 (기본정보 + 상세정보)

| API JSON 키 | DB 컬럼명 | 화면 표시명 | 비고 |
|---|---|---|---|
| `registerorgname` | `registerorgname` | 신청자종류 | 기본정보 |
| `registergbmname` | `registergbmname` | 신청자GBM | 기본정보 |
| `vocno` | `vocno` | VOC번호 | 기본정보 |
| `registername` | `registername` | 신청자 | 기본정보 |
| `register_SINGLEID` | `register_singleid` | 신청자ID | 기본정보 (선택) |
| `registerdeptname` | `registerdeptname` | 신청자부서 | 기본정보 |
| `regdate` | `regdate` | 신청일 | YYYYMMDD 형식 |
| `regtime` | `regtime` | 신청시각 | HHmmss 형식 |
| `voctitle` | `voctitle` | 제목 | 상세정보 |
| `wirtercomptelno` | `wirtercomptelno` | 전화번호 | 상세정보 (오타 그대로 유지) |
| `writermobiletelno` | `writermobiletelno` | 휴대폰번호 | 상세정보 |
| `writeremail` | `writeremail` | 이메일 | 상세정보 |
| `writername` | `writername` | 등록자 | 상세정보 |
| `writer_SINGLEID` | `writer_singleid` | 등록자ID | 상세정보 (선택) |
| `writerdeptname` | `writerdeptname` | 등록자부서 | 상세정보 |
| `acceptdate` | `acceptdate` | 접수일 | YYYYMMDD 형식 |
| `accepttime` | `accepttime` | 접수시각 | HHmmss 형식 |
| `systemname` | `systemname` | 시스템 | 상세정보 |
| `endreqdate` | `endreqdate` | 완료요청일 | YYYYMMDD 형식 |
| `endreqtime` | `endreqtime` | 완료요청시각 | HHmmss 형식 |
| `endplandate` | `endplandate` | 완료예정일 | YYYYMMDD 형식 |
| `endplantime` | `endplantime` | 완료예정시각 | HHmmss 형식 |
| `gbmname` | `gbmname` | VOC담당GBM | 상세정보 |
| `sysbizcode` | `sysbizcode` | 업무유형(상위) | 상세정보 — 업무유형 부모 코드/명 |
| `sysbizcode1` | `sysbizcode1` | 업무유형(하위) | 상세정보 — 업무유형 자식 코드/명 |
| `bizNmDept` | `bizNmDept` | 업무유형(전체) | 상세정보 — 하위호환용 (대소문자 주의) |
| `vocstatusname` | `vocstatusname` | 세부진행상태명 | 상세정보 |
| `vocstatuscode` | `vocstatuscode` | 세부진행상태코드 | voc_status 자동 매핑에 사용 |
| `voctypename` | `voctypename` | VOC유형명 | 상세정보 |
| `voctypecode` | `voctypecode` | VOC유형코드 | 상세정보 |

> **업무유형 필드 구조**:
> - `sysbizcode` = 상위 업무유형 (부모) — e.g., "MRO2.0(KOREA, 국내사업자)"
> - `sysbizcode1` = 하위 업무유형 (자식) — e.g., "기타 문의"
> - 화면 표시: `sysbizcode › sysbizcode1` (둘 다 있을 때), 하나만 있으면 그것만, 없으면 `bizNmDept` 폴백

---

## voc_stage_info 테이블 (처리정보 — vocInfoList 반복)

각 `vocInfoList` 항목이 하나의 행으로 저장됨.

| API JSON 키 | DB 컬럼명 | 화면 표시명 | 비고 |
|---|---|---|---|
| `vocno` | `vocno` | VOC번호 | stage_data 내 필드 |
| `registername` | `registername` | 등록자 | stage_data 내 필드 |
| `deptname` | `deptname` | 등록자부서 | stage_data 내 필드 |
| `regdate` | `regdate` | 등록일 | YYYYMMDD 형식 |
| `regtime` | `regtime` | 등록시각 | HHmmss 형식 |
| `voctitle` | `voctitle` | 제목 | stage_data 내 필드 |
| `voctext` | `voctext` | 내용 | HTML 포함 가능 — 표시 시 HTML 파싱 필요 |
| `uppervocno` | `uppervocno` | 상위VOC번호 | 메타 컬럼 |
| `vocstatuscode` | `vocstatuscode` | 단계상태코드 | scraper에서 직접 추출. type_items voc_status 자동 매핑 |
| `vocstatusname` | `vocstatusname` | 단계상태명 | scraper에서 직접 추출 |
| `voctypename` | `voctypename` | VOC유형명 | scraper에서 직접 추출 |
| `voctypecode` | `voctypecode` | VOC유형코드 | scraper에서 직접 추출 |
| `stage_index` | `stage_index` | 단계순서 | 0-based index (앱 내부 관리) |

> **직접 추출 필드**: `vocstatuscode`, `vocstatusname`, `voctypename`, `voctypecode`는  
> child_field_map 설정과 무관하게 scraper.py에서 `stage_item.get(키)`로 직접 추출됨.

---

## vocs 테이블 (앱 내부 VOC 관리)

| DB 컬럼명 | 의미 | API 연관 필드 |
|---|---|---|
| `voc_number` | VOC 식별번호 | `vocno` (기본정보) |
| `title` | VOC 제목 | `voctitle` |
| `content` | VOC 내용 | `voctext` (vocInfoList[0]) |
| `category` | 업무유형 (하위코드) | `bizNmDept` 또는 `sysbizcode1` |
| `sysbizcode` | 업무유형 상위 | `sysbizcode` |
| `sysbizcode1` | 업무유형 하위 | `sysbizcode1` |
| `process_type` | VOC유형 | `voctypename` |
| `status` | 현재 상태 | `vocstatuscode` → type_items 자동 매핑 |
| `due_date` | 완료요청일 | `endreqdate` |
| `requester` | 신청자 | `registername` |
| `assignee_id` | 담당자 (내부 배정) | — |
| `priority` | 우선순위 | — (앱 내부) |

---

## scraper.py 저장 흐름

```
fetch_voc(voc_number)
  └─ API 응답 파싱
       ├─ 기본 데이터 → vocs 테이블 (title, content, voc_number, due_date, requester,
       │                               category, process_type, sysbizcode, sysbizcode1)
       ├─ 전체 필드   → voc_info 테이블 (save_voc_info: api_field_map 기반 동적 저장)
       └─ vocInfoList → voc_stage_info 테이블
                         (save_voc_stages: stage_index, uppervocno,
                          vocstatuscode, vocstatusname, voctypename, voctypecode + stage_data)
```

### vocstatuscode 표시
- `voc_stage_info.vocstatuscode` 컬럼에 API 원본 코드 그대로 저장 (예: `"50"`)
- 화면 표시 시 프론트엔드 `typeItems['voc_status']`에서 코드 → 이름 매핑  
  (예: `"50"` → `"처리완료"`)
- vocs.status 업데이트 시 `_update_status_from_last_stage()`가 type_items의 `value=?`로 직접 조회

---

## 날짜 표시 형식

| API 원본 | 화면 표시 | 변환 함수 |
|---|---|---|
| `regdate="20261030"` + `regtime="121030"` | `2026-10-30 12:10:30` | `formatVocDate(dateStr, timeStr)` in common.js |
| YYYYMMDD 단독 | `YYYY-MM-DD` | 동일 함수 |

---

## 자주 헷갈리는 API 키 이름

| 주의 사항 | 정확한 키 |
|---|---|
| 전화번호 오타 (API 원본 오타) | `wirtercomptelno` (writer 아님, wirter) |
| 업무유형 상위코드 | `sysbizcode` |
| 업무유형 하위코드 | `sysbizcode1` |
| 업무유형 전체명(구방식) | `bizNmDept` (대소문자 혼합) |
| 신청자 ID | `register_SINGLEID` (대문자 포함) |
| 등록자 ID | `writer_SINGLEID` (대문자 포함) |
