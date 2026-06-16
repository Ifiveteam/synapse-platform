"""YouTube 자막 추출 (youtube-transcript-api)."""

from __future__ import annotations

import re


def _extract_video_id(url: str) -> str | None:
    match = re.search(r"(?:v=|shorts/)([^&?/]+)", url)
    return match.group(1) if match else None


def fetch_transcript(url: str) -> str | None:
    """영상 URL에서 자막 텍스트 추출. 실패 시 None."""
    video_id = _extract_video_id(url)
    if not video_id:
        return None

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("[Transcript] youtube-transcript-api 미설치")
        return None

    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["ko", "en"]
        )
        text = " ".join(chunk.get("text", "") for chunk in transcript).strip()
        return text or None
    except Exception as exc:
        print(f"[Transcript] 실패 ({video_id}): {exc}")
        return None
