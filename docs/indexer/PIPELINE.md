# Indexer — Catalog Pipeline

Takeout/ZIP 입력부터 `user_watch_catalog` upsert까지의 5단계 파이프라인.

---

## 1. 흐름 요약

```text
[분석 시작]
  preprocess      parse + filter + dedupe + 60일  (Takeout 기본 데이터)
  enrich_api      YouTube videos.list 50배치
  attach_derived  썸네일 URL + 숏츠 (API 없음)
  save_catalog    user_watch_catalog upsert
```

LangGraph 노드 = 위 4단계 (`preprocess` → `enrich_api` → `attach_derived` → `save_catalog`).

데이터 필드 매핑: [DATA.md](./DATA.md)

---

## 2. 노드 파일 (`nodes/`)

| 파일 | LangGraph 노드 | 역할 |
|------|----------------|------|
| `preprocess.py` | `node_preprocess` | parse · filter · dedupe · 60일 |
| `enrich_api.py` | `node_enrich_api` | YouTube API |
| `attach_derived.py` | `node_attach_derived` | 썸네일 · 숏츠 |
| `store.py` | `node_save_catalog` | catalog upsert |

메모리에서 ①②③을 붙인 뒤 **save 한 번**에 catalog 저장 (MVP).

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

## 4. enrich_api 노드

YouTube `videos.list` — `part=snippet,contentDetails`

| 필드 | API |
|------|-----|
| `youtube_category_id` | `snippet.categoryId` |
| `duration_sec` | `contentDetails.duration` |
| `description` | `snippet.description` |
| `tags` | `snippet.tags` |

**채우지 않음:** `thumbnail_url`, `is_shorts` (다음 노드)

---

## 5. attach_derived 노드

| 필드 | 규칙 |
|------|------|
| `thumbnail_url` | `i.ytimg.com/vi/{id}/hqdefault.jpg` |
| `is_shorts` | `/shorts/` OR `duration_sec ≤ 180` |

---

## 6. save_catalog 노드

- `ON CONFLICT (user_id, url) DO UPDATE`

---

## 7. LangGraph (MVP)

```text
preprocess → enrich_api → attach_derived → save_catalog → END
```

| 파일 | 노드 |
|------|------|
| `preprocess.py` | `node_preprocess` |
| `enrich_api.py` | `node_enrich_api` |
| `attach_derived.py` | `node_attach_derived` |
| `store.py` | `node_save_catalog` |

**MVP에서 제외 (나중에):** `start`, `delete`(reindex), `log`

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
