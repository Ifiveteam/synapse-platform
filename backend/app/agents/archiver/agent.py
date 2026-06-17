"""Archiver agent core — public facade over workflow graph."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.agents.archiver.graph import get_archiver_graph


class ArchiverAgent:
    async def stream_archive_llm(
        self,
        user_prompt: str,
        *,
        context_title: str | None = None,
        context_url: str | None = None,
    ) -> AsyncIterator[str]:
        """에이전트 진입점 — 내부 워크플로우 그래프에 스트리밍을 위임한다."""
        graph = get_archiver_graph()
        async for chunk in graph.stream_chat(
            user_prompt,
            context_title=context_title,
            context_url=context_url,
        ):
            yield chunk


_archiver_agent: ArchiverAgent | None = None


def get_archiver_agent() -> ArchiverAgent:
    global _archiver_agent
    if _archiver_agent is None:
        _archiver_agent = ArchiverAgent()
    return _archiver_agent
