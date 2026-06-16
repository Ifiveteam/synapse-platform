"""Archiver agent workflow engine — 스크래핑·RAG·구글 검색 통합 스트리밍."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from google.genai import types

from app.agents.archiver.llm.client import GEMINI_MODEL, gemini_client
from app.agents.archiver.nodes import (
    is_scrapable_url,
    retrieve_rag_context_node,
    scrape_web_context_node,
)
from app.agents.archiver.prompt import (
    NO_CONTEXT_TITLE,
    NO_CONTEXT_URL,
    OFF_TAB_BODY,
    build_comprehensive_archiver_instruction,
)
from app.agents.archiver.state import ArchiverState

logger = logging.getLogger(__name__)

_STREAM_ERROR = "❌ 통합 에이전트 처리 중 결함이 발생했습니다."
_GOOGLE_SEARCH_TOOL = types.Tool(google_search=types.GoogleSearch())


class ArchiverGraph:
    """Archiver 통합 지식 스트리밍 엔진.

    활성 탭 본문 스크래핑 → RAG 검색 → Gemini + Google Search 도구로 멀티 라우팅합니다.
    """

    async def stream_chat(
        self,
        message: str,
        context_title: str | None = None,
        context_url: str | None = None,
    ) -> AsyncIterator[str]:
        """페이지 내부 질문과 외부 검색/RAG 질문을 통합 처리하는 스트리밍 파이프라인."""
        resolved_title = context_title or NO_CONTEXT_TITLE
        resolved_url = context_url or NO_CONTEXT_URL

        initial_state: ArchiverState = {
            "messages": [],
            "context_title": resolved_title,
            "context_url": resolved_url,
            "context_body": "",
        }

        if is_scrapable_url(resolved_url):
            scrape_result = await scrape_web_context_node(initial_state)
            context_body = scrape_result.get("context_body", "")
        else:
            context_body = OFF_TAB_BODY

        rag_result = await retrieve_rag_context_node(initial_state, message)
        rag_context = rag_result.get("rag_context", "")

        system_instruction = build_comprehensive_archiver_instruction(
            context_title=resolved_title,
            context_url=resolved_url,
            context_body=context_body,
            rag_context=rag_context,
        )

        try:
            stream = await gemini_client.aio.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=message,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=[_GOOGLE_SEARCH_TOOL],
                    temperature=0.3,
                ),
            )
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception:
            logger.exception("Archiver integrated streaming engine failed")
            yield _STREAM_ERROR


_archiver_graph: ArchiverGraph | None = None


def get_archiver_graph() -> ArchiverGraph:
    global _archiver_graph
    if _archiver_graph is None:
        _archiver_graph = ArchiverGraph()
    return _archiver_graph
