# Synapse DB 스키마

PostgreSQL 17 · `pgvector` · `pgcrypto`  
마이그레이션 (실제 파일):
`001_initial_schema` → `002_create_scraps` → `003_user_subscription` (**현재 head**)

> 초기 스키마는 `001_initial_schema` **한 파일에 통합**돼 있다(과거 007~013 등 개별 마이그레이션은 통합됨, 실파일 없음). 이후 `scraps`(002), `user_subscription`(003)만 별도 추가. 새 마이그레이션은 `down_revision`을 직전 head로 지정.

---

## 테이블 관계 (요약)

| 테이블 | 설명 | 관계 |
|--------|------|------|
| `users` | 사용자 | `user_token` 1:1 |
| `user_token` | 로그인·Google·익스텐션 토큰 | → `users` |
| `extension_auth_code` | 웹→익스텐션 1회용 연동 코드 | → `users` |
| `user_watch_catalog` | 시청 기록 정본 (인덱서) | → `users`, ← `video_analysis` 0~1 |
| `user_subscription` | 구독 채널 스냅샷 (인덱서, 003) | → `users` |
| `user_analysis_source` | 업로드 소스별 분석 이력 (중복 방지) | → `users`, → `user_profile_history` 0~1 |
| `video_analysis` | 영상 LLM 분석 (프로파일러) | → `users`, → `user_watch_catalog` 1:1 |
| `user_profile_history` | 성향 점수 + LLM 해석 스냅샷 | → `users` |
| `user_ideal_persona` | 이상 자아 (네비게이터) | → `users`, → `user_profile_history` 0~1 |
| `navigator_proposal_cache` | 이상향 제안 3안 캐시 (네비게이터) | → `users`, → `user_profile_history` |
| `navigator_playlist` | 이상향 기반 YouTube 재생목록 (네비게이터) | → `users`, → `user_ideal_persona` |
| `scraps` | 웹·채팅 스크랩 요약 (아카이버·큐레이터, 002) | → `users` |
| `ai_chat_logs` | 통합 AI 채팅 로그 (Archiver·Curator) | → `users` |

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
| `extension_refresh_token` | VARCHAR(512) | Y | 익스텐션 세션 refresh token (006) |
| `extension_expires_at` | TIMESTAMPTZ | Y | 익스텐션 refresh token 만료 시각 (006) |
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
| `profile_history_id` | UUID | Y | FK → `user_profile_history.id` ON DELETE SET NULL |
| `created_at` | TIMESTAMPTZ | N | |
| `updated_at` | TIMESTAMPTZ | N | |

**UK:** `(user_id, source_key)`  
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
| `transcript` | TEXT | Y | 자막 텍스트. 프로파일러가 수집 (youtube-transcript-api) |
| `embedding_text` | TEXT | N | 임베딩에 사용한 원문 |
| `embedding` | VECTOR(1536) | N | 요약 기반 의미 벡터 |
| `created_at` | TIMESTAMPTZ | N | |
| `updated_at` | TIMESTAMPTZ | N | |

> `description`, `tags`, `thumbnail_url`는 catalog에 있음. `transcript`는 video_analysis에 저장. 조회 시 catalog JOIN.

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
| `proposals_json` | JSONB | N | 3안 전체(13축+8축+persona+reasoning) 직렬화본 |
| `generated_at` | TIMESTAMPTZ | N | 생성 시각 |
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
| `title` | TEXT | Y | 자동 `{persona_label} #N`, 사용자 수정 가능 |
| `summary` | TEXT | Y | 재생목록 총평 (LLM 큐레이션) |
| `items_json` | JSONB | Y | 보여줄 영상 10개 |
| `channels_json` | JSONB | Y | 발굴·선택 채널 `{channel_id, title}` — re-RSS 무쿼터 보충 |
| `reservoir_json` | JSONB | Y | 여분 영상 (즉시 교체용) |
| `youtube_playlist_id` | TEXT | Y | 실제 저장 후 채워짐 (Phase B) |
| `created_at` / `updated_at` | TIMESTAMPTZ | N | |

**인덱스:** `ix_np_user_ideal (user_id, ideal_id)`

계획: [navigator/PLAN_youtube_playlist.md](./navigator/PLAN_youtube_playlist.md)

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

## DB에 없는 것 / 레거시

| 항목 | 처리 방식 |
|------|-----------|
| 인덱서 job 상태 | 서버 메모리 (`takeout_status`, `analysis_status`) |
| 프로파일러 job 상태 | 서버 메모리 (`ProfilerService._jobs`) |
| `video_vectors` | 폐기. 미사용 ORM 모델(`VideoVector`)을 제거함. 인덱서 임베딩은 `user_watch_catalog.embedding`이 담당 |
| `user_profile_insight` | 폐기 (003에서 `user_profile_history`로 병합) |
| `user_video_watch`, `user_feature_snapshot`, `indexer_job` | 폐기 (스키마 미포함) |
