"""영상 요약 서브에이전트 (Profiler).

user_watch_catalog 샘플을 제목·설명·태그·카테고리 메타데이터만으로 Gemini 의미 분석
(요약/톤/의도/가치)한 뒤 embedding_text 생성 및 임베딩하여 video_analysis에 저장한다.
"""

from app.agents.profiler.sub_agent.video_summary.graph import (
    run_video_summary,
    video_summary_graph,
)

__all__ = ["run_video_summary", "video_summary_graph"]
