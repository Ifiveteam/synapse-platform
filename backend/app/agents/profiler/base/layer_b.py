from __future__ import annotations

from pydantic import BaseModel, Field


class LayerB(BaseModel):
    search_active_ratio: float = Field(ge=0, le=1)
    viewing_concentration: float = Field(ge=0, le=1)
    taste_diversity_index: float = Field(ge=0, le=100, default=0.0)
    exploration_depth: float = Field(ge=0, le=1, default=0.0)


class LayerBDelta(BaseModel):
    search_active_ratio: float = 0.0
    viewing_concentration: float = 0.0
    taste_diversity_index: float = 0.0
    exploration_depth: float = 0.0
