"""LangChain tools for the Profiler investigation agent."""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool

from app.agents.profiler.base import IndexedRecord
from app.agents.profiler.subagent.scoring import (
    get_channel_breakdown,
    get_sample_records,
    get_search_queries,
    get_tag_distribution,
)

INVESTIGATION_TOOL_NAMES: tuple[str, ...] = (
    "get_channel_breakdown",
    "get_search_queries",
    "get_tag_distribution",
    "get_sample_records",
)


def build_investigation_tools(records: list[IndexedRecord]) -> list[StructuredTool]:
    """Bind investigation tools to the current user's indexed records."""

    def channel_breakdown() -> str:
        """채널별 시청 시간(초) 집계를 반환합니다."""
        return json.dumps(get_channel_breakdown(records), ensure_ascii=False)

    def search_queries() -> str:
        """검색 기록의 검색어 목록을 반환합니다."""
        return json.dumps(get_search_queries(records), ensure_ascii=False)

    def tag_distribution() -> str:
        """콘텐츠 태그 빈도 분포를 반환합니다."""
        return json.dumps(get_tag_distribution(records), ensure_ascii=False)

    def sample_records() -> str:
        """대표 시청·검색 레코드 샘플을 반환합니다."""
        samples = get_sample_records(records)
        payload = [
            {
                "source_type": r.source_type,
                "title": r.title,
                "query": r.query,
                "channel": r.channel,
                "tags": r.tags,
                "duration_sec": r.duration_sec,
            }
            for r in samples
        ]
        return json.dumps(payload, ensure_ascii=False)

    return [
        StructuredTool.from_function(
            func=channel_breakdown,
            name="get_channel_breakdown",
            description="시청 기록을 채널별 시청 시간(초)으로 집계합니다.",
        ),
        StructuredTool.from_function(
            func=search_queries,
            name="get_search_queries",
            description="사용자의 검색어 목록을 반환합니다.",
        ),
        StructuredTool.from_function(
            func=tag_distribution,
            name="get_tag_distribution",
            description="Indexer가 부여한 taxonomy 태그의 빈도 분포를 반환합니다.",
        ),
        StructuredTool.from_function(
            func=sample_records,
            name="get_sample_records",
            description="분석에 참고할 대표 시청·검색 레코드 샘플을 반환합니다.",
        ),
    ]
