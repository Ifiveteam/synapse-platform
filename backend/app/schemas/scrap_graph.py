"""웹 대시보드 스크랩 그래프 API 스키마."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ScrapGraphNode(BaseModel):
    """react-force-graph 노드 (좌표 없음 — FE 물리 엔진이 배치)."""

    id: uuid.UUID
    title: str | None = None
    category: str
    tags: list[str] = Field(default_factory=list)


class ScrapGraphLink(BaseModel):
    """노드 간 코사인 유사도 엣지."""

    source: uuid.UUID
    target: uuid.UUID
    similarity: float = Field(ge=0.0, le=1.0)


class ScrapGraphResponse(BaseModel):
    """GET /api/v1/scraps/graph 응답."""

    nodes: list[ScrapGraphNode]
    links: list[ScrapGraphLink]
