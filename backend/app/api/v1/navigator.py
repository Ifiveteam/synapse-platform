"""Navigator 에이전트 라우터 — 이상향 설계·보관·적용·비교·가이드 (인증 필수).

[제안]   GET  /navigator/proposals             → 21축 → 반대·강점심화·균형 3종
[설계]   POST /navigator/chat/stream           → 대화형 이상향 설계 (SSE)
[보관]   POST /navigator/ideal                 → 이상향 생성(여러 개 보관)
         GET  /navigator/ideals                → 보관된 이상향 목록
         GET  /navigator/ideal/{id}            → 단건
[적용]   POST /navigator/ideal/{id}/apply      → 적용 중으로 설정 (1개만)
[분석]   GET  /navigator/ideal/{id}/comparison → 현재 vs 그 이상향 gap
         GET  /navigator/ideal/{id}/guide      → 그 이상향 기반 행동 가이드
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.v1.auth import get_current_user_dep
from app.models.user import User
from app.schemas.navigator import (
    ComparisonResponse,
    ConfirmIdealRequest,
    GuideResponse,
    IdealResponse,
    NavigatorChatRequest,
    PlaylistChatRequest,
    PlaylistResponse,
    PlaylistSummary,
    ProposalsResponse,
    RefreshItemRequest,
    RenamePlaylistRequest,
    SaveStartResponse,
)
from app.services.navigator import NavigatorService

router = APIRouter(prefix="/navigator", tags=["Navigator Agent"])


@router.get("/proposals", response_model=ProposalsResponse)
async def get_proposals(
    source_profile_history_id: str | None = Query(
        default=None, description="기준 분석 스냅샷 (없으면 최신)"
    ),
    refresh: bool = Query(default=False, description="캐시 무시하고 3안 새로 생성"),
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> ProposalsResponse:
    """선택한(없으면 최신) 21축 프로필을 근거로 반대·강점심화·균형 이상향을 제안한다.

    같은 (유저+스냅샷)이면 캐시된 3안을 재사용한다. refresh=true로 새로 생성.
    """
    snapshot_id: uuid.UUID | None = None
    if source_profile_history_id:
        try:
            snapshot_id = uuid.UUID(source_profile_history_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid source_profile_history_id",
            ) from exc
    return await navigator_service.get_proposals(
        user_id=user.id, source_profile_history_id=snapshot_id, refresh=refresh
    )


@router.post("/chat/stream")
async def stream_chat(
    request: NavigatorChatRequest,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
):
    """대화형 이상향 설계 SSE 스트림."""
    return StreamingResponse(
        navigator_service.stream_chat(request, user_id=user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ideal", response_model=IdealResponse)
async def create_ideal(
    request: ConfirmIdealRequest,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> IdealResponse:
    """이상향을 새로 생성해 보관한다 (적용은 별도)."""
    return await navigator_service.confirm_ideal(request, user_id=user.id)


@router.get("/ideals", response_model=list[IdealResponse])
async def list_ideals(
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> list[IdealResponse]:
    """보관된 이상향 목록 (최신순)."""
    return await navigator_service.list_ideals(user_id=user.id)


@router.get("/ideal/{ideal_id}", response_model=IdealResponse)
async def get_ideal(
    ideal_id: uuid.UUID,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> IdealResponse:
    """단건 이상향 조회."""
    return await navigator_service.get_ideal(user_id=user.id, ideal_id=ideal_id)


@router.post("/ideal/{ideal_id}/apply", response_model=IdealResponse)
async def apply_ideal(
    ideal_id: uuid.UUID,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> IdealResponse:
    """이 이상향을 '적용 중'으로 설정한다 (유저당 1개)."""
    return await navigator_service.apply_ideal(user_id=user.id, ideal_id=ideal_id)


@router.get("/ideal/{ideal_id}/comparison", response_model=ComparisonResponse)
async def get_comparison(
    ideal_id: uuid.UUID,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> ComparisonResponse:
    """현재 행동 8축 vs 해당 이상향 gap."""
    return await navigator_service.get_comparison(user_id=user.id, ideal_id=ideal_id)


@router.get("/ideal/{ideal_id}/guide", response_model=GuideResponse)
async def get_guide(
    ideal_id: uuid.UUID,
    refresh: bool = Query(default=False, description="캐시 무시하고 새로 생성"),
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> GuideResponse:
    """해당 이상향 기반 행동 가이드 (catalog RAG 그라운딩, 생성 결과 캐시)."""
    return await navigator_service.get_guide(
        user_id=user.id, ideal_id=ideal_id, refresh=refresh
    )


# ── 재생목록 (이상향 1개 : N개) ──────────────────────────────────
@router.post("/ideal/{ideal_id}/playlists", response_model=PlaylistResponse)
async def create_playlist(
    ideal_id: uuid.UUID,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> PlaylistResponse:
    """이상향+시청기록 근거로 새 재생목록 생성 (영상 10개 + 저수지)."""
    return await navigator_service.create_playlist(user_id=user.id, ideal_id=ideal_id)


@router.get("/ideal/{ideal_id}/playlists", response_model=list[PlaylistSummary])
async def list_playlists(
    ideal_id: uuid.UUID,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> list[PlaylistSummary]:
    """해당 이상향의 재생목록 목록."""
    return await navigator_service.list_playlists(user_id=user.id, ideal_id=ideal_id)


@router.get("/playlists/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: uuid.UUID,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> PlaylistResponse:
    """재생목록 단건."""
    return await navigator_service.get_playlist(
        user_id=user.id, playlist_id=playlist_id
    )


@router.patch("/playlists/{playlist_id}", response_model=PlaylistResponse)
async def rename_playlist(
    playlist_id: uuid.UUID,
    body: RenamePlaylistRequest,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> PlaylistResponse:
    """재생목록 제목 수정."""
    return await navigator_service.rename_playlist(
        user_id=user.id, playlist_id=playlist_id, title=body.title
    )


@router.delete("/playlists/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: uuid.UUID,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> None:
    """재생목록 삭제."""
    await navigator_service.delete_playlist(user_id=user.id, playlist_id=playlist_id)


@router.post("/playlists/{playlist_id}/item/refresh", response_model=PlaylistResponse)
async def refresh_playlist_item(
    playlist_id: uuid.UUID,
    body: RefreshItemRequest,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> PlaylistResponse:
    """영상 1개를 새 후보로 교체 (저수지→채널 re-RSS)."""
    return await navigator_service.refresh_item(
        user_id=user.id, playlist_id=playlist_id, video_id=body.video_id
    )


@router.post("/playlists/{playlist_id}/regenerate", response_model=PlaylistResponse)
async def regenerate_playlist(
    playlist_id: uuid.UUID,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> PlaylistResponse:
    """재생목록 전체 재생성 (채널 재발굴→큐레이션, 같은 행 갱신)."""
    return await navigator_service.regenerate_playlist(
        user_id=user.id, playlist_id=playlist_id
    )


@router.post("/playlists/{playlist_id}/save", response_model=SaveStartResponse)
async def save_playlist_to_youtube(
    playlist_id: uuid.UUID,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
) -> SaveStartResponse:
    """재생목록을 실제 YouTube에 비동기 저장 시작 (needs_reconsent면 재동의 필요)."""
    return await navigator_service.save_playlist_to_youtube(
        user_id=user.id, playlist_id=playlist_id
    )


@router.post("/playlists/{playlist_id}/chat")
async def chat_edit_playlist(
    playlist_id: uuid.UUID,
    body: PlaylistChatRequest,
    user: User = Depends(get_current_user_dep),
    navigator_service: NavigatorService = Depends(),
):
    """채팅으로 재생목록 부분수정 (SSE: status + 최종 playlist)."""
    return StreamingResponse(
        navigator_service.chat_edit(
            user_id=user.id, playlist_id=playlist_id, message=body.message
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
