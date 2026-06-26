"""노드: YouTube API 메타 + URL 썸네일 + 숏츠."""

from __future__ import annotations

import asyncio
import logging
import os

import httpx

from app.agents.indexer.state import IndexerState
from app.agents.indexer.utils import (
    _extract_video_id,
    filter_classified_catalog_items,
    is_shorts,
    parse_duration_iso,
    thumbnail_url_for,
)

logger = logging.getLogger(__name__)

_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
_API_TIMEOUT = 15.0
_MAX_RETRIES = 3
_RETRY_BACKOFF = 0.5  # 초, 지수 백오프 (0.5 → 1.0 → 2.0)
_RETRY_STATUSES = {429, 500, 502, 503, 504}  # 일시적 — 재시도 대상


async def fetch_youtube_metadata_batch(urls: list[str]) -> list[dict]:
    """videos.list 배치(병렬) — category, duration, description, tags. quota: 1 unit / 50 IDs."""
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

    video_ids = list(id_to_url.keys())
    batches = [video_ids[i : i + 50] for i in range(0, len(video_ids), 50)]

    def _parse(data: dict) -> dict[str, dict]:
        # 200 응답 — 비공개·삭제 영상은 items에 없어 자연히 제외(정당)
        out: dict[str, dict] = {}
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            content = item.get("contentDetails", {})
            out[item["id"]] = {
                "description": snippet.get("description", ""),
                "duration_sec": parse_duration_iso(content.get("duration", "PT0S")),
                "tags": snippet.get("tags") or [],
                "youtube_category_id": snippet.get("categoryId"),
            }
        return out

    async def fetch_one(batch: list[str], num: int) -> dict[str, dict]:
        logger.info(f"[enrich] YouTube API 배치 {num}/{len(batches)} ({len(batch)}개)")
        params = {
            "part": "snippet,contentDetails",
            "id": ",".join(batch),
            "key": api_key,
        }
        last_err: object = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await client.get(_VIDEOS_URL, params=params)
            except httpx.HTTPError as e:  # 네트워크/타임아웃 → 일시적, 재시도
                last_err = e
            else:
                if resp.status_code == 200:
                    return _parse(resp.json())  # 성공 (재시도 안 함)
                if resp.status_code not in _RETRY_STATUSES:
                    logger.warning(
                        f"[enrich] 배치 {num} 비재시도 오류 HTTP {resp.status_code}"
                    )
                    return {}  # 4xx(429 제외) 등 — 재시도 무의미
                last_err = f"HTTP {resp.status_code}"
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RETRY_BACKOFF * (2**attempt))
        logger.warning(f"[enrich] 배치 {num} {_MAX_RETRIES}회 실패: {last_err}")
        return {}  # 최종 실패 → empty (다음 실행 증분 백필)

    api_results: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=_API_TIMEOUT) as client:
        for partial in await asyncio.gather(
            *(fetch_one(batch, i + 1) for i, batch in enumerate(batches))
        ):
            api_results.update(partial)

    result: list[dict] = []
    for url in urls:
        vid_id = _extract_video_id(url)
        if vid_id and vid_id in api_results:
            result.append(dict(api_results[vid_id]))
        else:
            result.append(dict(empty))

    logger.info(f"[enrich] YouTube API 응답 {len(api_results)}건 / 요청 {len(urls)}건")
    return result


async def node_enrich(state: IndexerState) -> IndexerState:
    """YouTube API 메타 + URL 썸네일 + 숏츠."""
    try:
        items = state.get("cleaned_data") or []
        if not items:
            return {**state, "cleaned_data": [], "error": None}

        urls = [item.get("url", "") for item in items]
        logger.info(f"[enrich] 보강 시작 ({len(items)}개)")

        api_rows = await fetch_youtube_metadata_batch(urls)

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

        merged, skipped = filter_classified_catalog_items(merged)
        if skipped:
            logger.info(f"[enrich] 미분류 {skipped}건 제외 (임베딩·저장 대상 아님)")
        shorts = sum(1 for row in merged if row.get("is_shorts"))
        logger.info(f"[enrich] 숏츠 {shorts}건 · catalog 대상 {len(merged)}건")

        return {**state, "cleaned_data": merged, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}
