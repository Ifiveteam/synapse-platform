"""Curator 메인 채팅 스트리밍 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.v1.auth import get_current_user_dep
from app.models.user import User
from app.schemas.curator import (
    CuratorChatRequest,
    CuratorSessionListResponse,
    CuratorSessionMessagesResponse,
)
from app.services.curator_service import CuratorService

router = APIRouter(prefix="/curator", tags=["Curator"])


@router.post("/stream")
async def stream_chat(
    request: CuratorChatRequest,
    user: User = Depends(get_current_user_dep),
    service: CuratorService = Depends(),
):
    """메인 채팅 — SSE 스트림으로 답변 반환."""
    session_id = request.session_id or str(uuid.uuid4())

    return StreamingResponse(
        service.generate_stream(
            message=request.message,
            user_id=user.id,
            session_id=session_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions", response_model=CuratorSessionListResponse)
async def list_sessions(
    user: User = Depends(get_current_user_dep),
    service: CuratorService = Depends(),
):
    """유저의 큐레이터 채팅 세션 목록 반환."""
    sessions = await service.list_sessions(user.id)
    return CuratorSessionListResponse(sessions=sessions)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user_dep),
    service: CuratorService = Depends(),
):
    """세션 삭제."""
    await service.delete_session(session_id, user.id)


@router.get(
    "/sessions/{session_id}/messages", response_model=CuratorSessionMessagesResponse
)
async def get_session_messages(
    session_id: str,
    user: User = Depends(get_current_user_dep),
    service: CuratorService = Depends(),
):
    """특정 세션의 메시지 목록 반환."""
    messages = await service.get_session_messages(session_id, user.id)
    return CuratorSessionMessagesResponse(messages=messages)
