"""
Archiver 에이전트 전용 SSE 스트리밍 라우터
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatStreamRequest
from app.services.archiver_service import DEFAULT_USER_ID, ArchiverService

router = APIRouter(prefix="/archiver", tags=["Archiver Agent"])


@router.post("/stream")
async def stream_archiver_response(
    request: ChatStreamRequest,
    archiver_service: ArchiverService = Depends(),
):
    """
    유저가 수집한 웹 맥락(Context) 데이터와 질문을 아카이버 에이전트로 전달하여
    실시간 분석 및 기록 스트리밍을 반환합니다.
    """
    return StreamingResponse(
        archiver_service.generate_archive_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions")
async def get_archiver_sessions(
    archiver_service: ArchiverService = Depends(),
):
    """현재 로그인한 유저의 아카이버 대화 세션(웹페이지) 역사 목록을 반환한다."""
    sessions = await archiver_service.get_active_sessions(user_id=DEFAULT_USER_ID)
    return {
        "status": "success",
        "data": [session.model_dump(mode="json") for session in sessions],
    }


@router.get("/history/{session_id}")
async def get_session_chat_history(
    session_id: str,
    archiver_service: ArchiverService = Depends(),
):
    """특정 세션 ID의 유저-AI 대화 타임라인을 복원한다."""
    history = await archiver_service.get_session_history(session_id=session_id)
    return {
        "status": "success",
        "data": [message.model_dump(mode="json") for message in history],
    }
