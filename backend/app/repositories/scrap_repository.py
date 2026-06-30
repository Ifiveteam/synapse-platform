"""Scrap 도메인 데이터베이스 레포지토리."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scrap import Scrap


class ScrapRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_scrap(
        self,
        *,
        user_id: uuid.UUID,
        source_type: str,
        url: str | None,
        title: str | None,
        summary: str,
        category: str,
        tags: list[str],
        raw_body_snapshot: str | None = None,
        session_id: str | None = None,
    ) -> Scrap:
        """Gemini 요약·분류 결과와 수집 메타를 scraps 테이블에 저장한다."""
        scrap = Scrap(
            user_id=user_id,
            source_type=source_type,
            url=url,
            title=title,
            summary=summary,
            category=category,
            tags=tags,
            raw_body_snapshot=raw_body_snapshot,
            session_id=session_id,
        )
        self.db.add(scrap)
        await self.db.commit()
        await self.db.refresh(scrap)
        return scrap

    async def get_scraps_by_user_id(
        self,
        *,
        user_id: uuid.UUID,
        limit: int = 50,
    ) -> list[Scrap]:
        """유저 스크랩 목록을 created_at 내림차순으로 반환한다 (ix_scraps_user_created)."""
        result = await self.db.execute(
            select(Scrap)
            .where(Scrap.user_id == user_id)
            .order_by(Scrap.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_scrap_by_id(
        self,
        *,
        user_id: uuid.UUID,
        scrap_id: uuid.UUID,
    ) -> Scrap | None:
        """본인 소유 스크랩 1건을 조회한다. 없으면 None."""
        result = await self.db.execute(
            select(Scrap).where(
                Scrap.id == scrap_id,
                Scrap.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_scrap(
        self,
        *,
        user_id: uuid.UUID,
        scrap_id: uuid.UUID,
    ) -> bool:
        """본인 소유 스크랩 1건을 삭제한다. 없으면 False."""
        result = await self.db.execute(
            select(Scrap).where(
                Scrap.id == scrap_id,
                Scrap.user_id == user_id,
            )
        )
        scrap = result.scalar_one_or_none()
        if scrap is None:
            return False

        await self.db.delete(scrap)
        await self.db.commit()
        return True
