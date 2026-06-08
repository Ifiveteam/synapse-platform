"""
Navigator Agent - FastAPI Router
POST /api/v1/navigator/design   → 이상향 자동 설계
POST /api/v1/navigator/confirm  → 이상향 확정 + 가이드/퀘스트 생성
GET  /api/v1/navigator/quests   → 오늘의 퀘스트 조회
POST /api/v1/navigator/playlist → 재생목록 빌드
POST /api/v1/navigator/chat     → 대화형 이상향 설계 (SSE 스트리밍)
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.navigator import (
    Guide,
    IdealDesignResponse,
    IdealRadarChart,
    IdealType,
    NavigatorAgent,
    Playlist,
    Quest,
    RadarChart,
    get_navigator_agent,
)
from app.agents.navigator.tool import compare_radar

router = APIRouter(prefix="/navigator", tags=["navigator"])


# ──────────────────────────────────────────
# Request / Response 모델
# ──────────────────────────────────────────


class DesignIdealRequest(BaseModel):
    user_id: str
    current_radar: RadarChart
    top5_interests: list[str]


class ConfirmIdealRequest(BaseModel):
    user_id: str
    current_radar: RadarChart
    selected_ideal: IdealRadarChart
    top5_interests: list[str]


class ConfirmIdealResponse(BaseModel):
    guide: Guide
    quests: list[Quest]
    message: str


class PlaylistRequest(BaseModel):
    user_id: str
    current_radar: RadarChart
    selected_ideal: IdealRadarChart
    top5_interests: list[str]
    access_token: Optional[str] = None


class ChatRequest(BaseModel):
    user_id: str
    current_radar: RadarChart
    top5_interests: list[str]
    user_message: str
    ideal_proposals: Optional[IdealDesignResponse] = None
    selected_ideal: Optional[IdealRadarChart] = None
    is_ideal_confirmed: bool = False


# ──────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────


@router.post("/design", response_model=IdealDesignResponse, summary="이상향 자동 설계")
async def design_ideal(req: DesignIdealRequest) -> IdealDesignResponse:
    """
    현재 8각 레이더 차트 + TOP5 관심사로 3가지 이상향 자동 제안
    - OPPOSITE  (반대 성향형)
    - ADJACENT  (인접 확장형)  ← 기본 추천
    - BALANCED  (밸런스형)
    """
    agent: NavigatorAgent = get_navigator_agent()
    return agent.design_ideal_auto(
        user_id=req.user_id,
        current_radar=req.current_radar,
        top5_interests=req.top5_interests,
    )


@router.post("/confirm", response_model=ConfirmIdealResponse, summary="이상향 확정 + 가이드/퀘스트 생성")
async def confirm_ideal(req: ConfirmIdealRequest) -> ConfirmIdealResponse:
    """
    이상향 확정 후 30일 가이드 + 오늘의 퀘스트 3개 생성
    """
    agent: NavigatorAgent = get_navigator_agent()
    guide, quests = agent.generate_guide_and_quests(
        user_id=req.user_id,
        current_radar=req.current_radar,
        selected_ideal=req.selected_ideal,
        top5_interests=req.top5_interests,
    )

    comparison = compare_radar(req.current_radar, req.selected_ideal)
    gap_summary = f"총 gap: {comparison.total_gap:.1f}점"

    return ConfirmIdealResponse(
        guide=guide,
        quests=quests,
        message=f"이상향이 확정되었습니다! {gap_summary} - 오늘부터 시작해볼까요?",
    )


@router.get("/quests/{user_id}", response_model=list[Quest], summary="오늘의 퀘스트 조회")
async def get_quests(
    user_id: str,
    current_radar: RadarChart = None,
    selected_ideal: IdealRadarChart = None,
) -> list[Quest]:
    """
    유저의 현재 이상향 gap 기반 오늘의 퀘스트 반환
    (실제 구현 시 DB에서 저장된 상태 조회)
    """
    # TODO: DB에서 user_id 기반으로 comparison 조회
    # 현재는 예시 응답
    raise HTTPException(
        status_code=501,
        detail="DB 연동 후 구현 예정. /confirm API로 퀘스트를 생성하세요.",
    )


@router.post("/playlist", response_model=Playlist, summary="이상향 기반 재생목록 생성")
async def build_playlist(req: PlaylistRequest) -> Playlist:
    """
    이상향 기반으로 YouTube 검색 + 재생목록 큐레이션
    access_token 제공 시 실제 YouTube 재생목록 생성
    """
    from app.agents.navigator.graph import node_build_playlist
    from app.agents.navigator.state import NavigatorState
    from app.agents.navigator.schemas import IdealDesignResponse as IResponse

    state = NavigatorState(
        user_id=req.user_id,
        current_radar=req.current_radar,
        top5_interests=req.top5_interests,
        selected_ideal=req.selected_ideal,
        ideal_type=req.selected_ideal.ideal_type,
    )

    result = await node_build_playlist(state)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    playlist = result.get("playlist")
    if not playlist:
        raise HTTPException(status_code=500, detail="재생목록 생성 실패")

    return playlist


@router.post("/chat", summary="대화형 이상향 설계 (SSE 스트리밍)")
async def chat_design(req: ChatRequest) -> StreamingResponse:
    """
    유저 메시지를 받아 Navigator와 실시간 대화
    이상향 타입 선택, 조율, 확정까지 대화로 진행

    Response: Server-Sent Events (text/event-stream)
    """
    from app.agents.navigator.state import NavigatorState

    state = NavigatorState(
        user_id=req.user_id,
        current_radar=req.current_radar,
        top5_interests=req.top5_interests,
        ideal_proposals=req.ideal_proposals,
        selected_ideal=req.selected_ideal,
        is_ideal_confirmed=req.is_ideal_confirmed,
    )

    agent: NavigatorAgent = get_navigator_agent()

    async def event_generator():
        try:
            async for chunk in agent.chat(state, req.user_message):
                # SSE 형식
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
