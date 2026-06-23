"""Archiver agent business logic ? ??/DB ???, LangGraph? ?? ??."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.archiver.core.constants import STREAM_ERROR_PREFIX
from app.agents.archiver.core.history import append_user_turn, history_to_messages
from app.agents.archiver.engine import ArchiverEngine, get_archiver_engine
from app.agents.archiver.models import (
    NO_CONTEXT_TITLE,
    NO_CONTEXT_URL,
    ArchiverStreamEvent,
)
from app.agents.archiver.protocols.streaming import format_stream_event
from app.core.database.session import get_db
from app.repositories.archiver_repository import ArchiverRepository
from app.schemas.archiver import (
    ArchiverChatMessage,
    ArchiverSessionSummary,
    ChatStreamRequest,
)


def join_assistant_tokens(chunks: list[str]) -> str:
    """??? token ??? ??? assistant ?? ???? ???."""
    return "".join(chunks)


def should_persist_assistant_log(content: str) -> bool:
    """assistant role ??? DB? ???? ????."""
    normalized = content.strip()
    return bool(normalized) and not normalized.startswith(STREAM_ERROR_PREFIX)


def collect_token_chunks(stream_events: list[ArchiverStreamEvent]) -> list[str]:
    """ArchiverStreamEvent ???? token ??? content? ????."""
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
        """????? ?? ? LangGraph State? ????? ???? ?? ??."""
        context_title = (
            request.context.title if request.context else NO_CONTEXT_TITLE
        )
        context_url = request.context.url if request.context else NO_CONTEXT_URL
        context_body = request.context.body if request.context else None

        session_id = await self.repo.resolve_session_id(
            user_id=user_id,
            url=context_url,
        )
        prior_history = await self.repo.get_chat_history(
            session_id=session_id,
            user_id=user_id,
        )
        if not request.dom_continuation:
            await self.repo.save_chat_log(
                session_id=session_id,
                user_id=user_id,
                role="user",
                content=request.message,
                url=context_url,
                title=context_title,
            )

        conversation_messages = history_to_messages(prior_history)
        if not request.dom_continuation:
            conversation_messages = append_user_turn(
                conversation_messages,
                request.message,
            )
        initial_state = ArchiverEngine.build_initial_state(
            messages=conversation_messages,
            user_id=user_id,
            session_id=session_id,
            context_title=context_title,
            context_url=context_url,
            context_body=context_body,
            dom_continuation=request.dom_continuation,
        )

        assistant_token_chunks: list[str] = []

        async for stream_event in self.archiver_engine.stream(
            initial_state=initial_state,
            store=self.repo,
        ):
            yield format_stream_event(stream_event)

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
        """??? ?? ???? ?? ???? ????."""
        return await self.repo.get_user_sessions(user_id=user_id)

    async def get_session_history(
        self,
        session_id: str,
        *,
        user_id: uuid.UUID,
    ) -> list[ArchiverChatMessage]:
        """?? ??? ?? ??? ???? (?? ???)."""
        return await self.repo.get_chat_history(
            session_id=session_id,
            user_id=user_id,
        )
