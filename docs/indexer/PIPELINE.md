# Indexer — Catalog Pipeline

Takeout/ZIP 입력부터 `user_watch_catalog` upsert까지의 5단계 파이프라인.

---

## 1. 흐름 요약

```text
[분석 시작]
  preprocess          parse + filter + dedupe + 60일 윈도우 (+ZIP이면 구독 CSV 파싱)
  diff                기존 catalog와 비교 → 신규 / 기존(메타만 갱신) 분리 (증분)
  enrich              YouTube videos.list 50배치 + 썸네일 URL + 숏츠 판별
  embed               catalog embedding_text → OpenAI 임베딩
  save_catalog        user_watch_catalog upsert (+기존 watch_count·watched_at 갱신)
  save_subscriptions  구독 CSV 있을 때만 user_subscription 전체 교체
```

LangGraph 노드 = 위 6단계 (`preprocess` → `diff` → `enrich` → `embed` → `save_catalog` → `save_subscriptions`).

데이터 필드 매핑: [DATA.md](./DATA.md)

---

## 2. 노드 파일 (`nodes/`)

| 파일 | LangGraph 노드 | 역할 |
|------|----------------|------|
| `preprocess.py` | `node_preprocess` | parse · filter · dedupe · 60일 · (ZIP) 구독 CSV 파싱 |
| `diff.py` | `node_diff` | 기존 catalog와 비교 → 신규 / 기존 분리 (증분) |
| `enrich.py` | `node_enrich` | YouTube API + 썸네일 URL + 숏츠 |
| `embed.py` | `node_embed` | catalog embedding_text → OpenAI 임베딩 |
| `store.py` | `node_save_catalog` | catalog upsert + 기존 메타 갱신 |
| `subscriptions.py` | `node_save_subscriptions` | 구독 전체 교체 (CSV 있을 때만) |

---

## 3. preprocess 노드 (내부 단계)

### parse

| 입력 | ZIP 또는 JSON 경로 |
| 출력 | Takeout raw 배열 |

### filter

| 규칙 | 처리 |
|------|------|
| 광고 | `details`에 `광고` → 제외 |
| URL | `watch?v=` 또는 `/shorts/` |
| title | 접미사 제거, 빈값 제외 |
| platform | `"youtube"` |

### dedupe

URL당 **최신 `watched_at`** 1건.

### 60일 윈도우

- `analysis_end` = 최신 `watched_at`
- `analysis_start` = end − 60일
- 상수: `constants.WATCH_CATALOG_WINDOW_DAYS`

---

## 4. diff 노드

기존 catalog(임베딩 완료 URL)와 비교해 **신규**(enrich/embed 대상)와 **기존**(watched_at·watch_count만 갱신)을 분리 — 증분 인덱싱.

---

## 5. enrich 노드

YouTube `videos.list`(`part=snippet,contentDetails`) + URL 기반 썸네일·숏츠를 **한 노드에서** 처리.

| 필드 | 출처 |
|------|------|
| `youtube_category_id` | `snippet.categoryId` |
| `duration_sec` | `contentDetails.duration` |
| `description` | `snippet.description` |
| `tags` | `snippet.tags` |
| `thumbnail_url` | `i.ytimg.com/vi/{id}/hqdefault.jpg` (URL 패턴, quota 0) |
| `is_shorts` | `/shorts/` OR `duration_sec ≤ 180` |

카테고리(categoryId) 없는 행은 catalog·임베딩 대상에서 제외.

---

## 6. embed 노드

`embedding_text`(제목·채널·카테고리·태그) → OpenAI 임베딩(1536) → catalog `embedding`.

---

## 6b. save_catalog · save_subscriptions 노드

- `save_catalog`: 신규 `ON CONFLICT (user_id, url) DO UPDATE`, 기존은 watched_at·watch_count만 갱신.
- `save_subscriptions`: 구독 CSV가 있던 경우에만 `user_subscription` 전체 교체(delete-all → insert). 없으면 no-op. 구독 저장 실패는 catalog 결과를 무효화하지 않음.

---

## 7. LangGraph (MVP)

```text
preprocess → diff → enrich → embed → save_catalog → save_subscriptions → END
```

각 노드는 `should_continue`로 `error` 시 조기 종료(END). 구독 노드는 `save_catalog` 성공 후 실행되며, 구독 CSV가 없으면 no-op.

---

## 8. 진입점

| Drive `POST /takeout/drive/trigger/{id}` | upsert | BackgroundTasks |
| 로컬 `POST /indexer/analyze` | upsert | BackgroundTasks |

공통: `takeout_service.run_takeout_pipeline` → graph / catalog_pipeline

---

## 5. 산출 stats (job 완료 시)

| 필드 | 의미 |
|------|------|
| `raw_count` | S1 parse 건수 |
| `filtered_count` / `cleaned_count` | S2 후 건수 |
| `saved` | S5 upsert 건수 |
| `shorts_count` | `is_shorts=true` 건수 |
| `category_stats` | `youtube_category_id`별 Counter |

집계 쿼리: `compute_catalog_stats()` — UI·API 공용.

---

## 6. Quota · 성능

| 항목 | 수치 |
|------|------|
| videos.list | 1 unit / 50 IDs |
| ~640 catalog | ~13 units / 1회 분석 |
| 처리 시간 | 다운로드 + API → 수 분 이내 (MVP) |

API 키 없을 때: URL 기반 `thumbnail_url`·`is_shorts`(URL만), API 필드 null/빈값.
