# Auth — Google 토큰 구조 개선 계획

> 상태: **계획(미구현)**. 로그인 토큰과 Drive 토큰이 한 컬럼을 공유해 서로 덮어쓰는 문제를 분리하고,
> "폴더 변경" 시 매번 뜨는 Google 동의 팝업을 제거한다.
> 관련 코드: `services/google_oauth.py`, `api/v1/auth.py`, `api/v1/takeout.py`, `lib/google-picker.ts`

---

## 1. 문제 (현재 구조)

로그인과 Drive 연동이 **같은 컬럼** `user_token.google_refresh_token`에 refresh token을 저장하고 **서로 덮어쓴다.**

| 흐름 | 함수 | scope | 저장 위치 |
|---|---|---|---|
| 로그인 | `upsert_user_and_token` | `openid/email/profile` (`access_type=offline`, `prompt=consent`) | `google_refresh_token` (덮어씀) |
| Drive 연동 | `store_google_tokens` (`drive_connect` 경유) | `drive.file` | `google_refresh_token` (덮어씀) |

- 로그인 토큰엔 `drive.file`이 없다.
- 로그인은 `prompt=consent`+`offline`이라 **로그인할 때마다** 새 refresh token을 받아 컬럼을 덮어쓴다.
- 결과: **Drive 연동 후 재로그인하면** drive.file 토큰이 profile/email 토큰으로 덮여서 →
  `refresh_access_token`으로 만든 access token에 Drive 권한이 없음 → **Drive 다운로드/폴더 조회/Picker가 깨진다.**
- 지금은 "로그인 → Drive 연동" 순서라 당장은 동작하지만, **재로그인 한 번이면 Drive가 끊기는** 불안정한 구조.

추가로, **"폴더 변경"을 누를 때마다** 프론트가 GIS 코드 클라이언트로 새 인증 코드를 요청해서
매번 "계정을 선택하세요" 팝업이 뜬다 (`lib/google-picker.ts::connectDriveFolder`). 저장된 Drive refresh token을
재사용하지 않기 때문. → 위 토큰 분리가 선행돼야 이 팝업 제거도 안정적으로 가능.

---

## 2. 목표

1. **로그인 토큰과 Drive 토큰을 분리 저장** — 서로 안 건드리게.
2. Drive 작업(다운로드·폴더 조회·Picker 토큰 발급)은 **Drive 전용 토큰**만 사용.
3. **"폴더 변경" 팝업 제거** — 저장된 Drive 토큰으로 서버가 조용히 access token 발급, 최초/취소 시에만 동의 폴백.

---

## 3. 변경 계획

### 3.1 DB — `drive_refresh_token` 컬럼 신설
- `user_token`에 `drive_refresh_token VARCHAR(512) NULL` 추가.
- 마이그레이션 `009_drive_refresh_token` (`down_revision="008_drop_transcript"`).
- 모델 `models/user_token.py`에 필드 추가.

| 컬럼 | 용도 |
|---|---|
| `google_refresh_token` (기존) | 로그인(profile/email) refresh token — 로그인 흐름 전용 |
| `drive_refresh_token` (신규) | Drive(`drive.file`) refresh token — Drive 작업 전용 |

### 3.2 저장 경로 분리
- **로그인** (`upsert_user_and_token`): 계속 `google_refresh_token`만 저장. (변경 없음)
- **Drive 연동** (`store_google_tokens`): `google_refresh_token` 대신 **`drive_refresh_token`에 저장**하도록 변경.
  - `users.access_token`은 Drive access token으로 유지(즉시 Picker/다운로드용).

### 3.3 Drive access token 발급을 Drive 토큰 기준으로
- `refresh_access_token(user)`(현재 `google_refresh_token` 사용) 옆에 **Drive 전용** 발급 로직 추가
  또는 파라미터화: Drive 작업은 `drive_refresh_token`으로 refresh.
- Drive 사용처 점검: `download_drive_file`, `find_takeout_in_folder`, `refresh_user_token`(takeout_service) —
  전부 Drive 토큰 경로를 쓰도록 정리.

### 3.4 신규 엔드포인트 — 조용한 Picker 토큰 발급
- `POST /auth/drive/token` (인증 필요):
  - 저장된 `drive_refresh_token`으로 새 `drive.file` access token 발급 → `{access_token}` 반환.
  - 토큰 없음/만료/취소 시 → `401`/빈 응답으로 폴백 신호.

### 3.5 프론트 — "폴더 변경" 팝업 제거
- `lib/google-picker.ts`:
  - `changeFolder()`(또는 기존 `connectDriveFolder` 개선):
    1. 먼저 `POST /auth/drive/token`으로 토큰 시도(팝업 X) → 성공 시 바로 `openFolderPicker`.
    2. 실패(최초 연동/취소/만료) → 기존 GIS 동의 플로우(`getDriveAuthCode` → `connectDrive`) 폴백.
- 결과: **최초 1회만 동의**, 이후 폴더 변경은 팝업 없이 Picker만 뜸.
  연동 계정으로 토큰이 고정되므로 "계정 정렬" 문제도 오히려 안전해짐.

---

## 4. 엣지 케이스

- **최초 연동**: `drive_refresh_token` 없음 → 3.5의 폴백(동의)로 진행 후 저장.
- **Drive 권한 취소**(사용자가 구글 계정에서 앱 권한 삭제): refresh 실패 → 폴백으로 재동의 유도.
- **refresh token 미반환**: 구글은 재동의 없이는 refresh token을 안 줄 수 있음 → 기존 값 보존(현재 `store_google_tokens`의 `if refresh` 패턴 유지).
- **기존 유저 마이그레이션**: 009 적용 시 `drive_refresh_token`은 NULL로 시작 → 다음 "폴더 변경"/"연동" 때 채워짐.
  (기존 `google_refresh_token`에 Drive 토큰이 들어있을 수 있으나 신뢰하지 않고 새로 채우는 게 안전.)

---

## 5. 검증

1. 마이그레이션 왕복: `alembic upgrade head`(009) ↔ `downgrade -1`.
2. 로그인 → Drive 연동 → **재로그인** → Drive 폴더 조회/다운로드 정상(끊기지 않음) 확인. ← 핵심 회귀
3. "폴더 변경" 반복 시 팝업 안 뜨는지(2회차부터).
4. 권한 취소 후 "폴더 변경" → 동의 폴백 정상.
5. `ruff` + 백엔드 import + 프론트 `pnpm build`.

---

## 6. 관련/후속
- 이 문서는 **토큰 분리 + 팝업 제거**만 다룸.
- 별개 계획: 인덱싱 유저별 직렬화(큐 + `pending` 상태) — 동시 업로드 교착 방지. (추후 `docs/profile/` 또는 별도 문서)
