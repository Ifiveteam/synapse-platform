# Synapse DB 스키마

PostgreSQL 17 · `pgvector` · `pgcrypto`  
마이그레이션: `backend/alembic/versions/001_initial_schema.py` … `004_user_analysis_source.py`

---

## 테이블 관계 (요약)

| 테이블 | 설명 | 관계 |
|--------|------|------|
| `users` | 사용자 | `user_token` 1:1 |
| `user_token` | 로그인·Google 토큰 | → `users` |
| `user_watch_catalog` | 시청 기록 정본 (인덱서) | → `users`, ← `video_analysis` 0~1 |
| `user_analysis_source` | 업로드 소스별 분석 이력 (중복 방지) | → `users`, → `user_profile_history` 0~1 |
| `video_analysis` | 영상 LLM 분석 (프로파일러) | → `users`, → `user_watch_catalog` 1:1 |
| `user_profile_history` | 성향 점수 + LLM 해석 스냅샷 | → `users` |
| `user_ideal_persona` | 이상 자아 (네비게이터) | → `users` |

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
| `analysis_interval` | VARCHAR(50) | N | 프로파일러 분석 주기. 기본 `WEEKLY` |
| `next_analysis_at` | TIMESTAMPTZ | N | 다음 프로파일 분석 예정 시각 |
| `created_at` | TIMESTAMPTZ | N | 가입 시각 |

**인덱스:** `ix_users_next_analysis (next_analysis_at)`

---

## user_token

서비스 세션 토큰과 Google refresh token. `users`와 1:1.

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE. UK |
| `refresh_token` | VARCHAR(512) | N | 서비스 자체 refresh token |
| `google_refresh_token` | VARCHAR(512) | Y | Google OAuth refresh token |
| `expires_at` | TIMESTAMPTZ | N | 서비스 refresh token 만료 시각 |
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

네비게이터용 **이상 자아** 목표 점수 (Synapse 8축).

| 컬럼 | 타입 | NULL | 설명 |
|------|------|:----:|------|
| `id` | UUID | N | PK |
| `user_id` | UUID | N | FK → `users.id` ON DELETE CASCADE |
| `exploration` | FLOAT | Y | 목표 — 탐색 |
| `analytical` | FLOAT | Y | 목표 — 분석 |
| `creativity` | FLOAT | Y | 목표 — 창의 |
| `execution` | FLOAT | Y | 목표 — 실행 |
| `achievement_drive` | FLOAT | Y | 목표 — 성취동기 |
| `autonomy` | FLOAT | Y | 목표 — 자율 |
| `sociality` | FLOAT | Y | 목표 — 사회성 |
| `sensitivity` | FLOAT | Y | 목표 — 감수성 |
| `description` | TEXT | Y | 이상 자아에 대한 설명 |
| `created_at` | TIMESTAMPTZ | N | |
| `updated_at` | TIMESTAMPTZ | N | |

**인덱스:** `(user_id)`

---

## DB에 없는 것

| 항목 | 처리 방식 |
|------|-----------|
| 인덱서 job 상태 | 서버 메모리 (`takeout_status`, `analysis_status`) |
| 프로파일러 job 상태 | 서버 메모리 (`ProfilerService._jobs`) |
| `user_video_watch`, `user_feature_snapshot`, `video_vectors`, `indexer_job` | 폐기 (스키마 미포함) |
