"""Navigator 레포지토리 — user_ideal_persona 영속 + 통합 채팅 로그(NAVIGATOR)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.navigator.constants import (
    BEHAVIOR_AXES,
    DESCRIPTION_SEP,
    NAVIGATOR_AGENT_TYPE,
)
from app.agents.navigator.sub_agent.guide.store import CatalogHit
from app.models.chat import AIChatLog
from app.models.navigator_proposal_cache import NavigatorProposalCache
from app.models.user_ideal_persona import UserIdealPersona
from app.models.user_watch_catalog import UserWatchCatalog
from app.schemas.navigator import NavigatorChatMessage


def encode_description(ideal_type: str, reasoning: str) -> str:
    return f"{ideal_type}{DESCRIPTION_SEP}{reasoning}".strip()


def decode_description(description: str | None) -> tuple[str, str]:
    """description → (ideal_type, reasoning). 형식이 다르면 CUSTOM으로 폴백."""
    if not description:
        return "CUSTOM", ""
    parts = description.split(DESCRIPTION_SEP, 1)
    ideal_type = parts[0].strip() or "CUSTOM"
    reasoning = parts[1].strip() if len(parts) > 1 else ""
    return ideal_type, reasoning


class NavigatorRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── user_ideal_persona (유저당 여러 개 보관 + 1개 적용) ──────────
    async def create_ideal(
        self,
        *,
        user_id: uuid.UUID,
        scores8: dict[str, float],
        ideal_type: str,
        reasoning: str,
        persona_label: str = "",
        values_temperament: dict[str, float] | None = None,
        source_profile_history_id: uuid.UUID | None = None,
    ) -> UserIdealPersona:
        """이상향을 새 행으로 생성한다 (적용 여부는 별도 apply)."""
        persona = UserIdealPersona(
            user_id=user_id,
            persona_label=persona_label or None,
            values_temperament=values_temperament or None,
            description=encode_description(ideal_type, reasoning),
            source_profile_history_id=source_profile_history_id,
            is_active=False,
        )
        for axis in BEHAVIOR_AXES:
            setattr(persona, axis, float(scores8.get(axis, 0.0)))
        self.db.add(persona)
        await self.db.commit()
        await self.db.refresh(persona)
        return persona

    async def list_ideals(self, *, user_id: uuid.UUID) -> list[UserIdealPersona]:
        result = await self.db.execute(
            select(UserIdealPersona)
            .where(UserIdealPersona.user_id == user_id)
            .order_by(UserIdealPersona.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_ideal(
        self, *, user_id: uuid.UUID, ideal_id: uuid.UUID
    ) -> UserIdealPersona | None:
        result = await self.db.execute(
            select(UserIdealPersona).where(
                UserIdealPersona.id == ideal_id,
                UserIdealPersona.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_ideal(self, *, user_id: uuid.UUID) -> UserIdealPersona | None:
        result = await self.db.execute(
            select(UserIdealPersona)
            .where(
                UserIdealPersona.user_id == user_id,
                UserIdealPersona.is_active.is_(True),
            )
            .order_by(UserIdealPersona.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def set_active(
        self, *, user_id: uuid.UUID, ideal_id: uuid.UUID
    ) -> UserIdealPersona | None:
        """대상을 적용 중으로, 나머지는 해제 (유저당 1개만 active)."""
        target = await self.get_ideal(user_id=user_id, ideal_id=ideal_id)
        if target is None:
            return None
        await self.db.execute(
            update(UserIdealPersona)
            .where(
                UserIdealPersona.user_id == user_id,
                UserIdealPersona.is_active.is_(True),
            )
            .values(is_active=False)
        )
        target.is_active = True
        await self.db.commit()
        await self.db.refresh(target)
        return target

    # ── 제안 3안 캐시 (user + 분석 스냅샷) ──────────────────────────
    async def get_proposal_cache(
        self, *, user_id: uuid.UUID, snapshot_id: uuid.UUID
    ) -> NavigatorProposalCache | None:
        result = await self.db.execute(
            select(NavigatorProposalCache).where(
                NavigatorProposalCache.user_id == user_id,
                NavigatorProposalCache.source_profile_history_id == snapshot_id,
            )
        )
        return result.scalar_one_or_none()

    async def save_proposal_cache(
        self,
        *,
        user_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        proposals_json: list,
        catalog_count: int,
    ) -> None:
        """제안 3안을 (user, snapshot)에 upsert (refresh 시 덮어씀)."""
        stmt = pg_insert(NavigatorProposalCache).values(
            user_id=user_id,
            source_profile_history_id=snapshot_id,
            proposals_json=proposals_json,
            generated_at=datetime.now(UTC),
            catalog_count=catalog_count,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_npc_user_snapshot",
            set_={
                "proposals_json": stmt.excluded.proposals_json,
                "generated_at": stmt.excluded.generated_at,
                "catalog_count": stmt.excluded.catalog_count,
            },
        )
        await self.db.execute(stmt)
        await self.db.commit()

    # ── 가이드 캐시 (persona에 고정) ────────────────────────────────
    async def count_catalog(self, *, user_id: uuid.UUID) -> int:
        """유저 시청기록(catalog) 총 개수 — 가이드 신선도 판단용."""
        result = await self.db.execute(
            select(func.count())
            .select_from(UserWatchCatalog)
            .where(UserWatchCatalog.user_id == user_id)
        )
        return int(result.scalar_one() or 0)

    async def save_guide(
        self,
        *,
        user_id: uuid.UUID,
        ideal_id: uuid.UUID,
        guide_json: dict,
        catalog_count: int,
    ) -> UserIdealPersona | None:
        """생성된 가이드를 해당 이상향 행에 캐시한다."""
        target = await self.get_ideal(user_id=user_id, ideal_id=ideal_id)
        if target is None:
            return None
        target.guide_json = guide_json
        target.guide_generated_at = datetime.now(UTC)
        target.guide_catalog_count = catalog_count
        await self.db.commit()
        await self.db.refresh(target)
        return target

    # ── 채팅 로그 (ai_chat_logs, agent_type=NAVIGATOR) ──────────────
    async def resolve_session_id(self, *, user_id: uuid.UUID) -> str:
        """동일 유저의 최근 네비게이터 세션 ID, 없으면 신규 UUID."""
        result = await self.db.execute(
            select(AIChatLog.session_id)
            .where(
                AIChatLog.user_id == user_id,
                AIChatLog.agent_type == NAVIGATOR_AGENT_TYPE,
            )
            .order_by(AIChatLog.created_at.desc())
            .limit(1)
        )
        session_id = result.scalar_one_or_none()
        return session_id or str(uuid.uuid4())

    async def get_chat_history(
        self,
        *,
        session_id: str,
        user_id: uuid.UUID | None = None,
    ) -> list[NavigatorChatMessage]:
        query = (
            select(AIChatLog)
            .where(
                AIChatLog.session_id == session_id,
                AIChatLog.agent_type == NAVIGATOR_AGENT_TYPE,
            )
            .order_by(AIChatLog.created_at.asc())
        )
        if user_id is not None:
            query = query.where(AIChatLog.user_id == user_id)

        result = await self.db.execute(query)
        return [
            NavigatorChatMessage(
                id=log.id,
                role=log.role,
                content=log.content,
                created_at=log.created_at,
            )
            for log in result.scalars().all()
        ]

    async def save_chat_log(
        self,
        *,
        session_id: str,
        user_id: uuid.UUID,
        role: str,
        content: str,
    ) -> AIChatLog:
        """네비게이터 대화 로그를 기록한다 (RAG 미사용 → embedding 없음)."""
        log_entry = AIChatLog(
            session_id=session_id,
            user_id=user_id,
            agent_type=NAVIGATOR_AGENT_TYPE,
            role=role,
            content=content,
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry

    # ── 가이드 RAG: catalog 의미 검색 (CatalogStore 구현) ────────────
    async def search_by_axis(
        self,
        user_id: uuid.UUID,
        query_embedding: list[float],
        limit: int,
    ) -> list[CatalogHit]:
        """축 쿼리 임베딩과 cosine 가까운 실제 시청 영상을 반환한다."""
        distance = UserWatchCatalog.embedding.cosine_distance(query_embedding)
        stmt = (
            select(
                UserWatchCatalog.title,
                UserWatchCatalog.channel,
                UserWatchCatalog.youtube_category_id,
                distance.label("dist"),
            )
            .where(
                UserWatchCatalog.user_id == user_id,
                UserWatchCatalog.embedding.isnot(None),
            )
            .order_by(distance)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [
            CatalogHit(
                title=row.title or "",
                channel=row.channel or "",
                category_id=row.youtube_category_id,
                similarity=round(1.0 - float(row.dist), 4),
            )
            for row in result.all()
        ]
