from __future__ import annotations

from app.agents.profiler.video_summary.state import AnalyzedVideo, VideoSummaryState


def _embedding_text(a: AnalyzedVideo) -> str:
    summary = (a.get("summary_kr") or "").strip()
    tones = ", ".join(a.get("tones") or [])
    intents = ", ".join(a.get("intents") or [])
    values = ", ".join(a.get("value_signals") or [])
    text = f"{summary} / 톤: {tones} / 의도: {intents} / 가치: {values}".strip()
    # embedding_text는 NOT NULL — 비면 폴백
    return text if text.strip(" /") else (summary or "분석 없음")


def node_build_embedding_text(state: VideoSummaryState) -> VideoSummaryState:
    """분석 결과로 임베딩용 정리 문장을 만든다."""
    analyzed = state.get("analyzed") or []
    for a in analyzed:
        a["embedding_text"] = _embedding_text(a)
    return {**state, "analyzed": analyzed}
