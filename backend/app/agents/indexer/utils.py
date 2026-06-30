"""인덱서 공용 유틸 — Takeout 파싱, YouTube 보강 헬퍼, 도메인 상수.

노드(nodes/)는 state 오케스트레이션만 담당하고,
순수 변환·외부 1건 호출은 이 모듈에 둔다.

데이터 출처 요약:
  - Takeout JSON     → preprocess()
  - YouTube Data API → enrich 노드 (category, duration, tags 등)
  - URL 패턴         → thumbnail_url_for()  (API 키·quota 불필요)
"""

import csv
import io
import json
import logging
import re
import zipfile
from datetime import datetime, timezone

# 인덱서·프로파일러 공통 손잡이 (여기서 재노출 → 기존 import 경로 유지)
from app.agents.shared.analysis_window import (  # noqa: F401
    WATCH_CATALOG_WINDOW_DAYS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 도메인 상수
# ---------------------------------------------------------------------------

SHORTS_MAX_DURATION_SEC = 180  # 3분 — is_shorts() 판별 기준 (URL /shorts/ OR 이하)
# 공개 CDN 패턴. videos.list snippet.thumbnails 대신 사용 (quota 0)
YOUTUBE_THUMBNAIL_URL = "https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

# catalog embedding_text
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
        logger.debug(f"[ZIP] 파일 목록 ({len(all_names)}개): {all_names[:20]}")
        for name in all_names:
            if any(target in name for target in target_names):
                logger.info(f"[ZIP] 시청 기록 발견: {name}")
                with z.open(name) as f:
                    data = json.load(f)
                    logger.info(f"[ZIP] 항목 수: {len(data)}")
                    return data
    logger.warning(f"[ZIP] 시청 기록 파일 없음. 전체 목록: {all_names}")
    return []


def parse_takeout_json(json_path: str) -> list[dict]:
    """로컬 JSON 시청 기록 파일 로드."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 구독정보 CSV 파싱 (ZIP 전용 — watch-history.json 단독엔 없음)
# ---------------------------------------------------------------------------

# Takeout 구독 CSV 파일명 토큰 (한/영)
_SUBSCRIPTION_NAME_TOKENS = ("구독정보", "subscriptions")


def _match_subscription_columns(header: list[str]) -> dict[str, int]:
    """구독 CSV 헤더 → 컬럼 인덱스 매핑 (한/영, 컬럼 순서 무관).

    한글: '채널 ID', '채널 URL', '채널 제목' / 영문: 'Channel Id/Url/Title'.
    Takeout 구독 CSV는 이 3컬럼만 있어 단순 키워드 매칭으로 충분.
    """
    idx: dict[str, int] = {}
    for i, col in enumerate(header):
        key = (col or "").strip().lower()
        if "id" in key:
            idx.setdefault("channel_id", i)
        elif "url" in key:
            idx.setdefault("channel_url", i)
        elif "title" in key or "제목" in key:
            idx.setdefault("channel_title", i)
    return idx


def _parse_subscription_csv(text_data: str) -> list[dict]:
    """구독 CSV 본문 → [{channel_id, channel_url, channel_title}] (channel_id dedupe)."""
    reader = csv.reader(io.StringIO(text_data))
    rows = list(reader)
    if not rows:
        return []

    cols = _match_subscription_columns(rows[0])
    id_i = cols.get("channel_id")
    if id_i is None:
        logger.warning("[구독] CSV에서 채널 ID 컬럼을 찾지 못함")
        return []
    url_i = cols.get("channel_url")
    title_i = cols.get("channel_title")

    def _cell(row: list[str], i: int | None) -> str | None:
        if i is None or i >= len(row):
            return None
        value = (row[i] or "").strip()
        return value or None

    result: list[dict] = []
    seen: set[str] = set()
    for row in rows[1:]:
        channel_id = _cell(row, id_i)
        if not channel_id or channel_id in seen:
            continue
        seen.add(channel_id)
        result.append(
            {
                "channel_id": channel_id,
                "channel_url": _cell(row, url_i),
                "channel_title": _cell(row, title_i),
            }
        )
    return result


def parse_subscriptions_zip(zip_path: str) -> tuple[list[dict], bool]:
    """Takeout ZIP에서 구독정보 CSV 추출.

    반환 (구독 행 목록, 파일 발견 여부). 파일이 없으면 ([], False) —
    호출부는 '구독 데이터 없음'으로 보고 기존 구독을 건드리지 않는다
    (빈 목록으로 전체 교체하면 멀쩡한 구독이 삭제되므로).
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            csv_name = None
            for name in z.namelist():
                lower = name.lower()
                if lower.endswith(".csv") and any(
                    token in lower for token in _SUBSCRIPTION_NAME_TOKENS
                ):
                    csv_name = name
                    break
            if csv_name is None:
                logger.info("[구독] ZIP에 구독정보 CSV 없음 → 스킵")
                return [], False
            logger.info(f"[구독] 구독정보 발견: {csv_name}")
            with z.open(csv_name) as f:
                text_data = f.read().decode("utf-8-sig", errors="replace")
    except zipfile.BadZipFile:
        return [], False

    rows = _parse_subscription_csv(text_data)
    logger.info(f"[구독] 파싱 {len(rows)}건")
    return rows, True


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


def detect_platform(item: dict) -> str:
    """Takeout 항목의 URL·header·products에서 플랫폼을 식별한다 (없으면 youtube).

    예: products=["YouTube"] / header="YouTube" → "youtube".
    YouTube Music은 products가 ["YouTube"]로 와서 일반 시청과 구분되지 않으므로,
    titleUrl 호스트(music.youtube.com) 또는 header("YouTube Music")로 먼저 판별한다.
    멀티 플랫폼 확장 대비 — 파일이 알려주는 출처를 그대로 따른다.
    """
    url = item.get("titleUrl", "") or ""
    header = item.get("header", "") or ""
    if "music.youtube.com" in url or header.strip() == "YouTube Music":
        return "youtube_music"
    products = item.get("products")
    if isinstance(products, list) and products and products[0]:
        return str(products[0]).strip().lower().replace(" ", "_")
    if header:
        return str(header).strip().lower().replace(" ", "_")
    return "youtube"


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
                "platform": detect_platform(item),
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
    """catalog 임베딩용 평문 — 제목·채널·카테고리·태그.

    설명(description)은 해시태그·링크·홍보·제목반복 등 노이즈가 많아 제외한다.
    깊은 의미는 video_analysis(자막 요약) 임베딩이 별도로 담당.
    """
    parts: list[str] = []

    title = (item.get("title") or "").strip()
    if title:
        parts.append(f"제목: {title}")

    channel = (item.get("channel") or "").strip()
    if channel and channel.lower() != "unknown":
        parts.append(f"채널: {channel}")

    category = youtube_category_label(item.get("youtube_category_id"))
    if category:
        parts.append(f"카테고리: {category}")

    tags = item.get("tags")
    if isinstance(tags, list) and tags:
        tag_line = ", ".join(str(t).strip() for t in tags[:_TAGS_EMBED_MAX] if t)
        if tag_line:
            parts.append(f"태그: {tag_line}")

    if parts:
        return "\n".join(parts)
    return title or (item.get("url") or "unknown")
