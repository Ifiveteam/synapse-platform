"""Archiver agent business logic — 세션/DB 진입점, LangGraph에 실행 일임."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.archiver.constants import STREAM_ERROR_PREFIX
from app.agents.archiver.engine import ArchiverEngine, get_archiver_engine
from app.agents.archiver.history import append_user_turn, history_to_messages
from app.agents.archiver.streaming import format_stream_event
from app.agents.archiver.types import (
    NO_CONTEXT_TITLE,
    NO_CONTEXT_URL,
    ArchiverStreamEvent,
)
from app.core.database.session import get_db
from app.repositories.archiver_repository import ArchiverRepository
from app.schemas.archiver import (
    ArchiverChatMessage,
    ArchiverSessionSummary,
    ChatStreamRequest,
)


def join_assistant_tokens(chunks: list[str]) -> str:
    """스트림 token 이벤트 청크를 assistant 로그 본문으로 합친다."""
    return "".join(chunks)


def should_persist_assistant_log(content: str) -> bool:
    """assistant role 로그를 DB에 저장할지 판단한다.

    - 빈 본문은 저장하지 않는다.
    - STREAM_ERROR_PREFIX(❌)로 시작하는 엔진 오류 토큰은 SSE로만 전달하고 DB에는 남기지 않는다.
    """
    normalized = content.strip()
    return bool(normalized) and not normalized.startswith(STREAM_ERROR_PREFIX)


def collect_token_chunks(stream_events: list[ArchiverStreamEvent]) -> list[str]:
    """ArchiverStreamEvent 목록에서 token 이벤트 content만 추출한다."""
    return [event.content for event in stream_events if event.event == "token"]


class ArchiverService:
    def __init__(
        self,
        db: AsyncSession = Depends(get_db),
        archiver_engine: ArchiverEngine = Depends(get_archiver_engine),
    ) -> None:
        self.repo = ArchiverRepository(db)
        self.archiver_engine = archiver_engine

    async def generate_archive_stream(
        self,
        request: ChatStreamRequest,
        *,
        user_id: uuid.UUID,
    ) -> AsyncIterator[str]:
        """세션·로그 적재 후 LangGraph State를 초기화하여 그래프에 완전 일임."""
        context_title = (
            request.context.title if request.context else NO_CONTEXT_TITLE
        )
        context_url = request.context.url if request.context else NO_CONTEXT_URL

        session_id = await self.repo.resolve_session_id(
            user_id=user_id,
            url=context_url,
        )
        prior_history = await self.repo.get_chat_history(
            session_id=session_id,
            user_id=user_id,
        )
        await self.repo.save_chat_log(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=request.message,
            url=context_url,
            title=context_title,
        )

        conversation_messages = append_user_turn(
            history_to_messages(prior_history),
            request.message,
        )
        initial_state = ArchiverEngine.build_initial_state(
            messages=conversation_messages,
            user_id=user_id,
            session_id=session_id,
            context_title=context_title,
            context_url=context_url,
        )

        assistant_token_chunks: list[str] = []

        async for stream_event in self.archiver_engine.stream(
            initial_state=initial_state,
            store=self.repo,
        ):
            # SSE: event/data JSON envelope (status·token)
            yield format_stream_event(stream_event)

            # DB: token(답변 본문)만 누적 — status UI 안내 문구는 완전 격리
            if stream_event.event == "token":
                assistant_token_chunks.append(stream_event.content)

        full_ai_content = join_assistant_tokens(assistant_token_chunks)
        if should_persist_assistant_log(full_ai_content):
            await self.repo.save_chat_log(
                session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=full_ai_content,
                url=context_url,
                title=context_title,
            )

    async def get_active_sessions(
        self,
        *,
        user_id: uuid.UUID,
    ) -> list[ArchiverSessionSummary]:
        """유저의 최신 아카이빙 세션 리스트를 반환한다."""
        return await self.repo.get_user_sessions(user_id=user_id)

    async def get_session_history(
        self,
        session_id: str,
        *,
        user_id: uuid.UUID,
    ) -> list[ArchiverChatMessage]:
        """특정 세션의 대화 기록을 반환한다 (본인 세션만)."""
        return await self.repo.get_chat_history(
            session_id=session_id,
            user_id=user_id,
        )
