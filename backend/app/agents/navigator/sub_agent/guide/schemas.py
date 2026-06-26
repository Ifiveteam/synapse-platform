"""가이드 서브에이전트 전용 모델 (guide 안에서만 사용).

서브 밖으로 나가는 결과 모델(Guide·GuideStep)은 root schemas.py에 둔다.
"""

from __future__ import annotations

from pydantic import BaseModel

# ── store(catalog RAG Port) 반환 ───────────────────────────────


class CatalogHit(BaseModel):
    """축별 RAG로 찾은 실제 시청 영상 근거."""

    title: str
    channel: str
    category_id: str | None = None
    similarity: float = 0.0
