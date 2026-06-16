"""Archiver 도메인 및 통합 AI 채팅 로그 데이터베이스 레포지토리."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import AIChatLog

ARCHIVER_AGENT_TYPE = "ARCHIVER"


class ArchiverRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def resolve_session_id(self, user_id: int, url: str) -> str:
        """동일 유저·URL의 최근 아카이버 세션 ID를 반환하거나, 없으면 신규 UUID를 발급한다."""
        result = await self.db.execute(
            select(AIChatLog.session_id)
            .where(
                AIChatLog.user_id == user_id,
                AIChatLog.context_url == url,
                AIChatLog.agent_type == ARCHIVER_AGENT_TYPE,
            )
            .order_by(AIChatLog.created_at.desc())
            .limit(1)
        )
        session_id = result.scalar_one_or_none()
        if session_id:
            return session_id
        return str(uuid.uuid4())

    async def save_chat_log(
        self,
        session_id: str,
        user_id: int,
        role: str,
        content: str,
        url: str | None = None,
        title: str | None = None,
    ) -> AIChatLog:
        """통합 로그 테이블(ai_chat_logs)에 아카이버 에이전트 타입으로 대화 로그를 기록한다."""
        log_entry = AIChatLog(
            session_id=session_id,
            user_id=user_id,
            agent_type=ARCHIVER_AGENT_TYPE,
            role=role,
            content=content,
            context_url=url,
            context_title=title,
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry

    async def get_user_sessions(
        self,
        user_id: int,
        limit: int = 20,
    ) -> list[dict[str, str | datetime]]:
        """유저의 아카이버 세션 목록을 최근 활동 순으로 반환한다."""
        activity_subq = (
            select(
                AIChatLog.session_id.label("session_id"),
                func.max(AIChatLog.created_at).label("last_activity"),
            )
            .where(
                AIChatLog.user_id == user_id,
                AIChatLog.agent_type == ARCHIVER_AGENT_TYPE,
            )
            .group_by(AIChatLog.session_id)
            .order_by(func.max(AIChatLog.created_at).desc())
            .limit(limit)
            .subquery()
        )

        stmt = (
            select(
                activity_subq.c.session_id,
                AIChatLog.context_title,
                AIChatLog.context_url,
                activity_subq.c.last_activity,
            )
            .select_from(activity_subq)
            .join(
                AIChatLog,
                (AIChatLog.session_id == activity_subq.c.session_id)
                & (AIChatLog.role == "user")
                & (AIChatLog.user_id == user_id)
                & (AIChatLog.agent_type == ARCHIVER_AGENT_TYPE),
            )
            .order_by(
                activity_subq.c.last_activity.desc(),
                AIChatLog.created_at.asc(),
            )
        )
        result = await self.db.execute(stmt)

        sessions: list[dict[str, str | datetime]] = []
        seen_session_ids: set[str] = set()
        for row in result.all():
            if row.session_id in seen_session_ids:
                continue
            seen_session_ids.add(row.session_id)
            sessions.append(
                {
                    "session_id": row.session_id,
                    "context_title": row.context_title or "",
                    "context_url": row.context_url or "",
                    "last_activity": row.last_activity,
                }
            )
        return sessions

    async def get_chat_history(
        self,
        session_id: str,
        *,
        user_id: int | None = None,
    ) -> list[AIChatLog]:
        """세션 내 아카이버 대화 히스토리를 생성 시간 오름차순으로 반환한다."""
        query = (
            select(AIChatLog)
            .where(
                AIChatLog.session_id == session_id,
                AIChatLog.agent_type == ARCHIVER_AGENT_TYPE,
            )
            .order_by(AIChatLog.created_at.asc())
        )
        if user_id is not None:
            query = query.where(AIChatLog.user_id == user_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())
