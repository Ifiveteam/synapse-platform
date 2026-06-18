"""Archiver agent business logic — 세션/DB 진입점, LangGraph에 실행 일임."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.archiver.engine import ArchiverEngine, get_archiver_engine
from app.agents.archiver.types import NO_CONTEXT_TITLE, NO_CONTEXT_URL
from app.core.database.session import get_db
from app.repositories.archiver_repository import ArchiverRepository
from app.schemas.chat import (
    ArchiverChatMessage,
    ArchiverSessionSummary,
    ChatStreamRequest,
)

# TODO: 세션 인증 유틸 완성 시 토큰에서 동적으로 추출
DEFAULT_USER_ID = 1


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
    ) -> AsyncIterator[str]:
        """세션·로그 적재 후 LangGraph State를 초기화하여 그래프에 완전 일임."""
        user_id = DEFAULT_USER_ID

        context_title = (
            request.context.title if request.context else NO_CONTEXT_TITLE
        )
        context_url = request.context.url if request.context else NO_CONTEXT_URL

        session_id = await self.repo.resolve_session_id(
            user_id=user_id,
            url=context_url,
        )
        await self.repo.save_chat_log(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=request.message,
            url=context_url,
            title=context_title,
        )

        initial_state = ArchiverEngine.build_initial_state(
            message=request.message,
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
            # SSE: status·token 모두 클라이언트로 전달
            yield stream_event.content

            # DB: token(답변 본문)만 누적 — status UI 안내 문구는 완전 격리
            if stream_event.event == "token":
                assistant_token_chunks.append(stream_event.content)

        full_ai_content = "".join(assistant_token_chunks)
        if full_ai_content and not full_ai_content.startswith("❌"):
            await self.repo.save_chat_log(
                session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=full_ai_content,
                url=context_url,
                title=context_title,
            )

    async def get_active_sessions(self, user_id: int) -> list[ArchiverSessionSummary]:
        """유저의 최신 아카이빙 세션 리스트를 반환한다."""
        return await self.repo.get_user_sessions(user_id=user_id)

    async def get_session_history(self, session_id: str) -> list[ArchiverChatMessage]:
        """특정 세션의 대화 기록을 반환한다."""
        return await self.repo.get_chat_history(session_id=session_id)
