"""노드: YouTube API 메타 + URL 썸네일 + 숏츠."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.request

from app.agents.indexer.state import IndexerState
from app.agents.indexer.tool import (
    _extract_video_id,
    is_shorts,
    parse_duration_iso,
    thumbnail_url_for,
)


def fetch_youtube_metadata_batch(urls: list[str]) -> list[dict]:
    """videos.list 배치 — category, duration, description, tags. quota: 1 unit / 50 IDs."""
    api_key = os.getenv("YOUTUBE_API_KEY")
    empty = {
        "description": "",
        "duration_sec": 0,
        "tags": [],
        "youtube_category_id": None,
    }

    if not api_key:
        return [dict(empty) for _ in urls]

    id_to_url: dict[str, str] = {}
    for url in urls:
        vid_id = _extract_video_id(url)
        if vid_id:
            id_to_url[vid_id] = url

    api_results: dict[str, dict] = {}
    video_ids = list(id_to_url.keys())
    total_batches = (len(video_ids) + 49) // 50

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        batch_num = i // 50 + 1
        print(f"[enrich] YouTube API 배치 {batch_num}/{total_batches} ({len(batch)}개)")
        api_url = (
            "https://www.googleapis.com/youtube/v3/videos"
            f"?part=snippet,contentDetails&id={','.join(batch)}&key={api_key}"
        )
        try:
            with urllib.request.urlopen(api_url, timeout=15) as resp:
                data = json.loads(resp.read())
                for item in data.get("items", []):
                    vid_id = item["id"]
                    snippet = item.get("snippet", {})
                    content = item.get("contentDetails", {})
                    api_results[vid_id] = {
                        "description": snippet.get("description", ""),
                        "duration_sec": parse_duration_iso(
                            content.get("duration", "PT0S")
                        ),
                        "tags": snippet.get("tags") or [],
                        "youtube_category_id": snippet.get("categoryId"),
                    }
        except Exception as e:
            print(f"[enrich] YouTube API 배치 에러 (ids {i}~{i + 50}): {e}")

    result: list[dict] = []
    for url in urls:
        vid_id = _extract_video_id(url)
        if vid_id and vid_id in api_results:
            result.append(dict(api_results[vid_id]))
        else:
            result.append(dict(empty))

    print(f"[enrich] YouTube API 응답 {len(api_results)}건 / 요청 {len(urls)}건")
    return result


async def node_enrich(state: IndexerState) -> IndexerState:
    """YouTube API 메타 + URL 썸네일 + 숏츠."""
    try:
        items = state.get("cleaned_data") or []
        if not items:
            return {**state, "cleaned_data": [], "error": None}

        urls = [item.get("url", "") for item in items]
        print(f"[enrich] 보강 시작 ({len(items)}개)")

        api_rows = await asyncio.get_event_loop().run_in_executor(
            None, fetch_youtube_metadata_batch, urls
        )

        merged: list[dict] = []
        for item, api_row in zip(items, api_rows, strict=False):
            url = item.get("url", "")
            duration = api_row.get("duration_sec")
            if duration is None:
                duration = item.get("duration_sec") or item.get("duration")
            thumb = thumbnail_url_for(url)
            merged.append(
                {
                    **item,
                    **api_row,
                    "duration_sec": duration,
                    "thumbnail_url": thumb,
                    "is_shorts": is_shorts(url, duration),
                }
            )

        shorts = sum(1 for row in merged if row.get("is_shorts"))
        print(f"[enrich] 숏츠 {shorts}건")

        return {**state, "cleaned_data": merged, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}
