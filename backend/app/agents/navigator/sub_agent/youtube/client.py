"""YouTube 호출 IO 헬퍼 (코드가 부르는 것, LLM tool 아님).

- 채널 발굴: `search?type=channel` (쿼리당 100유닛, 1콜=실재 채널 ~25개). 환각 0.
- 영상 수집: 채널 RSS `feeds/videos.xml` (무쿼터, 표준 lib 파싱).
- Phase B: `playlists.insert` / `playlistItems.insert` (유저 OAuth 토큰) — 추후 추가.
키 없거나 오류면 graceful degrade(빈 결과).
"""

from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET

import httpx

from app.agents.navigator.sub_agent.youtube.schemas import ChannelRef, YoutubeVideo

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_RSS_URL = "https://www.youtube.com/feeds/videos.xml"

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
