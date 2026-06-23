# Indexer — 데이터 스펙

`user_watch_catalog` 컬럼 출처, Takeout 매핑, YouTube API, 숏츠 규칙.

> DDL 전체: [../erd.md](../erd.md#user_watch_catalog--시청-정본-인덱서--l0)

---

## 1. Catalog 필드 출처

| 컬럼 | 출처 | 파이프라인 단계 |
|------|------|-----------------|
| `user_id` | JWT / job context | S5 |
| `platform` | Takeout `header` → `youtube` | S2 |
| `title` | Takeout `title` (접미사 제거) | S2 |
| `url` | Takeout `titleUrl` | S2 |
| `channel` | Takeout `subtitles[0].name` | S2 |
| `channel_url` | Takeout `subtitles[0].url` | S2 |
| `watched_at` | Takeout `time` | S2 |
| `youtube_category_id` | API `snippet.categoryId` | S4 |
| `duration_sec` | API `contentDetails.duration` | S4 |
| `description` | API `snippet.description` | S4 |
| `tags` | API `snippet.tags` | S4 |
| `thumbnail_url` | **URL videoId** (아래 §2) | S4 |
| `is_shorts` | URL + duration (§3) | S4 |
| `embedding` | (선택) title+channel | — |

**UNIQUE:** `(user_id, url)` — 재시청 시 upsert 갱신.

---

## 2. 썸네일 URL

Takeout·API 없이 videoId만으로 생성 가능.

```text
https://i.ytimg.com/vi/{video_id}/hqdefault.jpg
```

- `video_id` 추출: `watch?v=` 또는 `/shorts/` 뒤 ID
- 구현: `tool.extract_video_id`, `tool.thumbnail_url_for`
- 상수: `constants.YOUTUBE_THUMBNAIL_URL`
- **정책:** URL 패턴 우선, API `snippet.thumbnails`는 fallback

---

## 3. 숏츠 분류

YouTube API에 `isShorts` 필드 **없음**.

`is_shorts = true` 조건 (**OR**):

```text
1. url에 "/shorts/" 포함
2. duration_sec > 0 AND duration_sec <= 180   (3분 이하)
```

| 예 | 결과 |
|----|------|
| `youtube.com/shorts/abc` | true |
| `watch?v=...` + 90초 | true |
| `watch?v=...` + 10분 | false |

- 상수: `constants.SHORTS_MAX_DURATION_SEC = 180`
- **사용 안 함:** `#shorts` tags (오탐 방지)

---

## 4. Takeout → Catalog 매핑

| Takeout 필드 | catalog | 비고 |
|--------------|---------|------|
| `header` | `platform` | `"YouTube"` → `youtube` |
| `title` | `title` | 접미사 제거 |
| `titleUrl` | `url` | upsert 키 |
| `subtitles[0].name` | `channel` | |
| `subtitles[0].url` | `channel_url` | |
| `time` | `watched_at` | ISO → TIMESTAMPTZ |
| `details` (광고) | — | **저장 안 함** |
| `products`, `activityControls` | — | 미사용 |

Takeout JSON에 **없는** 필드: `categoryId`, `description`, `duration` → S4 API 필수.

---

## 5. YouTube API

```http
GET https://www.googleapis.com/youtube/v3/videos
  ?part=snippet,contentDetails
  &id={comma_separated_ids}
  &key={YOUTUBE_API_KEY}
```

| API 필드 | catalog |
|----------|---------|
| `snippet.categoryId` | `youtube_category_id` |
| `snippet.description` | `description` |
| `contentDetails.duration` | `duration_sec` (`PT31S` → 31) |
| `snippet.tags` | `tags` |

**quota:** 1 unit / 최대 50 IDs.

### categoryId → 표시명 (DB 미저장)

| ID | 이름 (KR 예) |
|----|--------------|
| 10 | 음악 |
| 20 | 게임 |
| 22 | 인물/블로그 |
| 24 | 엔터테인먼트 |
| 27 | 교육 |
| 28 | 과학/기술 |

앱 상수: `external_trends._YOUTUBE_CATEGORY_BY_ID`, `frontend/src/lib/youtube-categories.ts`

---

## 6. 집계 (snapshot 테이블 없음)

`compute_catalog_stats(user_id)` 반환:

```json
{
  "total": 640,
  "shorts_count": 280,
  "long_count": 360,
  "category_stats": { "22": 150, "28": 80 },
  "channel_top5": [{ "name": "채널명", "count": 42 }]
}
```

---

## 7. 재분석 · 삭제

| 모드 | 동작 |
|------|------|
| **upsert** (기본) | `(user_id, url)` 충돌 시 메타·`watched_at` 갱신 |
| **reindex** | `video_analysis` → `user_watch_catalog` 삭제 후 S1~S5 |

API: `DELETE /indexer/videos` — 동일 삭제 순서.
