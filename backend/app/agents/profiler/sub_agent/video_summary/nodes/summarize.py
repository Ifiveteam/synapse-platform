from __future__ import annotations

import asyncio

from app.agents.profiler.sub_agent.video_summary.state import (
    AnalyzedVideo,
    CatalogInput,
    VideoSummaryState,
)

_CONCURRENCY = 8


def _embedding_text(a: AnalyzedVideo) -> str:
    summary = (a.get("summary_kr") or "").strip()
    tones = ", ".join(a.get("tones") or [])
    intents = ", ".join(a.get("intents") or [])
    values = ", ".join(a.get("value_signals") or [])
    text = f"{summary} / 톤: {tones} / 의도: {intents} / 가치: {values}".strip()
    return text if text.strip(" /") else (summary or "내용 없음")


async def node_summarize(state: VideoSummaryState) -> VideoSummaryState:
    """영상별 Gemini 의미분석. 동시성 제한, 1건 실패는 스킵하고 배치는 계속."""
    try:
        from app.agents.aggregator.llm.gemini import invoke_gemini_structured
        from app.agents.profiler.sub_agent.video_summary.prompts import (
            build_messages,
            has_min_content,
        )
        from app.schemas.profiler import VideoSemanticAnalysis

        catalogs = state.get("catalogs") or []
        sem = asyncio.Semaphore(_CONCURRENCY)

        async def _one(c: CatalogInput) -> AnalyzedVideo | None:
            if not has_min_content(c):
                return None
            async with sem:
                try:
                    res = await invoke_gemini_structured(
                        build_messages(c), VideoSemanticAnalysis
                    )
                except Exception:
                    return None
            return {
                "catalog_id": c["catalog_id"],
                "user_id": c["user_id"],
                "summary_kr": res.summary_kr,
                "tones": res.tones,
                "intents": res.intents,
                "value_signals": res.value_signals,
                "transcript": c.get("transcript"),
                "embedding_text": "",
                "embedding": None,
            }

        results = await asyncio.gather(*[_one(c) for c in catalogs])
        analyzed = [r for r in results if r is not None]
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
