from __future__ import annotations

import asyncio

from app.agents.profiler.sub_agent.video_summary.state import (
    AnalyzedVideo,
    CatalogInput,
    VideoSummaryState,
)

_BATCH_SIZE = 10  # 영상 N개를 Gemini 한 콜로 (150콜 → ~15콜)
_CONCURRENCY = 4  # 동시 배치 수 (= 영상 40개 동시)
_MAX_ATTEMPTS = 2  # 최초 + 실패 시 1회 재시도


def _embedding_text(a: AnalyzedVideo) -> str:
    summary = (a.get("summary_kr") or "").strip()
    tones = ", ".join(a.get("tones") or [])
    intents = ", ".join(a.get("intents") or [])
    values = ", ".join(a.get("value_signals") or [])
    text = f"{summary} / 톤: {tones} / 의도: {intents} / 가치: {values}".strip()
    return text if text.strip(" /") else (summary or "내용 없음")


async def node_summarize(state: VideoSummaryState) -> VideoSummaryState:
    """영상 배치(10개) Gemini 의미분석. 배치 실패 시 1회 재시도, 부분/실패는 스킵."""
    try:
        from app.agents.profiler.llm import invoke_gemini_structured
        from app.agents.profiler.sub_agent.video_summary.prompts import (
            build_batch_messages,
            has_min_content,
        )
        from app.schemas.profiler import VideoBatchAnalysis

        catalogs = [c for c in (state.get("catalogs") or []) if has_min_content(c)]
        chunks = [
            catalogs[i : i + _BATCH_SIZE] for i in range(0, len(catalogs), _BATCH_SIZE)
        ]
        sem = asyncio.Semaphore(_CONCURRENCY)

        async def _run_chunk(chunk: list[CatalogInput]) -> list[AnalyzedVideo]:
            async with sem:
                res = None
                for _ in range(_MAX_ATTEMPTS):
                    try:
                        res = await invoke_gemini_structured(
                            build_batch_messages(chunk), VideoBatchAnalysis
                        )
                        if res and res.items:
                            break
                    except Exception:
                        res = None
            if not res or not res.items:
                return []
            out: list[AnalyzedVideo] = []
            seen: set[int] = set()
            for item in res.items:
                idx = item.index
                if idx in seen or not (0 <= idx < len(chunk)):
                    continue
                seen.add(idx)
                c = chunk[idx]
                out.append(
                    {
                        "catalog_id": c["catalog_id"],
                        "user_id": c["user_id"],
                        "summary_kr": item.summary_kr,
                        "tones": item.tones,
                        "intents": item.intents,
                        "value_signals": item.value_signals,
                        "embedding_text": "",
                        "embedding": None,
                    }
                )
            return out

        results = await asyncio.gather(*[_run_chunk(ch) for ch in chunks])
        analyzed = [a for chunk_res in results for a in chunk_res]
        for a in analyzed:
            a["embedding_text"] = _embedding_text(a)
        skipped = len(catalogs) - len(analyzed)
        return {
            **state,
            "analyzed": analyzed,
            "skipped_count": skipped,
            "error": None,
        }
    except Exception as e:
        return {**state, "analyzed": [], "error": str(e)}
