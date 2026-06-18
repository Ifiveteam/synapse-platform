"""인덱서 공용 유틸 — Takeout 파싱, YouTube 보강 헬퍼, 도메인 상수.

노드(nodes/)는 state 오케스트레이션만 담당하고,
순수 변환·외부 1건 호출은 이 모듈에 둔다.

데이터 출처 요약:
  - Takeout JSON     → preprocess()
  - YouTube Data API → enrich 노드 (category, duration, tags 등)
  - URL 패턴         → thumbnail_url_for()  (API 키·quota 불필요)
"""

import json
import re
import zipfile
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# 도메인 상수
# ---------------------------------------------------------------------------

SHORTS_MAX_DURATION_SEC = 180  # 3분 — is_shorts() 판별 기준 (URL /shorts/ OR 이하)
WATCH_CATALOG_WINDOW_DAYS = 60  # preprocess — catalog에 넣을 시청 기록 일수
# 공개 CDN 패턴. videos.list snippet.thumbnails 대신 사용 (quota 0)
YOUTUBE_THUMBNAIL_URL = "https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

# catalog embedding_text
_DESCRIPTION_EMBED_MAX = 300
_TAGS_EMBED_MAX = 10
# YouTube categoryId → 한글 (embedding_text용, DB 미저장)
_YOUTUBE_CATEGORY_LABELS: dict[str, str] = {
    "1": "영화/애니메이션",
    "2": "자동차",
    "10": "음악",
    "15": "애완동물",
    "17": "스포츠",
    "19": "여행/이벤트",
    "20": "게임",
    "22": "인물/블로그",
    "23": "코미디",
    "24": "엔터테인먼트",
    "25": "뉴스/정치",
    "26": "노하우/스타일",
    "27": "교육",
    "28": "과학/기술",
    "29": "비영리/사회운동",
}


def youtube_category_label(category_id: str | None) -> str | None:
    if not category_id:
        return None
    return _YOUTUBE_CATEGORY_LABELS.get(str(category_id))


def has_classified_category(item: dict) -> bool:
    """YouTube categoryId가 있는 행만 catalog·임베딩 대상."""
    cat = item.get("youtube_category_id")
    if cat is None:
        return False
    text = str(cat).strip()
    return bool(text) and text.lower() != "unknown"


def filter_classified_catalog_items(items: list[dict]) -> tuple[list[dict], int]:
    """카테고리 없는 행 제거. (유지 목록, 제외 건수)"""
    kept = [item for item in items if has_classified_category(item)]
    return kept, len(items) - len(kept)


# ---------------------------------------------------------------------------
# Takeout 파싱 · 전처리
# ---------------------------------------------------------------------------


def parse_takeout_zip(zip_path: str) -> list[dict]:
    """구글 테이크아웃 ZIP에서 watch-history.json(또는 한글 파일명) 추출."""
    target_names = ["watch-history.json", "시청_기록.json", "시청 기록.json"]

    with zipfile.ZipFile(zip_path, "r") as z:
        all_names = z.namelist()
        print(f"[ZIP] 파일 목록 ({len(all_names)}개): {all_names[:20]}")
        for name in all_names:
            if any(target in name for target in target_names):
                print(f"[ZIP] 시청 기록 발견: {name}")
                with z.open(name) as f:
                    data = json.load(f)
                    print(f"[ZIP] 항목 수: {len(data)}")
                    return data
    print(f"[ZIP] 시청 기록 파일 없음. 전체 목록: {all_names}")
    return []


def parse_takeout_json(json_path: str) -> list[dict]:
    """로컬 JSON 시청 기록 파일 로드."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_ad(item: dict) -> bool:
    """Takeout details에 '광고' 포함 시 True — catalog 제외."""
    details = item.get("details", [])
    return any("광고" in d.get("name", "") for d in details)


def extract_title(raw_title: str) -> str:
    """'…을(를) 시청했습니다.' 접미사 제거."""
    return re.sub(r"\s*을\(를\)\s*시청했습니다\.$", "", raw_title).strip()


def normalize_timestamp(time_str: str) -> str:
    """Takeout time → UTC 'YYYY-MM-DD HH:MM:SS'."""
    if not time_str:
        return ""
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return time_str


def preprocess(data: list[dict]) -> list[dict]:
    """Takeout raw → 인덱서 최소 행 (광고·비-YouTube URL 제외)."""
    cleaned = []
    for item in data:
        if is_ad(item):
            continue
        url = item.get("titleUrl", "")
        if "watch?v=" not in url and "/shorts/" not in url:
            continue
        title = extract_title(item.get("title", "")).strip()
        if not title:
            continue
        subtitles = item.get("subtitles", [])
        channel = subtitles[0].get("name", "") if subtitles else ""
        channel_url = subtitles[0].get("url", "") if subtitles else ""
        watched_at = normalize_timestamp(item.get("time", ""))
        cleaned.append(
            {
                "title": title,
                "channel": channel,
                "channel_url": channel_url,
                "url": url,
                "watched_at": watched_at,
            }
        )
    return cleaned


# ---------------------------------------------------------------------------
# YouTube URL · 썸네일 · 숏츠 · 자막
# ---------------------------------------------------------------------------


def extract_video_id(url: str) -> str | None:
    """watch?v= / shorts/ URL에서 11자리 video ID 추출."""
    m = re.search(r"(?:v=|shorts/)([^&?/]+)", url)
    return m.group(1) if m else None


_extract_video_id = extract_video_id  # enrich 노드 내부 alias


def thumbnail_url_for(url: str) -> str | None:
    """썸네일 URL — video ID로 i.ytimg.com 패턴 조합.

    YouTube Data API 미사용. enrich 노드에서 catalog.thumbnail_url에 저장.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None
    return YOUTUBE_THUMBNAIL_URL.format(video_id=video_id)


def parse_duration_iso(duration_str: str) -> int:
    """YouTube API contentDetails.duration (ISO 8601, 예: PT4M13S) → 초."""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str or "PT0S")
    if not m:
        return 0
    return (
        int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)
    )


_parse_duration = parse_duration_iso


def is_shorts(url: str, duration_sec: int | None) -> bool:
    """숏츠 판별 — URL에 /shorts/ 포함 OR 0 < duration ≤ SHORTS_MAX_DURATION_SEC.

    tags #shorts는 사용하지 않음.
    """
    if "/shorts/" in url:
        return True
    if duration_sec and 0 < duration_sec <= SHORTS_MAX_DURATION_SEC:
        return True
    return False


def build_catalog_embedding_text(item: dict) -> str:
    """catalog 임베딩용 평문 — 제목·카테고리·태그·설명(앞 300자).

    재생목록/유사 영상 추천용. 채널명은 넣지 않음.
    """
    parts: list[str] = []

    title = (item.get("title") or "").strip()
    if title:
        parts.append(f"제목: {title}")

    category = youtube_category_label(item.get("youtube_category_id"))
    if category:
        parts.append(f"카테고리: {category}")

    tags = item.get("tags")
    if isinstance(tags, list) and tags:
        tag_line = ", ".join(str(t).strip() for t in tags[:_TAGS_EMBED_MAX] if t)
        if tag_line:
            parts.append(f"태그: {tag_line}")

    description = (item.get("description") or "").strip()
    if description:
        parts.append(f"설명: {description[:_DESCRIPTION_EMBED_MAX]}")

    if parts:
        return "\n".join(parts)
    return title or (item.get("url") or "unknown")
