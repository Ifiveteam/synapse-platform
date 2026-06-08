"""
Navigator Agent - YouTube Service
YouTube Data API v3 기반 영상 검색 + 재생목록 생성
"""

import os
import re
from typing import Optional

import httpx

from .schemas import IdealRadarChart, Playlist, PlaylistItem


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def _get_api_key() -> str:
    key = os.getenv("YOUTUBE_API_KEY", "")
    if not key:
        raise EnvironmentError("YOUTUBE_API_KEY 환경변수가 설정되지 않았습니다.")
    return key


def _parse_duration(iso_duration: str) -> int:
    """ISO 8601 duration → 초 변환 (PT1H2M3S → 3723)"""
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    match = re.match(pattern, iso_duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


async def search_videos(
    query: str,
    max_results: int = 5,
    language: str = "ko",
) -> list[dict]:
    """
    YouTube 영상 검색
    Returns: [{video_id, title, channel, duration_seconds}]
    """
    api_key = _get_api_key()

    # 1단계: search.list로 video_id 수집
    search_params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "relevanceLanguage": language,
        "key": api_key,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        search_resp = await client.get(f"{YOUTUBE_API_BASE}/search", params=search_params)
        search_resp.raise_for_status()
        search_data = search_resp.json()

    video_ids = [
        item["id"]["videoId"]
        for item in search_data.get("items", [])
    ]
    if not video_ids:
        return []

    # 2단계: videos.list로 duration 수집
    videos_params = {
        "part": "snippet,contentDetails",
        "id": ",".join(video_ids),
        "key": api_key,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        videos_resp = await client.get(f"{YOUTUBE_API_BASE}/videos", params=videos_params)
        videos_resp.raise_for_status()
        videos_data = videos_resp.json()

    results = []
    for item in videos_data.get("items", []):
        duration_iso = item["contentDetails"]["duration"]
        results.append({
            "video_id": item["id"],
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "duration_seconds": _parse_duration(duration_iso),
        })

    return results


async def build_playlist_items(
    search_queries: list[dict],  # [{query, reason, target_axis}]
    videos_per_query: int = 2,
) -> list[PlaylistItem]:
    """
    검색어 목록으로 PlaylistItem 생성
    """
    items: list[PlaylistItem] = []

    for sq in search_queries:
        try:
            videos = await search_videos(sq["query"], max_results=videos_per_query)
            for v in videos:
                items.append(PlaylistItem(
                    video_id=v["video_id"],
                    title=v["title"],
                    channel=v["channel"],
                    duration_seconds=v["duration_seconds"],
                    reason=sq.get("reason", ""),
                ))
        except Exception:
            # 검색 실패 시 해당 쿼리 skip
            continue

    return items


async def create_youtube_playlist(
    title: str,
    description: str,
    video_ids: list[str],
    access_token: str,
) -> Optional[str]:
    """
    YouTube 재생목록 생성 (OAuth 필요)
    Returns: playlist_id or None
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    api_key = _get_api_key()

    # 재생목록 생성
    create_body = {
        "snippet": {"title": title, "description": description},
        "status": {"privacyStatus": "private"},
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        create_resp = await client.post(
            f"{YOUTUBE_API_BASE}/playlists",
            params={"part": "snippet,status", "key": api_key},
            json=create_body,
            headers=headers,
        )
        if create_resp.status_code != 200:
            return None

        playlist_id = create_resp.json()["id"]

        # 영상 추가
        for video_id in video_ids:
            item_body = {
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            }
            await client.post(
                f"{YOUTUBE_API_BASE}/playlistItems",
                params={"part": "snippet", "key": api_key},
                json=item_body,
                headers=headers,
            )

    return playlist_id


async def build_playlist_from_ideal(
    user_id: str,
    ideal: IdealRadarChart,
    search_queries: list[dict],
    playlist_title: str,
    playlist_description: str,
    access_token: Optional[str] = None,
) -> Playlist:
    """
    이상향 기반 플레이리스트 전체 빌드 (검색 + 생성)
    """
    items = await build_playlist_items(search_queries, videos_per_query=2)

    playlist = Playlist(
        user_id=user_id,
        title=playlist_title,
        description=playlist_description,
        items=items,
        ideal_type=ideal.ideal_type,
    )

    # OAuth 토큰 있으면 실제 YouTube 재생목록 생성
    if access_token and items:
        video_ids = [item.video_id for item in items]
        playlist_id = await create_youtube_playlist(
            title=playlist_title,
            description=playlist_description,
            video_ids=video_ids,
            access_token=access_token,
        )
        playlist.youtube_playlist_id = playlist_id

    return playlist
