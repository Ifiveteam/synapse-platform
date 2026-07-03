"""YouTube 호출 IO 헬퍼 (코드가 부르는 것, LLM tool 아님).

- 채널 발굴: `search?type=channel` (쿼리당 100유닛, 1콜=실재 채널 ~25개). 환각 0.
- 영상 수집: 채널 RSS `feeds/videos.xml` (무쿼터, 표준 lib 파싱).
- Phase B: `playlists.insert` / `playlistItems.insert` (유저 OAuth 토큰) — 추후 추가.
키 없거나 오류면 graceful degrade(빈 결과).
"""

from __future__ import annotations

import logging
import os
import re
import xml.etree.ElementTree as ET
from typing import Protocol, TypeVar

import httpx

from app.agents.navigator.sub_agent.youtube.constants import SHORTS_MAX_SECONDS
from app.agents.navigator.sub_agent.youtube.schemas import ChannelRef, YoutubeVideo

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
_PLAYLISTS_URL = "https://www.googleapis.com/youtube/v3/playlists"
_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
_RSS_URL = "https://www.youtube.com/feeds/videos.xml"

_DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")

_RSS_NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}
_TIMEOUT = 20.0


def _api_key() -> str | None:
    return os.getenv("YOUTUBE_API_KEY")


async def search_channels(
    *,
    query: str,
    max_results: int = 25,
    region_code: str = "KR",
    relevance_language: str = "ko",
) -> list[ChannelRef]:
    """`search?type=channel`로 쿼리에 맞는 실재 채널을 반환한다 (1콜=100유닛)."""
    key = _api_key()
    if not key or not query.strip():
        return []
    params = {
        "part": "snippet",
        "type": "channel",
        "q": query,
        "maxResults": min(max_results, 50),
        "regionCode": region_code,
        "relevanceLanguage": relevance_language,
        "key": key,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_SEARCH_URL, params=params)
        data = resp.json()
    except Exception:
        logger.exception("youtube search_channels failed: %s", query)
        return []
    if "error" in data:
        logger.warning(
            "youtube search_channels error: %s", data["error"].get("message")
        )
        return []
    out: list[ChannelRef] = []
    for item in data.get("items", []):
        cid = (item.get("id") or {}).get("channelId")
        snippet = item.get("snippet") or {}
        if cid:
            out.append(
                ChannelRef(
                    channel_id=cid,
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                )
            )
    return out


# ── 쓰기: 실제 YouTube 재생목록 (유저 OAuth 토큰) ─────────────────


async def create_youtube_playlist(
    *, access_token: str, title: str, description: str = ""
) -> str | None:
    """유저 계정에 재생목록 생성 → playlist id (playlists.insert, 50유닛)."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                _PLAYLISTS_URL,
                params={"part": "snippet,status"},
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "snippet": {
                        "title": title[:150],
                        "description": description[:4000],
                    },
                    "status": {"privacyStatus": "private"},
                },
            )
        data = resp.json()
    except Exception:
        logger.exception("youtube create_playlist failed")
        return None
    if "error" in data:
        logger.warning(
            "youtube create_playlist error: %s", data["error"].get("message")
        )
        return None
    return data.get("id")


async def add_playlist_item(
    *, access_token: str, playlist_id: str, video_id: str
) -> bool:
    """재생목록에 영상 1개 추가 (playlistItems.insert, 50유닛). 성공 여부."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                _PLAYLIST_ITEMS_URL,
                params={"part": "snippet"},
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        },
                    }
                },
            )
        data = resp.json()
    except Exception:
        logger.warning("youtube add_playlist_item failed: %s", video_id)
        return False
    if "error" in data:
        logger.warning(
            "youtube add_playlist_item error(%s): %s",
            video_id,
            data["error"].get("message"),
        )
        return False
    return True


def _parse_duration(iso: str) -> int:
    """ISO8601(PT#H#M#S) → 초. 파싱 실패 시 0."""
    m = _DURATION_RE.fullmatch(iso or "")
    if not m:
        return 0
    h, mm, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mm * 60 + s


async def fetch_video_durations(video_ids: list[str]) -> dict[str, int]:
    """video_id → 길이(초). videos.list(part=contentDetails), 50개/콜(1유닛).

    키 없거나 오류면 빈 dict(→ 호출측이 필터를 스킵하도록).
    """
    key = _api_key()
    ids = [v for v in video_ids if v]
    if not key or not ids:
        return {}
    out: dict[str, int] = {}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            for i in range(0, len(ids), 50):
                chunk = ids[i : i + 50]
                resp = await client.get(
                    _VIDEOS_URL,
                    params={
                        "part": "contentDetails",
                        "id": ",".join(chunk),
                        "key": key,
                    },
                )
                data = resp.json()
                if "error" in data:
                    logger.warning(
                        "youtube videos.list error: %s", data["error"].get("message")
                    )
                    continue
                for item in data.get("items", []):
                    vid = item.get("id")
                    dur = (item.get("contentDetails") or {}).get("duration", "")
                    if vid:
                        out[vid] = _parse_duration(dur)
    except Exception:
        logger.exception("youtube fetch_video_durations failed")
    return out


class _HasVideoId(Protocol):
    video_id: str


_T = TypeVar("_T", bound=_HasVideoId)


async def filter_out_shorts(items: list[_T]) -> list[_T]:
    """쇼츠(길이 ≤ SHORTS_MAX_SECONDS) 제외. 길이 못 얻은 건 관대하게 남긴다.

    길이 조회가 전부 실패(키 없음 등)하면 원본 그대로 반환(필터 스킵).
    """
    if not items:
        return items
    durations = await fetch_video_durations([it.video_id for it in items])
    if not durations:
        return items
    big = 10**9
    return [it for it in items if durations.get(it.video_id, big) > SHORTS_MAX_SECONDS]


async def fetch_channel_uploads(
    *, channel_id: str, limit: int = 15
) -> list[YoutubeVideo]:
    """채널 RSS에서 최근 업로드를 반환한다 (무쿼터)."""
    if not channel_id:
        return []
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_RSS_URL, params={"channel_id": channel_id})
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.text)
    except Exception:
        logger.warning("youtube RSS failed: %s", channel_id)
        return []
    videos: list[YoutubeVideo] = []
    for entry in root.findall("a:entry", _RSS_NS)[:limit]:
        vid = entry.findtext("yt:videoId", default="", namespaces=_RSS_NS)
        if not vid:
            continue
        thumb = ""
        group = entry.find("media:group", _RSS_NS)
        if group is not None:
            thumb_el = group.find("media:thumbnail", _RSS_NS)
            if thumb_el is not None:
                thumb = thumb_el.get("url", "")
        videos.append(
            YoutubeVideo(
                video_id=vid,
                title=entry.findtext("a:title", default="", namespaces=_RSS_NS),
                channel=entry.findtext(
                    "a:author/a:name", default="", namespaces=_RSS_NS
                ),
                channel_id=entry.findtext(
                    "yt:channelId", default="", namespaces=_RSS_NS
                ),
                thumbnail_url=thumb,
                published_at=entry.findtext(
                    "a:published", default="", namespaces=_RSS_NS
                ),
            )
        )
    return videos
