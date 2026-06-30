"""YouTube 자막 fetch (video_analysis.transcript).

youtube-transcript-api 1.x 인스턴스 fetch API 사용.
결과를 '정상(ok)' / '자막 없음(none, 정상)' / '차단·일시오류(blocked, 재시도 후 실패)'로
구분하고, 일시적 실패는 백오프 재시도한다. 차단 여부 가시화를 위해 로깅한다.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_VIDEO_ID_RE = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})"
)
_LANGUAGES = ["ko", "en", "en-US"]
_MAX_RETRIES = 3
_RETRY_BACKOFF = 1.0  # 초, 지수 백오프 (1 → 2 → 4)


@dataclass
class TranscriptResult:
    """자막 fetch 결과.

    status:
      - ok      : 자막 확보
      - none    : 자막 없음/비활성 (정상 — 메타데이터로 분석)
      - blocked : 재시도 후에도 실패 (차단·rate limit 의심)
    """

    text: str | None
    status: str


def extract_video_id(url: str | None) -> str | None:
    if not url:
        return None
    match = _VIDEO_ID_RE.search(url)
    return match.group(1) if match else None


def _join_segments(fetched) -> str | None:
    text = " ".join(getattr(seg, "text", "") for seg in fetched).strip()
    return text or None


def fetch_youtube_transcript(url: str | None) -> TranscriptResult:
    """자막 텍스트 fetch. 일시적 차단은 재시도, 영구 실패(자막 없음)는 즉시 none."""
    video_id = extract_video_id(url)
    if not video_id:
        return TranscriptResult(None, "none")

    from youtube_transcript_api import (
        IpBlocked,
        NoTranscriptFound,
        RequestBlocked,
        TranscriptsDisabled,
        VideoUnavailable,
        YouTubeTranscriptApi,
    )

    # 영구 실패 = 자막이 원래 없음 → 재시도 무의미 (정상 처리)
    permanent = (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable)
    # 일시 실패 = 차단·rate limit → 재시도 대상
    transient = (IpBlocked, RequestBlocked)

    api = YouTubeTranscriptApi()
    last_err: object = None
    for attempt in range(_MAX_RETRIES):
        try:
            fetched = api.fetch(video_id, languages=_LANGUAGES)
            return TranscriptResult(_join_segments(fetched), "ok")
        except permanent:
            return TranscriptResult(None, "none")
        except transient as e:
            last_err = e
        except Exception as e:  # noqa: BLE001 — 미상 오류는 일시로 보고 재시도
            last_err = e
        if attempt < _MAX_RETRIES - 1:
            time.sleep(_RETRY_BACKOFF * (2**attempt))

    logger.warning(
        "[transcript] fetch 실패(차단 의심) video_id=%s: %r", video_id, last_err
    )
    return TranscriptResult(None, "blocked")
