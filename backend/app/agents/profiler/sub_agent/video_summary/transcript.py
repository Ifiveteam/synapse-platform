"""YouTube 자막 fetch (video_analysis.transcript)."""

from __future__ import annotations

import re

_VIDEO_ID_RE = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})"
)


def extract_video_id(url: str | None) -> str | None:
    if not url:
        return None
    match = _VIDEO_ID_RE.search(url)
    return match.group(1) if match else None


def fetch_youtube_transcript(url: str | None) -> str | None:
    video_id = extract_video_id(url)
    if not video_id:
        return None
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        segments = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["ko", "en", "en-US"]
        )
        text = " ".join(seg.get("text", "") for seg in segments).strip()
        return text or None
    except Exception:
        return None
