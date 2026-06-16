import asyncio

from app.agents.indexer.sampling import select_samples
from app.agents.indexer.state import IndexerState


async def node_light_enrich(state: IndexerState) -> IndexerState:
    """YouTube API로 duration·숏츠·description·썸네일 URL 보강."""
    try:
        from app.agents.indexer.tool import extract_hashtags, get_videos_info_batch

        items = state["cleaned_data"]
        urls = [item.get("url", "") for item in items]
        print(f"[Enrich] YouTube API 보강 시작 ({len(items)}개)")

        video_infos = await asyncio.get_event_loop().run_in_executor(
            None, get_videos_info_batch, urls
        )

        enriched = [
            {
                **item,
                "description": info["description"],
                "duration": info["duration"],
                "is_shorts": info["is_shorts"],
                "thumbnail_url": info.get("thumbnail_url"),
                "keywords": extract_hashtags(
                    info["description"], info["tags"], item.get("title", "")
                ),
            }
            for item, info in zip(items, video_infos, strict=False)
        ]
        return {**state, "cleaned_data": enriched, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}


async def node_classify(state: IndexerState) -> IndexerState:
    """2개월 전체 데이터 대상 GPT 카테고리 분류."""
    try:
        from app.agents.indexer.prompt import (
            DEFAULT_CATEGORY,
            classify_batch,
            normalize_category,
        )

        items = state["cleaned_data"]
        texts = [
            item["title"]
            + (" " + item["description"][:100] if item.get("description") else "")
            for item in items
        ]

        batch_size = 30
        parallel = 5
        batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]

        loop = asyncio.get_event_loop()
        categories: list[str] = []

        for i in range(0, len(batches), parallel):
            group = batches[i : i + parallel]
            futures = [loop.run_in_executor(None, classify_batch, b) for b in group]
            group_results = await asyncio.gather(*futures)
            for result in group_results:
                categories.extend(result)
            done = min((i + parallel) * batch_size, len(texts))
            print(f"[분류] {done}/{len(texts)}")

        classified = [
            {
                **item,
                "category": normalize_category(
                    categories[j] if j < len(categories) else DEFAULT_CATEGORY
                ),
            }
            for j, item in enumerate(items)
        ]
        print(
            f"[분류] 완료 {len(classified)}건 "
            f"(카테고리 {len({c['category'] for c in classified})}종)"
        )
        return {**state, "cleaned_data": classified, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}


def node_sample(state: IndexerState) -> IndexerState:
    """카테고리 × 숏츠/롱폼별 최신 5개 샘플 선정."""
    sampled = select_samples(state["cleaned_data"], per_group=5)
    print(f"[Sample] {len(state['cleaned_data'])}건 → 샘플 {len(sampled)}건")
    return {
        **state,
        "sampled_data": sampled,
        "sample_count": len(sampled),
        "error": None,
    }


async def node_heavy_enrich(state: IndexerState) -> IndexerState:
    """샘플 영상만 자막·썸네일 URL 보강."""
    try:
        from app.agents.indexer.tool import thumbnail_url_for
        from app.agents.indexer.transcript import fetch_transcript

        samples = state.get("sampled_data") or []
        if not samples:
            return {**state, "sampled_data": [], "error": None}

        print(f"[HeavyEnrich] 샘플 {len(samples)}건 자막·썸네일 수집")
        loop = asyncio.get_event_loop()
        enriched: list[dict] = []

        for item in samples:
            url = item.get("url", "")
            thumb = item.get("thumbnail_url") or thumbnail_url_for(url)
            transcript = await loop.run_in_executor(None, fetch_transcript, url)
            enriched.append({**item, "thumbnail_url": thumb, "transcript": transcript})

        return {**state, "sampled_data": enriched, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}
