from __future__ import annotations

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    weight: float = 0.0


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float = 1.0
    relation: str = ""
    directed: bool = False


class GraphViewData(BaseModel):
    kind: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
