"""Curator 메인 채팅 스트리밍 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.v1.auth import get_current_user_dep
from app.models.user import User
from app.schemas.curator import CuratorChatRequest
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
