from __future__ import annotations

import asyncio

from app.agents.profiler.video_summary.state import (
    AnalyzedVideo,
    VideoSummaryState,
    WatchInput,
)

_CONCURRENCY = 8


async def node_summarize(state: VideoSummaryState) -> VideoSummaryState:
    """영상별 Gemini 의미분석. 동시성 제한, 1건 실패는 스킵하고 배치는 계속."""
    try:
        from app.agents.aggregator.llm.gemini import invoke_gemini_structured
        from app.agents.profiler.video_summary.prompt import (
            build_messages,
            has_min_content,
        )
        from app.agents.profiler.video_summary.schemas import VideoSemanticAnalysis

        watches = state.get("watches") or []
        sem = asyncio.Semaphore(_CONCURRENCY)

        async def _one(w: WatchInput) -> AnalyzedVideo | None:
            if not has_min_content(w):
                return None
            async with sem:
                try:
                    res = await invoke_gemini_structured(
                        build_messages(w), VideoSemanticAnalysis
                    )
                except Exception:
                    return None
            return {
                "watch_id": w["watch_id"],
                "summary_kr": res.summary_kr,
                "tones": res.tones,
                "intents": res.intents,
                "value_signals": res.value_signals,
                "embedding_text": "",
                "embedding": None,
            }

        results = await asyncio.gather(*[_one(w) for w in watches])
        analyzed = [r for r in results if r is not None]
        skipped = len(watches) - len(analyzed)
        return {
            **state,
            "analyzed": analyzed,
            "skipped_count": skipped,
            "error": None,
        }
    except Exception as e:
        return {**state, "analyzed": [], "error": str(e)}
