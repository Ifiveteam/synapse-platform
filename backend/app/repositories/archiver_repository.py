"""Archiver 도메인 및 통합 AI 채팅 로그 데이터베이스 레포지토리."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.archiver.constants import ARCHIVER_AGENT_TYPE, RAG_SEARCH_LIMIT
from app.agents.archiver.store import PastKnowledgeHit
from app.models.chat import AIChatLog
from app.schemas.chat import ArchiverChatMessage, ArchiverSessionSummary

_MAX_RAG_KEYWORDS = 5
_MIN_KEYWORD_LEN = 2
_RAG_CONTENT_PREVIEW_CHARS = 400


def _extract_search_keywords(query_text: str) -> list[str]:
    """질문에서 검색용 키워드를 추출한다. (한글·영문 토큰 지원)"""
    tokens = re.findall(r"[\w가-힣]+", query_text)
    seen: set[str] = set()
    keywords: list[str] = []
    for token in tokens:
        normalized = token.strip().lower()
        if len(normalized) < _MIN_KEYWORD_LEN or normalized in seen:
            continue
        seen.add(normalized)
        keywords.append(normalized)
        if len(keywords) >= _MAX_RAG_KEYWORDS:
            break
    return keywords


def _truncate_content(content: str, limit: int = _RAG_CONTENT_PREVIEW_CHARS) -> str:
    text = content.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


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
    ) -> list[ArchiverSessionSummary]:
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

        sessions: list[ArchiverSessionSummary] = []
        seen_session_ids: set[str] = set()
        for row in result.all():
            if row.session_id in seen_session_ids:
                continue
            seen_session_ids.add(row.session_id)
            sessions.append(
                ArchiverSessionSummary(
                    session_id=row.session_id,
                    context_title=row.context_title or "",
                    context_url=row.context_url or "",
                    last_activity=row.last_activity,
                )
            )
        return sessions

    async def get_chat_history(
        self,
        session_id: str,
        *,
        user_id: int | None = None,
    ) -> list[ArchiverChatMessage]:
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
        return [
            ArchiverChatMessage(
                id=log.id,
                role=log.role,
                content=log.content,
                created_at=log.created_at,
            )
            for log in result.scalars().all()
        ]

    async def search_past_knowledge(
        self,
        user_id: int,
        query_text: str,
        limit: int = RAG_SEARCH_LIMIT,
        *,
        exclude_query_text: str | None = None,
    ) -> list[PastKnowledgeHit]:
        """질문 키워드와 겹치는 과거 아카이버 대화·스크랩 맥락을 검색한다."""
        keywords = _extract_search_keywords(query_text)
        if not keywords:
            return []

        search_conditions = []
        for keyword in keywords:
            pattern = f"%{keyword}%"
            search_conditions.append(AIChatLog.content.ilike(pattern))
            search_conditions.append(AIChatLog.context_title.ilike(pattern))

        filters = [
            AIChatLog.user_id == user_id,
            AIChatLog.agent_type == ARCHIVER_AGENT_TYPE,
            or_(*search_conditions),
        ]
        if exclude_query_text:
            filters.append(
                ~(
                    (AIChatLog.content == exclude_query_text)
                    & (AIChatLog.role == "user")
                )
            )

        stmt = (
            select(AIChatLog)
            .where(*filters)
            .order_by(AIChatLog.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return [
            PastKnowledgeHit(
                role=log.role,
                content=_truncate_content(log.content),
                context_title=log.context_title or "이전 웹페이지",
                created_at=log.created_at.strftime("%Y-%m-%d"),
            )
            for log in logs
        ]
