"""Archiver agent business logic — 세션/DB I/O, LangGraph 실행, 스크랩 파이프라인."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
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
from app.agents.archiver.scrap import (
    classify_scrap_content,
    normalize_custom_category,
    truncate_raw_body,
)
from app.core.database.session import get_db
from app.repositories.archiver_repository import ArchiverRepository
from app.repositories.scrap_repository import ScrapRepository
from app.schemas.archiver import (
    ArchiverChatMessage,
    ArchiverSessionSummary,
    ChatStreamRequest,
)
from app.schemas.scrap import ScrapCreateRequest, ScrapDetailResponse, ScrapResponse
from app.services.scrap_embedding_service import ScrapEmbeddingService


def join_assistant_tokens(chunks: list[str]) -> str:
    """스트림 token 청크 목록을 assistant 최종 본문 문자열로 합친다."""
    return "".join(chunks)


def should_persist_assistant_log(content: str) -> bool:
    """assistant role 로그를 DB에 저장할지 판단한다."""
    normalized = content.strip()
    return bool(normalized) and not normalized.startswith(STREAM_ERROR_PREFIX)


def collect_token_chunks(stream_events: list[ArchiverStreamEvent]) -> list[str]:
    """ArchiverStreamEvent 목록에서 token 이벤트 content만 추출한다."""
    return [event.content for event in stream_events if event.event == "token"]


def _format_web_user_content(
    *,
    title: str | None,
    url: str | None,
    raw_body: str,
) -> str:
    lines: list[str] = []
    if title and title.strip():
        lines.append(f"제목: {title.strip()}")
    if url and url.strip():
        lines.append(f"URL: {url.strip()}")
    lines.append(f"본문:\n{raw_body}")
    return "\n".join(lines)


class ArchiverService:
    def __init__(
        self,
        db: AsyncSession = Depends(get_db),
        archiver_engine: ArchiverEngine = Depends(get_archiver_engine),
        scrap_embedding_service: ScrapEmbeddingService = Depends(),
    ) -> None:
        self.repo = ArchiverRepository(db)
        self.scrap_repo = ScrapRepository(db)
        self.archiver_engine = archiver_engine
        self.scrap_embedding_service = scrap_embedding_service

    async def generate_archive_stream(
        self,
        request: ChatStreamRequest,
        *,
        user_id: uuid.UUID,
    ) -> AsyncIterator[str]:
        """세션·로그 조립 후 LangGraph State를 초기화하여 그래프에 실행 위임."""
        context_title = request.context.title if request.context else NO_CONTEXT_TITLE
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

    async def create_scrap_pipeline(
        self,
        *,
        user_id: uuid.UUID,
        request_data: ScrapCreateRequest,
    ) -> ScrapResponse:
        """페이지 본문을 Gemini로 요약·분류한 뒤 DB에 저장한다."""
        raw_body = truncate_raw_body(request_data.raw_body)
        user_content = _format_web_user_content(
            title=request_data.title,
            url=request_data.url,
            raw_body=raw_body,
        )

        classification = await classify_scrap_content(
            user_content,
            custom_category=normalize_custom_category(request_data.custom_category),
        )

        scrap = await self.scrap_repo.create_scrap(
            user_id=user_id,
            source_type="web",
            url=request_data.url,
            title=request_data.title,
            summary=classification.summary,
            category=classification.category,
            tags=classification.tags,
            raw_body_snapshot=raw_body or None,
            session_id=None,
        )
        await self.scrap_embedding_service.embed_and_persist(
            scrap_id=scrap.id,
            title=request_data.title,
            summary=classification.summary,
            raw_body=raw_body or None,
        )
        return ScrapResponse.model_validate(scrap)

    async def get_user_scraps(
        self,
        *,
        user_id: uuid.UUID,
        limit: int = 50,
    ) -> list[ScrapResponse]:
        """유저 스크랩 목록을 최신순으로 반환한다."""
        scraps = await self.scrap_repo.get_scraps_by_user_id(
            user_id=user_id,
            limit=limit,
        )
        return [ScrapResponse.model_validate(scrap) for scrap in scraps]

    async def get_user_scrap_detail(
        self,
        *,
        user_id: uuid.UUID,
        scrap_id: uuid.UUID,
    ) -> ScrapDetailResponse:
        """본인 소유 스크랩 1건과 URL 기준 Archiver 대화 히스토리를 반환한다."""
        scrap = await self.scrap_repo.get_scrap_by_id(
            user_id=user_id,
            scrap_id=scrap_id,
        )
        if scrap is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="스크랩을 찾을 수 없습니다.",
            )

        scrap_response = ScrapResponse.model_validate(scrap)
        archiver_session_id: str | None = None
        archiver_history: list[ArchiverChatMessage] = []

        if scrap.url:
            archiver_session_id = await self.repo.find_session_id_by_url(
                user_id=user_id,
                url=scrap.url,
            )
            if archiver_session_id:
                archiver_history = await self.repo.get_chat_history(
                    archiver_session_id,
                    user_id=user_id,
                )

        return ScrapDetailResponse(
            scrap=scrap_response,
            archiver_session_id=archiver_session_id,
            archiver_history=archiver_history,
        )

    async def delete_user_scrap(
        self,
        *,
        user_id: uuid.UUID,
        scrap_id: uuid.UUID,
    ) -> None:
        """본인 소유 스크랩을 삭제한다. 없으면 404."""
        deleted = await self.scrap_repo.delete_scrap(
            user_id=user_id,
            scrap_id=scrap_id,
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="스크랩을 찾을 수 없습니다.",
            )

    async def get_active_sessions(
        self,
        *,
        user_id: uuid.UUID,
    ) -> list[ArchiverSessionSummary]:
        """유저의 활성 Archiver 세션 목록을 반환한다."""
        return await self.repo.get_user_sessions(user_id=user_id)

    async def get_session_history(
        self,
        session_id: str,
        *,
        user_id: uuid.UUID,
    ) -> list[ArchiverChatMessage]:
        """한 세션의 대화 히스토리를 반환한다 (유저 스코프)."""
        return await self.repo.get_chat_history(
            session_id=session_id,
            user_id=user_id,
        )
