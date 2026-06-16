"""Archiver agent business logic — pipeline orchestration with DB persistence."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.archiver.graph import ArchiverGraph, get_archiver_graph
from app.agents.archiver.prompt import NO_CONTEXT_TITLE, NO_CONTEXT_URL
from app.core.database.session import get_db
from app.repositories.archiver_repository import ArchiverRepository
from app.schemas.chat import ChatStreamRequest

# TODO: 세션 인증 유틸 완성 시 토큰에서 동적으로 추출
DEFAULT_USER_ID = 1


class ArchiverService:
    def __init__(
        self,
        db: AsyncSession = Depends(get_db),
        archiver_graph: ArchiverGraph = Depends(get_archiver_graph),
    ) -> None:
        self.repo = ArchiverRepository(db)
        self.archiver_graph = archiver_graph

    async def generate_archive_stream(
        self,
        request: ChatStreamRequest,
    ) -> AsyncIterator[str]:
        """웹 맥락 수집 메타데이터 정산, DB 선저장, 그래프 호출, AI 답변 최종 기록을 관장한다."""
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

        full_response_chunks: list[str] = []

        async for chunk in self.archiver_graph.stream_chat(
            message=request.message,
            context_title=context_title,
            context_url=context_url,
        ):
            full_response_chunks.append(chunk)
            yield chunk

        full_ai_content = "".join(full_response_chunks)
        if full_ai_content and not full_ai_content.startswith("❌"):
            await self.repo.save_chat_log(
                session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=full_ai_content,
                url=context_url,
                title=context_title,
            )

    async def get_active_sessions(self, user_id: int) -> list[dict]:
        """유저의 최신 아카이빙 세션 리스트를 반환한다."""
        return await self.repo.get_user_sessions(user_id=user_id)

    async def get_session_history(self, session_id: str) -> list[dict]:
        """특정 세션의 대화 기록을 프론트엔드 ChatMessage UI 규격에 맞춰 정제한다."""
        raw_logs = await self.repo.get_chat_history(session_id=session_id)
        return [
            {
                "id": log.id,
                "role": log.role,
                "content": log.content,
                "created_at": log.created_at.isoformat(),
            }
            for log in raw_logs
        ]
