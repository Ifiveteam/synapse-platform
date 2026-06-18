# Indexer — HTTP API

Takeout Drive 연동 · 로컬 업로드 · catalog 조회.  
Base path: `/api/v1`

---

## 1. Takeout (Drive)

Prefix: `/takeout`

### Discover — Takeout 후보 목록

```http
GET /takeout/drive/discover
Authorization: Bearer {token}
```

**목표 응답**

```json
{
  "files": [
    {
      "id": "drive_file_id",
      "name": "takeout-20260616.zip",
      "size": "52428800",
      "modifiedTime": "2026-06-16T10:00:00.000Z",
      "mimeType": "application/zip"
    }
  ]
}
```

- 분석 **시작하지 않음**
- 호환: `GET /takeout/drive/files` (동일)

**Drive 검색 규칙**

- `name contains 'takeout'`
- 폴더 제외, ZIP, size ≥ 200KB
- `modifiedTime` desc

---

### 분석 시작

```http
POST /takeout/drive/trigger/{file_id}?reindex=false
Authorization: Bearer {token}
```

**응답 (즉시)**

```json
{
  "status": "started",
  "task_id": "uuid",
  "file_id": "drive_file_id"
}
```

| Query | 설명 |
|-------|------|
| `reindex=true` | catalog+analysis 삭제 후 전체 재적재 |
| `reindex=false` | upsert 병합 (기본) |

백그라운드: `BackgroundTasks` → ZIP 다운로드 → catalog pipeline.

**폐기 예정:** `POST /takeout/drive/auto` (탭 진입 자동 분석)

---

### Job 상태 조회

```http
GET /takeout/status/{task_id}
```

**진행 중**

```json
{
  "status": "downloading"
}
```

```json
{
  "status": "processing",
  "stage": "enrich",
  "progress": { "done": 100, "total": 640 }
}
```

**완료**

```json
{
  "status": "success",
  "saved": 620,
  "raw_count": 1200,
  "filtered_count": 640,
  "cleaned_count": 640,
  "shorts_count": 280,
  "category_stats": { "22": 150, "28": 80 }
}
```

**실패**

```json
{
  "status": "error",
  "message": "Drive 파일 다운로드 실패"
}
```

| status | 의미 |
|--------|------|
| `not_found` | task_id 없음 또는 서버 재시작 |
| `downloading` | Drive ZIP 수신 중 |
| `processing` | S1~S5 실행 중 |
| `success` | catalog 저장 완료 |
| `error` | 실패 |

저장소: 서버 메모리 `takeout_status` (DB 아님).

---

## 2. Indexer (로컬 업로드)

Prefix: `/indexer`

### 파일 업로드 분석

```http
POST /indexer/analyze
Content-Type: multipart/form-data
Authorization: Bearer {token}

file: takeout.zip | watch-history.json
```

```json
{ "status": "started", "task_id": "uuid" }
```

폴링: `GET /indexer/analyze/{task_id}`

### 재분석 (catalog 삭제 후)

```http
POST /indexer/reindex
```

`reindex=true` pipeline.

### 샘플 (시연)

```http
POST /indexer/analyze/sample
```

`limit=20`만 처리.

---

## 3. Catalog CRUD

### 목록

```http
GET /indexer/videos
Authorization: Bearer {token}
```

```json
[
  {
    "id": "uuid",
    "title": "영상 제목",
    "channel": "채널명",
    "url": "https://www.youtube.com/watch?v=...",
    "watched_at": "2026-06-01 12:00:00",
    "youtube_category_id": "22",
    "tags": ["tag1"],
    "duration": 180,
    "is_shorts": true,
    "thumbnail_url": "https://i.ytimg.com/vi/.../hqdefault.jpg"
  }
]
```

### 전체 삭제

```http
DELETE /indexer/videos
```

`video_analysis` → `user_watch_catalog` 순 삭제.

---

## 4. 프론트 연동

| UI | API |
|----|-----|
| Drive 탭 · 새로고침 | `GET /discover` |
| 「분석 시작」 | `POST /trigger/{file_id}` |
| 진행 표시 | `GET /status/{task_id}` 3초 폴링 |
| 직접 업로드 | `POST /indexer/analyze` |
| 영상 목록 (IndexerPage) | `GET /indexer/videos` |

**localStorage**

- `driveTasks` — `{ [fileId]: { taskId, status } }`
- `driveAnalyzed` — 완료 stats 캐시 (보조)

---

## 5. 환경 변수

| 변수 | 용도 |
|------|------|
| `YOUTUBE_API_KEY` | S4 enrich |
| Google OAuth (`users.access_token`) | Drive 다운로드 |
| `DATABASE_URL` | catalog upsert |
