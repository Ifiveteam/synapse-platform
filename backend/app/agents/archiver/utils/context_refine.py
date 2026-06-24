"""탭 URL·제목 정제 및 본문 빈약 판별 — search/collect 공용 (순환 import 방지)."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.agents.archiver.core.constants import THIN_CONTEXT_BODY_CHARS
from app.agents.archiver.models import NO_CONTEXT_TITLE, NO_CONTEXT_URL
from app.agents.archiver.utils.context_body_quality import is_meaningful_context_body

_TITLE_SEP = re.compile(r"\s*[-|·•—:]{1,3}\s+")

_TRACKING_QUERY_KEYS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "ref",
        "source",
        "spm",
        "igshid",
    }
)


def _looks_like_site_suffix(segment: str) -> bool:
    stripped = segment.strip()
    if not stripped:
        return True
    if len(stripped) <= 24 and not re.search(r"[\uac00-\ud7a3]", stripped):
        return True
    if len(stripped) <= 12:
        return True
    if re.fullmatch(r"[\w\s.&]+", stripped) and len(stripped.split()) <= 3:
        return True
    return False


def clean_context_title(title: str | None) -> str:
    """탭 제목에서 플랫폼 노이즈 접미사를 벗겨 주제 명칭을 남긴다."""
    normalized = (title or "").strip()
    if not normalized or normalized == NO_CONTEXT_TITLE:
        return ""

    parts = [part.strip() for part in _TITLE_SEP.split(normalized) if part.strip()]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]

    if _looks_like_site_suffix(parts[-1]) and len(parts[0]) >= 2:
        return parts[0]

    return max(parts, key=len)


def clean_context_url(url: str | None) -> str:
    """URL에서 추적 파라미터·fragment를 제거한다."""
    normalized = (url or "").strip()
    if not normalized or normalized in {NO_CONTEXT_URL, "N/A"}:
        return ""

    try:
        parsed = urlparse(normalized)
        if not parsed.scheme or not parsed.netloc:
            return normalized

        filtered_query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=False)
            if key.lower() not in _TRACKING_QUERY_KEYS
            and not key.lower().startswith("utm_")
        ]
        query = urlencode(filtered_query, doseq=True)
        path = parsed.path.rstrip("/") or "/"
        return urlunparse((parsed.scheme, parsed.netloc, path, "", query, ""))
    except Exception:
        return normalized


def extract_url_search_hint(url: str | None) -> str:
    """경로·호스트에서 검색 쿼리 보조 힌트를 추출한다."""
    cleaned = clean_context_url(url)
    if not cleaned:
        return ""

    try:
        parsed = urlparse(cleaned)
    except Exception:
        return ""

    segments = [segment for segment in parsed.path.split("/") if segment]
    if segments:
        tail = segments[-1]
        decoded = re.sub(r"[-_]+", " ", tail)
        decoded = re.sub(r"\.[a-z0-9]{1,6}$", "", decoded, flags=re.IGNORECASE)
        if len(decoded) >= 2 and re.search(r"[\uac00-\ud7a3a-zA-Z]", decoded):
            return decoded.strip()

    host = parsed.netloc.removeprefix("www.")
    if host and host not in {"localhost", "127.0.0.1"}:
        return host.split(".")[0]

    return ""


def is_thin_context_body(text: str | None) -> bool:
    """DOM·스크래핑 본문이 질문 답변에 부족할 정도로 짧은지 판별한다."""
    normalized = (text or "").strip()
    if not is_meaningful_context_body(normalized):
        return True
    return len(normalized) < THIN_CONTEXT_BODY_CHARS
