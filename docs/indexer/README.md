# Indexer

Google Takeout YouTube 시청 기록을 **`user_watch_catalog`**에, 구독정보를 **`user_subscription`**에 적재하는 에이전트. (YouTube Music 시청은 `platform=youtube_music`로 라벨)

> 이 문서 하나로 파이프라인·데이터·API를 모두 다룬다. DB 상세: [../erd.md](../erd.md).

**한 줄 정의:** Takeout 파싱 → 광고·노이즈 제거 → 증분 diff → YouTube API 50개 배치 enrich → 임베딩 → catalog upsert (+구독 전체 교체).

프로파일러(`video_analysis`)·의미 분석·job DB 테이블은 인덱서 범위 밖. job 진행 상태는 DB에 저장하지 않고 서버 메모리(`takeout_status`/`analysis_status`)에만 둔다.

---

## 1. Catalog 파이프라인 (LangGraph 6노드)

**파일:** `agents/indexer/graph.py` · 각 노드는 `should_continue`로 `error` 시 조기 종료(END).

```text
preprocess → diff → enrich → embed → save_catalog → save_subscriptions → END
```

| 노드 | 파일 | 역할 |
|------|------|------|
| `node_preprocess` | `nodes/preprocess.py` | parse · 광고/노이즈 filter · URL당 dedupe · 최근 윈도우 컷 · (ZIP) 구독 CSV 파싱 |
| `node_diff` | `nodes/diff.py` | 기존 catalog와 비교 → 신규(enrich/embed 대상) / 기존(watched_at·watch_count만 갱신) 분리 (증분) |
| `node_enrich` | `nodes/enrich.py` | YouTube `videos.list` 50배치 + 썸네일 URL + 숏츠 판별 |
| `node_embed` | `nodes/embed.py` | `embedding_text` → OpenAI 임베딩(1536) |
| `node_save_catalog` | `nodes/store.py` | `ON CONFLICT (user_id, url) DO UPDATE` upsert |
| `node_save_subscriptions` | `nodes/subscriptions.py` | 구독 CSV 있을 때만 `user_subscription` 전체 교체(delete-all → insert). 없으면 no-op |

Takeout 파싱·헬퍼(ZIP/JSON·광고 필터·플랫폼·구독 CSV·썸네일·숏츠)는 `agents/indexer/utils.py`.

### preprocess 내부
- **filter**: `details`에 `광고` → 제외 · URL은 `watch?v=` 또는 `/shorts/`만 · title 접미사 제거·빈값 제외.
- **dedupe**: URL당 최신 `watched_at` 1건.
- **윈도우**: `analysis_end`=최신 `watched_at`, `analysis_start`=end − `WATCH_CATALOG_WINDOW_DAYS`(≈2달, `agents/shared/analysis_window.py`, 인덱서·프로파일러 공유).

### enrich 필드 출처
| 필드 | 출처 |
|------|------|
| `youtube_category_id` | `snippet.categoryId` |
| `duration_sec` | `contentDetails.duration` (`PT31S`→31) |
| `description` | `snippet.description` |
| `tags` | `snippet.tags` |
| `thumbnail_url` | `https://i.ytimg.com/vi/{video_id}/hqdefault.jpg` (URL 패턴, quota 0. API `snippet.thumbnails`는 fallback) |
| `is_shorts` | `/shorts/` URL **OR** `0 < duration_sec ≤ 180` |

categoryId 없는 행은 catalog·임베딩 대상에서 제외. `embedding_text` = 제목·채널·카테고리·태그.

---

## 2. 데이터 스펙

### Takeout → catalog 매핑
| Takeout | catalog | 비고 |
|---------|---------|------|
| `header` / `titleUrl` | `platform` | 기본 `youtube`. `music.youtube.com` URL 또는 header `"YouTube Music"` → `youtube_music` |
| `title` | `title` | 접미사 제거 |
| `titleUrl` | `url` | upsert 키 `(user_id, url)` |
| `subtitles[0].name` / `.url` | `channel` / `channel_url` | |
| `time` | `watched_at` | ISO → TIMESTAMPTZ |
| `details`(광고) | — | 저장 안 함 |

Takeout JSON에 **없는** 필드(`categoryId`·`description`·`duration`)는 enrich 단계 YouTube API 필수.

### YouTube API
`GET /youtube/v3/videos?part=snippet,contentDetails&id={≤50 ids}&key=…` — quota 1 unit / 50 IDs. API 키 없으면 URL 기반 `thumbnail_url`·`is_shorts`(URL만)만 채우고 나머지 null.

### 숏츠 분류
`is_shorts=true` = (`/shorts/` URL) **OR** (`0 < duration_sec ≤ 180`). `#shorts` 태그는 오탐 방지로 미사용 (`SHORTS_MAX_DURATION_SEC=180`).

### 구독정보 (`user_subscription`)
- 출처: Takeout ZIP 내 `구독정보.csv`(한/영 헤더 `채널 ID/URL/제목`). **ZIP에만 존재** — `watch-history.json` 단독 업로드엔 없어 스킵.
- 갱신: CSV가 있을 때만 전체 교체(구독 취소 반영). 구독 저장 실패는 catalog 결과를 무효화하지 않음.
- 활용: 적재만 인덱서. 소비 자율성·아스피레이션 활용은 네비게이터 예정.

### job 완료 stats
`raw_count`(parse) · `filtered_count`/`cleaned_count` · `saved`(upsert) · `shorts_count` · `category_stats`(categoryId별 Counter).

---

## 3. HTTP API

### Takeout (`app/api/v1/takeout.py`, prefix `/takeout`) — Drive 연동
| Method | Path | 설명 |
|--------|------|------|
| POST | `/drive/folder` | Picker로 고른 감시 폴더 저장(연동 완료) |
| GET | `/drive/connection` | 폴더 연동 여부 + 폴더명 |
| GET | `/schedule` · PUT `/schedule` | 자동분석 주기(1~12개월) 조회/변경 (+`next_analysis_at` 재계산) |
| GET | `/drive/files` | 연동 폴더의 Takeout 파일 목록 + 파일별 상태(new/running/completed/failed) |
| POST | `/drive/auto` | 폴더에서 최신 Takeout 자동 탐지 후 분석 시작 |
| POST | `/drive/trigger/{file_id}` | 지정 파일 분석 시작 (`?batch_id=` optional) |
| GET | `/status/{task_id}` | 인메모리 job 상태(downloading/processing/success/error) |

### Indexer (`app/api/v1/indexer.py`, prefix `/indexer`) — 직접 업로드·조회
| Method | Path | 설명 |
|--------|------|------|
| POST | `/analyze` | Takeout JSON/ZIP 업로드 → 백그라운드 분석 (`batch_id` Form optional) |
| POST | `/analyze/sample` | 샘플 모드(20개, 시연용) |
| POST | `/batch/{batch_id}/seal` | 업로드 "다 보냄" — 배치 닫고 조건 되면 프로파일러 1회 트리거 |
| GET | `/analyze/{task_id}` | 분석 결과 조회 |
| GET | `/videos` · DELETE `/videos` | 수집 영상 목록 조회 / catalog·분석·구독·소스 이력 전체 삭제 |
| GET | `/graph-summary` | 시청 그래프용 catalog 집계(상위 카테고리·채널, 최근 2달) |
| GET | `/embedding-graph` | 영상 임베딩 PCA 2D 투영(`?snapshot_id=`면 그 배치 영상만, 아니면 최근 2달 최대 2000개) |
| GET | `/status` | 인덱서 헬스체크 |

> 재분석은 `POST /drive/trigger`의 upsert가 기본. 같은 소스(`drive:{file_id}`/`upload:{sha256}`)가 `completed`면 스킵. **`GET /takeout/drive/discover`·`POST /indexer/reindex`는 존재하지 않음**(과거 문서 잔재).

공통: 같은 유저는 `indexer_service.enqueue`로 **직렬 큐**에 등록돼 하나씩 순차 인덱싱. 프로파일러 트리거는 IndexerService가 profile-once 정책으로 처리.

---

## 4. 코드 위치 · 폐기

| 구분 | 경로 |
|------|------|
| LangGraph·노드 | `agents/indexer/graph.py`, `nodes/{preprocess,diff,enrich,embed,store,subscriptions}.py` |
| 파싱·헬퍼 | `agents/indexer/utils.py` |
| Repository | `repositories/indexer_repository.py` (`upsert_catalog_records`·`fetch_graph_summary`·`fetch_catalog_embedding_rows` 등) |
| ORM | `models/user_watch_catalog.py`, `user_subscription.py` |
| API | `api/v1/takeout.py`, `api/v1/indexer.py` |
| Drive 서비스 | `services/takeout_service.py` (검색·다운로드·`run_takeout_pipeline`) |
| 프론트 | `frontend/src/components/upload/` (업로드·Drive 연동 UI) |

**폐기·미사용:** `user_video_watch`·`user_feature_snapshot`·`indexer_job` 테이블(catalog가 정본, 메모리 job으로 충분), GPT `classify`(YouTube `categoryId` 사용), heavy enrich(프로파일러 선별로 이전).
