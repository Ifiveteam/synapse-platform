# 관리자 페이지 — Phase 1 (관리자 인증 + 대시보드 셸 + 유저 관리 + 구독·결제 현황)

날짜: 2026-07-06

## 배경

Synapse에는 지금까지 관리자 전용 기능이 전혀 없다. CS 대응(가입자 조회, 플랜 변경, 탈퇴 처리)
\
을 하려면 DB에 직접 SQL을 날려야 하는 상태다. 관리자 페이지를 단계적으로 구축하기로 하고, 전체 로드맵을 다음과 같이 잡았다.

- **Phase 1 (이번 스펙)**: 관리자 인증 + 대시보드 셸 + 유저 관리(조회/플랜변경/강제탈퇴) + 구독·결제 현황(결제 이력 테이블 포함) + 강제탈퇴 시 구글 OAuth 동의 철회
- **Phase 2**: 관리자 액션 감사 로그(audit log), 역할별 권한 차등(super-admin vs viewer), 사용 현황 통계, 큐레이터 대화 로그 열람 — 관리자가 늘어나거나 거버넌스가 필요해지는 시점에 진행
- **Phase 3**: 운영 모니터링 — 에이전트/스케줄러 에러를 DB에 남기는 로깅 인프라부터 새로 깔아야 해서 가장 나중

이 문서는 Phase 1만 다룬다.

## 목표

- 관리자가 로그인해서 가입자 목록을 검색·조회할 수 있다.
- 특정 유저의 플랜(free/pro)을 관리자가 직접 변경할 수 있다.
- 특정 유저를 관리자가 강제 탈퇴(계정 삭제)시킬 수 있다. 이때 Synapse DB 데이터 삭제와 함께, 구글에 부여했던 OAuth 접근 권한(Drive 등)도 revoke되어 실질적으로 연동이 끊긴다.
- 관리자가 현재 Free/Pro 가입자 수와 결제 내역(언제·얼마·누가)을 조회할 수 있다.

## 비목표 (이번 스펙에서 안 하는 것 — Phase 2로 이연)

- 관리자 액션 감사 로그(audit log) — 관리자가 1~2명뿐인 현재 단계에서는 과함. 나중에 관리자가 늘어나면 "누가 언제 뭘 바꿨는지" 추적용으로 추가.
- 역할별 권한 차등(super-admin vs viewer 등) — 지금은 `ADMIN_EMAILS`에 있으면 전원 동일 권한(조회+수정+삭제). CS 담당자와 개발 담당자를 분리해야 할 필요가 생기면 추가.
- 사용 현황 통계, 큐레이터 대화 로그 열람 — 기존 데이터 조회 위주라 가볍게 추가 가능하지만 이번 스펙 범위 밖.
- 구독 취소 이력 — 결제(적립) 이벤트만 기록하고, 취소 시점 기록은 안 함 (`user.plan`을 free로 되돌리기만).

## 관리자 인증

- `backend/.env`에 `ADMIN_EMAILS=a@example.com,b@example.com` (콤마 구분) 추가.
- 기존 `get_current_user_dep`(구글 로그인 세션 검증)을 통과한 뒤, 유저 이메일이 `ADMIN_EMAILS`에 포함되는지 확인하는 `get_admin_user_dep` FastAPI dependency를 신설한다.
- `/api/v1/admin/*` 라우터 전체에 `get_admin_user_dep`를 적용해 관리자가 아니면 403을 반환한다.
- 기존 `GET /api/v1/auth/me` 응답(`UserResponse`)에 `is_admin: bool` 필드를 추가한다. 서버가 `ADMIN_EMAILS`와 대조해 계산한 결과만 내려주고, 이메일 목록 자체는 클라이언트에 노출하지 않는다.

## 데이터 모델 변경

### 신규: `PaymentTransaction`

결제 승인 성공 시점의 기록. `backend/app/models/payment_transaction.py`

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, cascade delete |
| amount | Integer | 결제 금액 (원) |
| toss_payment_key | String | 토스페이먼츠 paymentKey |
| toss_order_id | String | 토스페이먼츠 orderId |
| paid_at | DateTime(timezone) | 결제 승인 시각 (server_default now) |

Alembic 마이그레이션 1개 추가 (현재 head: `010_batch_source_catalog` 다음 리비전).

### 변경: `backend/app/api/v1/payment.py`

`confirm_payment`가 토스 승인 성공 후 `user.plan = "pro"` 처리와 같은 트랜잭션 안에서 `PaymentTransaction` row를 INSERT한다. `cancel_subscription`은 이번 스펙에서 변경 없음(플랜만 free로).

## 백엔드

### 신규 파일
- `backend/app/api/v1/admin.py` — 관리자 라우터 (`prefix="/admin"`)
- `backend/app/services/admin/user_service.py` — 유저 관리 비즈니스 로직 (조회/플랜변경/탈퇴)
- `backend/app/services/admin/billing_service.py` — 구독·결제 현황 집계
- `backend/app/models/payment_transaction.py` — 위 모델

### API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/v1/admin/users` | 유저 목록. 쿼리파라미터 `query`(이메일 부분검색), `plan`(free/pro 필터), `page`, `page_size` |
| GET | `/api/v1/admin/users/{user_id}` | 유저 상세 — 기본정보 + 시청기록/스크랩/이상향 개수(COUNT 쿼리) |
| PATCH | `/api/v1/admin/users/{user_id}/plan` | body `{ "plan": "free" \| "pro" }` — `User.plan` 직접 변경 |
| DELETE | `/api/v1/admin/users/{user_id}` | 강제 탈퇴 (아래 "강제 탈퇴 흐름" 참고) |
| GET | `/api/v1/admin/billing/summary` | `{ free_count, pro_count, this_month_payment_count, this_month_revenue }` |
| GET | `/api/v1/admin/billing/payments` | 결제 내역 목록 (페이지네이션). 각 항목: 유저 이메일, 금액, 결제일시 |

### 강제 탈퇴 흐름 (`DELETE /api/v1/admin/users/{user_id}`)

1. 대상 유저 조회, 없으면 404.
2. `UserToken.google_refresh_token`이 있으면 `https://oauth2.googleapis.com/revoke?token=...` 호출해 구글 OAuth 동의를 철회한다.
   - revoke 요청이 실패해도(이미 만료된 토큰 등) 삭제 자체는 계속 진행한다 — 목적은 "가능하면 정리"이지, 실패가 탈퇴를 막으면 안 됨. 실패는 `logger.warning`으로만 남긴다.
3. `session.delete(user)` — 기존 `delete_me`(`app/api/v1/auth.py:186`)와 동일한 삭제 로직 재사용. FK cascade로 연관 데이터 전부 삭제.

이 revoke 로직은 `app/api/v1/auth.py`의 `delete_me`(유저 본인 탈퇴)에도 동일하게 적용해 공통 함수로 뺀다 (`app/services/user_deletion.py` 같은 공용 모듈에 `revoke_and_delete_user(session, user)` 형태로 구현 — 관리자 강제탈퇴와 본인탈퇴 양쪽에서 재사용).

## 프론트엔드

### 신규 파일
- `frontend/src/pages/admin/AdminUsersPage.tsx`
- `frontend/src/pages/admin/AdminBillingPage.tsx`
- `frontend/src/components/admin/AdminLayout.tsx` — 상단 네비게이션형 레이아웃 (기존 메인 앱 Sidebar와 별도)
- `frontend/src/api/admin.ts` — 관리자 API 클라이언트

### 라우팅
- `frontend/src/routes/paths.ts`에 `admin: "/admin"`, `adminUsers: "/admin/users"`, `adminBilling: "/admin/billing"` 추가
- `frontend/src/routes/router.tsx`에 `/admin` 하위 라우트 등록, `AdminLayout`으로 감쌈
- 라우트 가드: `useAuthStore`의 `user.is_admin`이 false면 `/`로 리다이렉트. 이건 UX용이고, 실제 방어선은 백엔드 403.
- **진입점**: 이번 스펙에서는 `/admin/users`, `/admin/billing` URL 직접 접근만 지원한다(주소창에 직접 입력). Sidebar에 관리자 전용 아이콘을 넣는 건 UI를 전체적으로 다듬는 다음 작업에서 처리하고, 지금은 기능 동작(들어가지는지)만 확보한다.

### 화면 구성
- **유저 목록** (`/admin/users`): 이메일 검색 입력, 플랜 필터(전체/Free/Pro), 테이블(이메일/이름/플랜/가입일/다음 분석 예정일), 행마다 "상세" 버튼, 페이지네이션.
- **유저 상세** (모달 또는 하위 라우트): 기본정보 + 활동 요약(시청기록/스크랩/이상향 개수) + "플랜을 X로 변경" 버튼 + "계정 강제 탈퇴" 버튼(위험 액션이라 별도 색상).
- **탈퇴 확인 모달**: "복구할 수 없습니다. 구글 연동도 함께 해제되며, 같은 구글 계정으로 재로그인해도 이전 데이터는 복구되지 않습니다." 문구를 명시하고, 한 번 더 확인받는다.
- **구독·결제 현황** (`/admin/billing`): 상단 KPI 카드(Free 인원수, Pro 인원수, 이번달 결제건수, 이번달 매출) + 결제 내역 테이블(이메일/금액/결제일시), 페이지네이션.

## 에러 처리

- 관리자가 아닌 로그인 유저가 `/api/v1/admin/*` 접근 → 403
- 로그인하지 않은 채 접근 → 401 (기존 `get_current_user_dep` 동작)
- 존재하지 않는 `user_id` 조회/변경/삭제 → 404
- 이미 삭제된 유저를 다시 삭제 시도(동시 처리 등 동시성 엣지케이스) → 404로 통일 처리
- 강제 탈퇴 시 구글 revoke 호출 실패 → 삭제는 계속 진행, 경고 로그만 남김 (탈퇴 자체를 막지 않음)

## 테스트 계획

- 백엔드: `get_admin_user_dep`가 화이트리스트 밖 이메일을 403으로 막는지, 화이트리스트 안 이메일은 통과하는지 단위 테스트.
- 백엔드: 유저 목록 검색/필터/페이지네이션, 상세 조회 COUNT 값 정확성, 플랜 변경, 강제 탈퇴(연관 데이터까지 삭제되는지, revoke 실패해도 삭제는 되는지) 검증.
- 백엔드: `confirm_payment` 성공 시 `PaymentTransaction` row가 정확히 남는지, billing summary/목록 API 집계값 검증.
- 프론트: `is_admin=false`일 때 `/admin` 접근 시 리다이렉트되는지 수동 확인.
- 수동 시나리오: 실제 관리자 이메일로 로그인 → 유저 검색 → 상세 조회 → 플랜 변경 → 강제 탈퇴까지, 그리고 결제 현황 페이지 조회까지 엔드투엔드로 브라우저에서 직접 실행.
