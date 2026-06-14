import asyncio

from app.agents.indexer.state import IndexerState


async def node_enrich(state: IndexerState) -> IndexerState:
    """YouTube 배치 보강 + 카테고리 분류 (키워드는 해시태그 추출)"""
    try:
        from app.agents.indexer.prompt import classify_batch
        from app.agents.indexer.tool import extract_hashtags, get_videos_info_batch

        items = state["cleaned_data"]
        urls = [item.get("url", "") for item in items]
        print(f"[Enrich] YouTube API 보강 시작 ({len(items)}개)")

        video_infos = await asyncio.get_event_loop().run_in_executor(
            None, get_videos_info_batch, urls
        )

        # 해시태그 키워드 + YouTube 메타 보강
        enriched = [
            {
                **item,
                "description": info["description"],
                "duration": info["duration"],
                "is_shorts": info["is_shorts"],
                "keywords": extract_hashtags(
                    info["description"], info["tags"], item.get("title", "")
                ),
            }
            for item, info in zip(items, video_infos)
        ]

        # 카테고리만 GPT (제목 + 디스크립션 앞 200자)
        texts = [
            item["title"]
            + (" " + item["description"][:100] if item["description"] else "")
            for item in enriched
        ]

        BATCH = 30
        PARALLEL = 5
        batches = [texts[i : i + BATCH] for i in range(0, len(texts), BATCH)]

        loop = asyncio.get_event_loop()
        categories: list[str] = []

        for i in range(0, len(batches), PARALLEL):
            group = batches[i : i + PARALLEL]
            futures = [loop.run_in_executor(None, classify_batch, b) for b in group]
            group_results = await asyncio.gather(*futures)
            for r in group_results:
                categories.extend(r)
            done = min((i + PARALLEL) * BATCH, len(texts))
            print(f"[분류] {done}/{len(texts)}")

        result = [
            {**item, "category": categories[j] if j < len(categories) else "기타"}
            for j, item in enumerate(enriched)
        ]
        return {**state, "cleaned_data": result, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}
