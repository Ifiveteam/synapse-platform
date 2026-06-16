from __future__ import annotations

from app.agents.profiler.video_summary.state import VideoSummaryState


def node_embed(state: VideoSummaryState) -> VideoSummaryState:
    """embedding_text를 배치 임베딩해 각 분석 결과에 채운다."""
    try:
        from app.agents.profiler.video_summary.embedding import embed_texts

        analyzed = state.get("analyzed") or []
        if not analyzed:
            return {**state, "error": None}

        texts = [a["embedding_text"] for a in analyzed]
        vectors = embed_texts(texts)

        for a, vec in zip(analyzed, vectors):
            a["embedding"] = vec
        return {**state, "analyzed": analyzed, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}
