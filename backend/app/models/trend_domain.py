"""어그리게이터(4 에이전트) 6대 트렌드 도메인 — 코드·DB 공통 고정 Enum."""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


class TrendDomain(StrEnum):
    """거시 트렌드 분류 도메인 (6종 고정).

    JSONB 집계 필드(예: top_domains.*.main_category) 및 배치 매핑 규칙에서
    반드시 이 값만 사용한다.
    """

    TECH_BUSINESS = "Tech/Business"
    CONTENT_MEDIA = "Content/Media"
    LIFESTYLE_WELLNESS = "Lifestyle/Wellness"
    SOCIAL_CURRENT_AFFAIRS = "Social/Current Affairs"
    KNOWLEDGE_EDUCATION = "Knowledge/Education"
    ECONOMY_TECHFIN = "Economy/TechFin"


TREND_DOMAIN_VALUES: tuple[str, ...] = tuple(domain.value for domain in TrendDomain)

trend_domain_pg_enum = SAEnum(
    TrendDomain,
    name="trend_domain",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
    native_enum=True,
    create_constraint=True,
)
