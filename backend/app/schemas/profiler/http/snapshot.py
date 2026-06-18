"""프로필 스냅샷 HTTP 응답."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TopCategoryItem(BaseModel):
    category_id: str
    count: int


class TopChannelItem(BaseModel):
    channel: str
    count: int


class DbProfileResponse(BaseModel):
    """DB user_profile_history 스냅샷 (점수 + 해석)."""

    user_id: str
    snapshot_id: str
    snapshot_date: datetime
    scores: dict[str, float]
    summary_text: str
    persona_label: str | None = None
    behavior_reasoning: str | None = None
    dominant_traits: list[str] | None = None
    supporting_evidence: dict | None = None
    tone_of_user: str | None = None
    top_categories: list[TopCategoryItem] = []
    top_channels: list[TopChannelItem] = []
