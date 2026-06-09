from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

TASTE_DIVERSITY_AXES: tuple[str, ...] = (
    "intellectual_curiosity",
    "social_awareness",
    "practical_orientation",
    "emotional_comfort",
)


class SynapseAxisKey(StrEnum):
    INTELLECTUAL_CURIOSITY = "intellectual_curiosity"
    PRACTICAL_ORIENTATION = "practical_orientation"
    EMOTIONAL_COMFORT = "emotional_comfort"
    SOCIAL_AWARENESS = "social_awareness"
    CREATIVE_EXPRESSION = "creative_expression"
    ENTERTAINMENT_RELEASE = "entertainment_release"
    SELF_IMPROVEMENT = "self_improvement"
    DEPTH_IMMERSION = "depth_immersion"


SYNAPSE_AXIS_KEYS: tuple[str, ...] = tuple(key.value for key in SynapseAxisKey)


class Synapse8Axes(BaseModel):
    intellectual_curiosity: int = Field(ge=0, le=100)
    practical_orientation: int = Field(ge=0, le=100)
    emotional_comfort: int = Field(ge=0, le=100)
    social_awareness: int = Field(ge=0, le=100)
    creative_expression: int = Field(ge=0, le=100)
    entertainment_release: int = Field(ge=0, le=100)
    self_improvement: int = Field(ge=0, le=100)
    depth_immersion: int = Field(ge=0, le=100)


class AxesDelta(BaseModel):
    intellectual_curiosity: float = 0.0
    practical_orientation: float = 0.0
    emotional_comfort: float = 0.0
    social_awareness: float = 0.0
    creative_expression: float = 0.0
    entertainment_release: float = 0.0
    self_improvement: float = 0.0
    depth_immersion: float = 0.0
