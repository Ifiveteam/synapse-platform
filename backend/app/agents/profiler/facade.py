"""Profiler 에이전트 파사드 — 프로파일 생성·스냅샷 비교·영상 요약을 한 진입점으로 묶는다.

DB·HTTP는 모른다. service·api는 이 파사드만 호출한다.
그래프는 각 모듈 싱글톤이라 파사드는 위임만 담당한다.
(향후 실시간 분석 등 서브에이전트가 추가되면 여기에 메서드로 노출한다.)

※ run_* 진입 함수는 메서드 내부에서 lazy import 한다.
  일부 sub_agent 모듈이 services.profiler.scores를 참조해, top-level import 시
  service↔agent 순환이 생기기 때문(기존 api 라우터도 같은 이유로 lazy import).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.profiler.sub_agent.compare.state import CompareState
    from app.agents.profiler.sub_agent.video_summary.state import VideoSummaryState


class ProfilerAgent:
    """Profiler 능력(프로파일·비교·영상요약)을 묶어 노출하는 파사드."""

    async def run_profile(
        self, user_id: str, email: str, *, analysis_limit: int | None = None
    ) -> dict:
        """catalog → video_summary → 행동 프로파일 생성·DB 저장."""
        from app.agents.profiler.graph import run_profiler_async

        return await run_profiler_async(user_id, email, analysis_limit=analysis_limit)

    async def compare(
        self, user_id: str, from_snapshot_id: str, to_snapshot_id: str
    ) -> CompareState:
        """두 프로필 스냅샷 비교 (결정론적 diff + LLM 변화 요약)."""
        from app.agents.profiler.sub_agent.compare import run_compare

        return await run_compare(user_id, from_snapshot_id, to_snapshot_id)

    async def summarize_videos(
        self, user_id: uuid.UUID, limit: int | None = None
    ) -> VideoSummaryState:
        """시청 catalog 샘플에 자막·의미분석을 붙여 video_analysis에 적재."""
        from app.agents.profiler.sub_agent import run_video_summary

        return await run_video_summary(user_id, limit)


_profiler_agent: ProfilerAgent | None = None


def get_profiler_agent() -> ProfilerAgent:
    """FastAPI Depends/싱글톤용 ProfilerAgent."""
    global _profiler_agent
    if _profiler_agent is None:
        _profiler_agent = ProfilerAgent()
    return _profiler_agent
