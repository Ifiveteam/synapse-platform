# Synapse DB 스키마

PostgreSQL 17 · `pgvector` · `pgcrypto`

마이그레이션 (실제 파일 · 분기/병합 있음):

```text
001_initial_schema → 002_create_scraps → 003_user_subscription
                                             ├─ 004_drive_folder → 005_analysis_stage ─┐
                                             └─ 004_scrap_embeddings ─────────────────┴─ 006_merge_heads → 007_user_behavior_logs → 008_drop_transcript → 009_interval_months → 010_batch_source_catalog
  → 011_profile_v2 → 012_rename_v2_portrait → 013_ideal_targets → 014_playlist_status → 015_playlist_save_status
  → 016_navigator_proposal_status → 017_ideal_taste_keywords → 018_playlist_refresh_period → 019_playlist_last_refreshed_at  (현재 head)
```

> 초기 스키마는 `001_initial_schema` **한 파일에 통합**돼 있다(과거 007~013 등 개별 마이그레이션은 통합됨, 실파일 없음). 이후 `scraps`(002) → `user_subscription`(003)까지 선형. 003에서 **두 갈래로 분기**(`004_drive_folder`+`005_analysis_stage` / `004_scrap_embeddings`)했다가 `006_merge_heads`로 병합, 이후 007~010까지 선형, 다시 011~019(대부분 프로파일러·네비게이터)가 선형으로 이어져 `019_playlist_last_refreshed_at`가 현재 head. 새 마이그레이션은 `down_revision`을 **`019_playlist_last_refreshed_at`**로 지정.

| 리비전 | 추가/변경 |
|--------|-----------|
| `004_drive_folder` | `user_token`에 `drive_folder_id`·`drive_folder_name` 추가 (Takeout 자동분석용 Picker 폴더) |
| `004_scrap_embeddings` | `scrap_embeddings` 테이블 신설 (scraps 1:1 pgvector) |
| `005_analysis_stage` | `user_analysis_source`에 `stage` 컬럼 추가 (indexing/profiling) |
| `006_merge_heads` | 위 두 갈래 병합 (no-op) |
| `007_user_behavior_logs` | `user_behavior_logs` 테이블 신설 (익스텐션 체류시간) |
| `008_drop_transcript` | `video_analysis.transcript` 컬럼 제거 (자막 IP 차단으로 미사용) |
| `009_interval_months` | `users.analysis_interval_months` 추가 (Drive 자동분석 주기) |
| `010_batch_source_catalog` | `analysis_batch`·`analysis_source_catalog` 신설 + `user_analysis_source`·`user_profile_history`에 `batch_id` (요청 단위 배치 스코프 분석) |
| `011_profile_v2` → `012_rename_v2_portrait` | `user_profile_history`에 초상 프로필 JSONB 추가(`v2`) 후 `portrait`로 개명 |
| `013_ideal_targets` | `user_ideal_persona`에 `target_disposition`·`target_interest` JSONB (목표 성향·관심 도메인) |
| `014_playlist_status` | `navigator_playlist.status` (pending/ready/failed, 기본 ready) |
| `015_playlist_save_status` | `navigator_playlist.save_status` (none/saving/saved/failed, 기본 none) |
| `016_navigator_proposal_status` | `navigator_proposal_cache.status`(기본 ready) + `proposals_json`·`generated_at` nullable화 |
| `017_ideal_taste_keywords` | `user_ideal_persona.taste_keywords` JSONB (대화 관심 키워드) |
| `018_playlist_refresh_period` | `navigator_playlist.refresh_period` (none/weekly/monthly, 기본 none) |
| `019_playlist_last_refreshed_at` | `navigator_playlist.last_refreshed_at` timestamptz (자동 갱신 주기 판정) |

---

## 테이블 관계 (요약)

| 테이블 | 설명 | 관계 |
|--------|------|------|
| `users` | 사용자 | `user_token` 1:1 |
| `user_token` | 로그인·Google·익스텐션 토큰 + Drive 폴더(004) | → `users` |
| `extension_auth_code` | 웹→익스텐션 1회용 연동 코드 | → `users` |
| `user_watch_catalog` | 시청 기록 정본 (인덱서) | → `users`, ← `video_analysis` 0~1, ← `analysis_source_catalog` N |
| `user_subscription` | 구독 채널 스냅샷 (인덱서, 003) | → `users` |
| `analysis_batch` | 분석 요청(클릭) 단위 묶음. seal되면 그 배치로 프로파일 1회 (010) | → `users` |
| `user_analysis_source` | 업로드 소스별 분석 이력 (중복 방지). `batch_id`로 배치 소속 | → `users`, → `analysis_batch` 0~1, → `user_profile_history` 0~1 |
| `analysis_source_catalog` | 소스(파일)↔시청영상 다대다 소속. 배치 스코프 분석용 (010) | → `user_analysis_source`, → `user_watch_catalog` |
| `video_analysis` | 영상 LLM 분석 (프로파일러) | → `users`, → `user_watch_catalog` 1:1 |
| `user_profile_history` | 성향 점수 + LLM 해석 스냅샷. `batch_id`로 유발 배치 박제 | → `users`, → `analysis_batch` 0~1 |
| `user_ideal_persona` | 이상 자아 (네비게이터) | → `users`, → `user_profile_history` 0~1 |
| `navigator_proposal_cache` | 이상향 제안 3안 캐시 (네비게이터) | → `users`, → `user_profile_history` |
| `navigator_playlist` | 이상향 기반 YouTube 재생목록 (네비게이터) | → `users`, → `user_ideal_persona` |
| `scraps` | 웹·채팅 스크랩 요약 (아카이버·큐레이터, 002) | → `users` |
| `scrap_embeddings` | 스크랩 본문 임베딩 (아카이버, 004) | → `scraps` 1:1 |
| `ai_chat_logs` | 통합 AI 채팅 로그 (Archiver·Curator) | → `users` |
| `user_behavior_logs` | 익스텐션 체류시간·URL 로그 (Tracking, 007) | → `users` |

---

## users

사용자 계정 및 Google OAuth 프로필.

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK. `gen_random_uuid()` |
| `email` | VARCHAR(255) | N | 로그인 이메일. UK |
| `google_sub_id` | VARCHAR(255) | N | Google 계정 고유 ID. UK |
| `name` | VARCHAR(256) | N | 표시 이름 |
| `picture` | TEXT | Y | 프로필 이미지 URL |
| `access_token` | TEXT | Y | Google access token (Drive 등) |
| `plan` | VARCHAR(20) | N | 요금제. 기본 `free` (013) |
| `analysis_interval` | VARCHAR(50) | N | 프로파일러 분석 주기. 기본 `WEEKLY` |
| `next_analysis_at` | TIMESTAMPTZ | N | 다음 프로파일 분석 예정 시각 |
| `created_at` | TIMESTAMPTZ | N | 가입 시각 |

**인덱스:** `ix_users_next_analysis (next_analysis_at)`

---

## user_token

서비스 세션 토큰과 Google·익스텐션 refresh token. `users`와 1:1.

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE. UK |
| `refresh_token` | VARCHAR(512) | N | 서비스 자체 refresh token |
| `google_refresh_token` | VARCHAR(512) | Y | Google OAuth refresh token |
| `expires_at` | TIMESTAMPTZ | N | 서비스 refresh token 만료 시각 |
| `extension_refresh_token` | VARCHAR(512) | Y | 익스텐션 세션 refresh token |
| `extension_expires_at` | TIMESTAMPTZ | Y | 익스텐션 refresh token 만료 시각 |
| `drive_folder_id` | VARCHAR(255) | Y | Picker로 1회 선택한 Takeout Drive 폴더 ID. 스케줄러는 이 값 있는 유저만 처리 (004_drive_folder) |
| `drive_folder_name` | VARCHAR(512) | Y | 연동 폴더 표시명 (004_drive_folder) |
| `created_at` | TIMESTAMPTZ | N | |
| `updated_at` | TIMESTAMPTZ | N | |

---

## extension_auth_code

웹 로그인 세션에서 발급하는 **익스텐션 1회용 연동 코드** (짧은 TTL). (006)

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK. `gen_random_uuid()` |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE. index |
| `code_hash` | VARCHAR(64) | N | 1회용 코드 해시. UK |
| `expires_at` | TIMESTAMPTZ | N | 코드 만료 시각. index |
| `used_at` | TIMESTAMPTZ | Y | 사용 시각 (소비되면 기록) |
| `created_at` | TIMESTAMPTZ | N | |
| `updated_at` | TIMESTAMPTZ | N | |

---

## user_watch_catalog

인덱서가 저장하는 **시청 기록 정본**. 유저당 최근 60일, 영상(URL)당 1행. 재분석 시 같은 URL은 upsert.

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE |
| `platform` | VARCHAR(20) | N | 플랫폼. 예: `youtube` |
| `title` | TEXT | Y | 영상 제목 |
| `url` | TEXT | N | 영상 URL. `(user_id, url)` UK |
| `channel` | TEXT | N | 채널명 |
| `channel_url` | TEXT | Y | 채널 URL |
| `watched_at` | TIMESTAMPTZ | N | 시청 시각 (Takeout) |
| `youtube_category_id` | VARCHAR(10) | Y | YouTube API `categoryId`. 표시명은 DB에 안 넣음 |
| `duration_sec` | INT | Y | 재생 길이(초). YouTube API |
| `is_shorts` | BOOLEAN | Y | 숏츠 여부. `/shorts/` URL 또는 180초 이하 |
| `description` | TEXT | Y | 영상 설명. YouTube API |
| `tags` | JSONB | Y | 태그 배열. YouTube API |
| `thumbnail_url` | TEXT | Y | 썸네일 URL. video ID 기반 패턴 |
| `embedding_text` | TEXT | Y | 임베딩 입력문 (제목·카테고리·태그·설명 300자) |
| `embedding` | VECTOR(1536) | Y | `embedding_text` OpenAI 임베딩 (추천·유사도) |

**UK:** `(user_id, url)`  
**인덱스:** `(user_id, watched_at DESC)`, `(user_id, youtube_category_id)`, HNSW on `embedding`

> **platform**: 시청 출처. 일반 영상은 `youtube`, YouTube Music(`music.youtube.com` URL 또는 header `YouTube Music`)은 `youtube_music`.

---

## user_subscription

인덱서가 Takeout **구독정보 CSV**(ZIP 내)에서 적재하는 **구독 채널 스냅샷**. 채널(URL) 단위 1행. 분석(업로드)마다 **전체 교체**(구독 취소 반영) — 단, 구독 CSV가 있는 ZIP일 때만. (003)

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK. `gen_random_uuid()` |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE |
| `channel_id` | TEXT | N | Takeout `채널 ID` |
| `channel_url` | TEXT | Y | Takeout `채널 URL` |
| `channel_title` | TEXT | Y | Takeout `채널 제목` |
| `created_at` / `updated_at` | TIMESTAMPTZ | N | |

**UK:** `(user_id, channel_id)` — `uq_usub_user_channel`  
**인덱스:** `ix_usub_user (user_id)`

> 적재만 인덱서 담당. 활용(소비 자율성·아스피레이션)은 **네비게이터** 예정 — 프로파일러 채점엔 미사용.

---

## user_analysis_source

업로드 **소스 파일 1건**당 분석 파이프라인(인덱서 → 프로파일러) 실행 이력. 같은 Takeout 재업로드 시 `completed`면 스킵.

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE |
| `source_key` | VARCHAR(512) | N | `drive:{file_id}` 또는 `upload:{sha256}` |
| `file_name` | TEXT | Y | UI 표시용 파일명 |
| `status` | VARCHAR(20) | N | `running` · `completed` · `failed` |
| `stage` | VARCHAR(20) | N | `status=running` 중 세부단계: `indexing`(분류) · `profiling`(분석). 기본 `indexing` (005_analysis_stage) |
| `profile_history_id` | UUID | Y | FK → `user_profile_history.id` ON DELETE SET NULL |
| `created_at` | TIMESTAMPTZ | N | |
| `updated_at` | TIMESTAMPTZ | N | |

**UK:** `(user_id, source_key)` — `uq_uas_user_source`  
**인덱스:** `(user_id, created_at DESC)`

`source_key` 규칙:
- Drive: `drive:{google_drive_file_id}`
- 직접 업로드: `upload:{파일 내용 SHA-256}`

---

## video_analysis

프로파일러가 **선별한 catalog 행**에 대해 수행한 영상 의미 분석. `catalog_id`당 최대 1행.

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK |
| `catalog_id` | UUID | N | FK → `user_watch_catalog.id` ON DELETE CASCADE. UK |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE |
| `summary_kr` | TEXT | N | 한국어 요약 |
| `tones` | JSONB | N | 톤 분석 결과 |
| `intents` | JSONB | N | 의도 분석 결과 |
| `value_signals` | JSONB | N | 가치 신호 분석 결과 |
| `embedding_text` | TEXT | N | 임베딩에 사용한 원문 |
| `embedding` | VECTOR(1536) | N | 요약 기반 의미 벡터 |
| `created_at` | TIMESTAMPTZ | N | |
| `updated_at` | TIMESTAMPTZ | N | |

> `description`, `tags`, `thumbnail_url`는 catalog에 있음. 조회 시 catalog JOIN. 자막(`transcript`)은 youtube-transcript-api IP 차단으로 수집률 0%라 제거함(008). 의미분석은 제목·설명·태그·카테고리 메타데이터만 사용.

**인덱스:** `(user_id)`, HNSW on `embedding`

---

## user_profile_history

프로파일러가 산출한 **성향 점수 + LLM 해석** 스냅샷 (시점별).

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE |
| `snapshot_date` | TIMESTAMPTZ | N | 스냅샷 기준 시각 |
| `self_direction` | FLOAT | Y | Schwartz — 자기지향 |
| `stimulation` | FLOAT | Y | Schwartz — 자극 |
| `achievement` | FLOAT | Y | Schwartz — 성취 |
| `power` | FLOAT | Y | Schwartz — 권력 |
| `security` | FLOAT | Y | Schwartz — 안전 |
| `benevolence` | FLOAT | Y | Schwartz — 친선 |
| `universalism` | FLOAT | Y | Schwartz — 보편 |
| `hedonism` | FLOAT | Y | Schwartz — 쾌락 |
| `conformity` | FLOAT | Y | Schwartz — 순응 |
| `tradition` | FLOAT | Y | Schwartz — 전통 |
| `novelty_seeking` | FLOAT | Y | 개방성·호기심 |
| `persistence` | FLOAT | Y | 성실성·끈기 |
| `self_transcendence` | FLOAT | Y | 초개인·자기초월 |
| `exploration` | FLOAT | Y | Synapse 8축 — 탐색 |
| `analytical` | FLOAT | Y | Synapse 8축 — 분석 |
| `creativity` | FLOAT | Y | Synapse 8축 — 창의 |
| `execution` | FLOAT | Y | Synapse 8축 — 실행 |
| `achievement_drive` | FLOAT | Y | Synapse 8축 — 성취동기 |
| `autonomy` | FLOAT | Y | Synapse 8축 — 자율 |
| `sociality` | FLOAT | Y | Synapse 8축 — 사회성 |
| `sensitivity` | FLOAT | Y | Synapse 8축 — 감수성 |
| `summary_text` | TEXT | Y | 성향 요약 문장 |
| `persona_label` | VARCHAR(100) | Y | 페르소나 라벨 |
| `behavior_reasoning` | TEXT | Y | 행동·취향 근거 설명 |
| `dominant_traits` | JSONB | Y | 두드러진 특성 목록 |
| `supporting_evidence` | JSONB | Y | 근거 데이터 (영상·지표 등) |
| `tone_of_user` | TEXT | Y | 사용자 말투·톤 요약 |
| `portrait` | JSONB | Y | 초상 프로필: persona_label·keywords·interest(9도메인)·disposition(6축)·style·reasoning. 프로파일러 산출·네비게이터 주 신호 (011→012) |
| `batch_id` | UUID | Y | FK → `analysis_batch.id` ON DELETE SET NULL. 이 스냅샷을 유발한 배치 박제 (010) |
| `created_at` | TIMESTAMPTZ | N | |
| `updated_at` | TIMESTAMPTZ | N | |

**인덱스:** `(user_id, snapshot_date DESC)`

---

## user_ideal_persona

네비게이터용 **이상 자아**. 유저당 여러 개 보관하고 그중 하나만 적용(`is_active`).

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK. `gen_random_uuid()` |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE |
| `source_profile_history_id` | UUID | Y | FK → `user_profile_history.id` ON DELETE SET NULL. 근거 스냅샷 (007) |
| `exploration` | FLOAT | Y | 목표 8축 — 탐색 |
| `analytical` | FLOAT | Y | 목표 8축 — 분석 |
| `creativity` | FLOAT | Y | 목표 8축 — 창의 |
| `execution` | FLOAT | Y | 목표 8축 — 실행 |
| `achievement_drive` | FLOAT | Y | 목표 8축 — 성취동기 |
| `autonomy` | FLOAT | Y | 목표 8축 — 자율 |
| `sociality` | FLOAT | Y | 목표 8축 — 사회성 |
| `sensitivity` | FLOAT | Y | 목표 8축 — 감수성 |
| `persona_label` | TEXT | Y | 이상향 페르소나 명칭 (010) |
| `values_temperament` | JSONB | Y | 설계 원본 13축(가치10+기질3). 8축 파생원본 (011) |
| `target_disposition` | JSONB | Y | 목표 성향 6축 신호 — 화면·재생목록용 (013) |
| `target_interest` | JSONB | Y | 목표 관심 도메인 분포(예 `{"게임":20,"지식·교육":30}`) (013) |
| `taste_keywords` | JSONB | Y | 대화에서 추출한 구체 관심 키워드(재생목록 검색 씨앗). 대화 없으면 null (017) |
| `description` | TEXT | Y | 이상 자아 설명 |
| `is_active` | BOOLEAN | N | 적용 중 여부. 기본 `false` (008) |
| `guide_json` | JSONB | Y | 행동 가이드 캐시 (009) |
| `guide_generated_at` | TIMESTAMPTZ | Y | 가이드 생성 시각 (009) |
| `guide_catalog_count` | INT | Y | 생성 당시 시청기록 수 → 현재 수와 다르면 stale (009) |
| `created_at` | TIMESTAMPTZ | N | |
| `updated_at` | TIMESTAMPTZ | N | |

**인덱스:** `ix_uip_user (user_id)`, `ix_uip_user_active (user_id, is_active)`

---

## navigator_proposal_cache

네비게이터 **이상향 제안 3안 캐시**. (유저 + 분석 스냅샷)별로 LLM 생성 결과를 보관, 같은 스냅샷이면 재사용(refresh 시 덮어씀). (012)

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK. `gen_random_uuid()` |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE |
| `source_profile_history_id` | UUID | N | FK → `user_profile_history.id` ON DELETE CASCADE. 근거 스냅샷 |
| `status` | VARCHAR(20) | N | 생성 상태 — `pending`(백그라운드 생성중) / `ready` / `failed`. 기본 `ready` (016) |
| `proposals_json` | JSONB | Y | 3안 전체 직렬화본. pending 행은 결과 없음 (016에서 nullable) |
| `generated_at` | TIMESTAMPTZ | Y | 생성 시각. pending 행은 없음 (016에서 nullable) |
| `catalog_count` | INT | Y | 생성 당시 시청기록 수 (stale 힌트) |
| `created_at` | TIMESTAMPTZ | N | |
| `updated_at` | TIMESTAMPTZ | N | |

**UK:** `(user_id, source_profile_history_id)` — `uq_npc_user_snapshot`

---

## navigator_playlist

네비게이터 **이상향 기반 YouTube 재생목록**. 이상향(`user_ideal_persona`) 1개에 N개. (001)

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK. `gen_random_uuid()` |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE |
| `ideal_id` | UUID | N | FK → `user_ideal_persona.id` ON DELETE CASCADE |
| `status` | TEXT | N | 생성 상태 — `pending` / `ready` / `failed`. 기본 `ready` (014) |
| `save_status` | TEXT | N | YouTube 저장 상태 — `none` / `saving` / `saved` / `failed`. 기본 `none` (015) |
| `refresh_period` | TEXT | N | 자동 갱신 주기 — `none` / `weekly` / `monthly`. 기본 `none` (018) |
| `last_refreshed_at` | TIMESTAMPTZ | Y | 마지막 (재)생성 시각. 주기 도래 판정용, null이면 미갱신 (019) |
| `title` | TEXT | Y | 자동 `{persona_label} #N`, 사용자 수정 가능 |
| `summary` | TEXT | Y | 재생목록 총평 (LLM 큐레이션) |
| `items_json` | JSONB | Y | 보여줄 영상 10개 |
| `channels_json` | JSONB | Y | 발굴·선택 채널 `{channel_id, title}` — re-RSS 무쿼터 보충 |
| `reservoir_json` | JSONB | Y | 여분 영상 (즉시 교체용) |
| `youtube_playlist_id` | TEXT | Y | 실제 저장 후 채워짐 (Phase B) |
| `created_at` / `updated_at` | TIMESTAMPTZ | N | |

**인덱스:** `ix_np_user_ideal (user_id, ideal_id)`

상세: [navigator/README.md](./navigator/README.md)

---

## scraps

아카이버·큐레이터가 수집한 **웹 페이지·채팅 스크랩** (Gemini 요약·분류). (002)

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK. `gen_random_uuid()` |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE. index |
| `source_type` | VARCHAR(20) | N | `web` \| `chat` |
| `url` | VARCHAR(2048) | Y | 출처 URL |
| `title` | VARCHAR(512) | Y | 제목 |
| `summary` | TEXT | N | LLM 요약 |
| `category` | VARCHAR(512) | N | LLM 분류 |
| `tags` | JSONB | N | 태그 배열 (기본 `[]`) |
| `raw_body_snapshot` | TEXT | Y | 원문 스냅샷 |
| `session_id` | VARCHAR(50) | Y | chat 출처 시 아카이버 세션 ID |
| `created_at` / `updated_at` | TIMESTAMPTZ | N | |

**인덱스:** `ix_scraps_user_id (user_id)`, `ix_scraps_user_created (user_id, created_at)`

---

## scrap_embeddings

스크랩 본문의 **OpenAI 임베딩** (1536차원). `scraps`와 1:1. 스크랩 시맨틱 그래프(코사인 유사도) 조회용. (004_scrap_embeddings)

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `scrap_id` | UUID | N | PK **이자** FK → `scraps.id` ON DELETE CASCADE (1:1) |
| `embedding_text` | TEXT | N | 임베딩 입력 원문 |
| `embedding` | VECTOR(1536) | N | 본문 임베딩 |
| `created_at` / `updated_at` | TIMESTAMPTZ | N | |

**인덱스:** HNSW on `embedding` (`vector_cosine_ops`, `ix_scrap_embeddings_embedding`)

---

## ai_chat_logs

에이전트 통합 **AI 채팅 로그**. Archiver(패시브 웹 맥락)·Curator(챗봇 세션)가 공유한다. `session_id`로 세션 묶음. (005)

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | INTEGER | N | PK. autoincrement |
| `session_id` | VARCHAR(50) | N | 세션 ID. index |
| `user_id` | UUID | N | FK → `users.id`. index |
| `agent_type` | VARCHAR(30) | N | 에이전트 종류 (`archiver`·`curator` 등). index |
| `role` | VARCHAR(20) | N | 메시지 역할 (`user`·`assistant` 등) |
| `content` | TEXT | N | 메시지 본문 |
| `context_url` | VARCHAR(2048) | Y | (아카이버) 패시브 웹 맥락 URL |
| `context_title` | VARCHAR(512) | Y | (아카이버) 패시브 웹 맥락 제목 |
| `content_embedding` | VECTOR(1536) | Y | `content` RAG 임베딩 (과거 지식 검색) |
| `created_at` | TIMESTAMPTZ | N | |

**인덱스:** `(session_id)`, `(user_id)`, `(agent_type)`

---

## user_behavior_logs

익스텐션이 수집하는 **브라우저 탭 체류 세션** 정산 이벤트. 페이지 이탈·탭 전환·포커스 변경 시 1행. 대시보드(`/me/activity`)의 오늘 총 체류시간·도메인 TOP5 집계 원본. (007_user_behavior_logs)

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | INTEGER | N | PK. autoincrement |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE. index |
| `url` | VARCHAR(2048) | N | 정규화된 페이지 URL (쿼리·fragment 제거) |
| `domain` | VARCHAR(255) | N | hostname. index |
| `page_title` | VARCHAR(500) | Y | 페이지 제목 |
| `duration_seconds` | INTEGER | N | 체류 시간(초). 기본 `0`, 최소 1초 이상만 적재 |
| `timestamp` | TIMESTAMPTZ | N | 세션 시각. index |

**인덱스:** `ix_user_behavior_logs_user_timestamp (user_id, timestamp)`, `(domain)`, `(user_id)`, `(timestamp)`

---

## DB에 없는 것 / 레거시

| 항목 | 처리 방식 |
|------|-----------|
| 인덱서 job 상태 | 서버 메모리 (`takeout_status`, `analysis_status`) |
| 프로파일러 job 상태 | 서버 메모리 (`ProfilerService._jobs`) |
| `video_vectors` | 폐기. 미사용 ORM 모델(`VideoVector`)을 제거함. 인덱서 임베딩은 `user_watch_catalog.embedding`이 담당 |
| `user_profile_insight` | 폐기 (003에서 `user_profile_history`로 병합) |
| `user_video_watch`, `user_feature_snapshot`, `indexer_job` | 폐기 (스키마 미포함) |
