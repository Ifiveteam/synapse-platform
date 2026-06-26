"""Scrap 비즈니스 로직 — Gemini 파이프라인 및 DB 영속화."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.scrap.classifier import classify_scrap_content, truncate_raw_body
from app.core.database.session import get_db
from app.repositories.archiver_repository import ArchiverRepository
from app.repositories.scrap_repository import ScrapRepository
from app.schemas.archiver import ArchiverChatMessage
from app.schemas.scrap import ScrapCreateRequest, ScrapResponse


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


def _format_chat_user_content(
    *,
    title: str | None,
    url: str | None,
    user_message: str,
    assistant_message: str,
) -> str:
    lines: list[str] = ["[대화 맥락 스크랩]"]
    if title and title.strip():
        lines.append(f"페이지 제목: {title.strip()}")
    if url and url.strip():
        lines.append(f"페이지 URL: {url.strip()}")
    lines.append(f"사용자: {user_message.strip()}")
    lines.append(f"AI: {assistant_message.strip()}")
    return "\n".join(lines)


def extract_last_dialogue_turn(
    history: list[ArchiverChatMessage],
) -> tuple[str, str] | None:
    """세션 히스토리에서 마지막 user→assistant 턴을 추출한다."""
    if not history:
        return None

    last_assistant_idx: int | None = None
    for index in range(len(history) - 1, -1, -1):
        if history[index].role == "assistant":
            last_assistant_idx = index
            break

    if last_assistant_idx is None:
        return None

    assistant_message = history[last_assistant_idx].content.strip()
    if not assistant_message:
        return None

    for index in range(last_assistant_idx - 1, -1, -1):
        if history[index].role == "user":
            user_message = history[index].content.strip()
            if user_message:
                return user_message, assistant_message
            break

    return None


class ScrapService:
    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.scrap_repo = ScrapRepository(db)
        self.archiver_repo = ArchiverRepository(db)

    async def create_scrap_pipeline(
        self,
        *,
        user_id: uuid.UUID,
        request_data: ScrapCreateRequest,
    ) -> ScrapResponse:
        """수집 경로별 맥락을 조립한 뒤 Gemini 분류·DB 저장까지 수행한다."""
        if request_data.source_type == "web":
            raw_body = truncate_raw_body(request_data.raw_body)
            user_content = _format_web_user_content(
                title=request_data.title,
                url=request_data.url,
                raw_body=raw_body,
            )
            raw_body_snapshot = raw_body
            session_id = None
        else:
            session_id = (request_data.session_id or "").strip()
            history = await self.archiver_repo.get_chat_history(
                session_id=session_id,
                user_id=user_id,
            )
            last_turn = extract_last_dialogue_turn(history)
            if last_turn is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="스크랩할 대화 턴을 찾을 수 없습니다.",
                )

            user_message, assistant_message = last_turn
            user_content = _format_chat_user_content(
                title=request_data.title,
                url=request_data.url,
                user_message=user_message,
                assistant_message=assistant_message,
            )
            raw_body_snapshot = truncate_raw_body(user_content)

        classification = await classify_scrap_content(user_content)

        scrap = await self.scrap_repo.create_scrap(
            user_id=user_id,
            source_type=request_data.source_type,
            url=request_data.url,
            title=request_data.title,
            summary=classification.summary,
            category=classification.category,
            tags=classification.tags,
            raw_body_snapshot=raw_body_snapshot or None,
            session_id=session_id,
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
