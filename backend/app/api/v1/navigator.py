"""
Navigator Agent - FastAPI Router (v1.1)

[이상향 자동 설계]
  POST /navigator/design          → 수식 기반 3종 자동 제안

[이상향 수정 — 3모드]
  PATCH /navigator/ideal/direct   → Mode 1: 직접 수치 수정 (모델 없음)
  POST  /navigator/ideal/chat     → Mode 2: 자연어 대화 수정 (gpt-4o-mini)
  POST  /navigator/ideal/auto     → Mode 3: AI 최적 이상향 설계 (gpt-4o)

[이상향 확정 후]
  POST  /navigator/confirm        → 가이드 + 퀘스트 생성
  POST  /navigator/chat           → 대화형 이상향 설계 SSE

[재생목록]
  POST  /navigator/playlist       → YouTube 재생목록 생성
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.navigator import (
    Guide,
    IdealDesignResponse,
    IdealRadarChart,
    NavigatorAgent,
    Playlist,
    ProfilerData,
    Quest,
    get_navigator_agent,
)
from app.agents.navigator.modifier import modify_by_chat, modify_direct, optimize_auto
from app.agents.navigator.tool import compare_radar

router = APIRouter(prefix="/navigator", tags=["navigator"])


# ──────────────────────────────────────────
# 공통 Request 모델
# ──────────────────────────────────────────


class DesignIdealRequest(BaseModel):
    user_id: str
    profiler_data: ProfilerData
    top5_interests: list[str] = Field(default_factory=list)


class ConfirmIdealRequest(BaseModel):
    user_id: str
    profiler_data: ProfilerData
    selected_ideal: IdealRadarChart
    top5_interests: list[str] = Field(default_factory=list)


class ConfirmIdealResponse(BaseModel):
    guide: Guide
    quests: list[Quest]
    message: str


class PlaylistRequest(BaseModel):
    user_id: str
    profiler_data: ProfilerData
    selected_ideal: IdealRadarChart
    top5_interests: list[str] = Field(default_factory=list)
    access_token: Optional[str] = None


class ChatRequest(BaseModel):
    user_id: str
    profiler_data: ProfilerData
    top5_interests: list[str] = Field(default_factory=list)
    user_message: str
    ideal_proposals: Optional[IdealDesignResponse] = None
    selected_ideal: Optional[IdealRadarChart] = None
    is_ideal_confirmed: bool = False


# ──────────────────────────────────────────
# 이상향 수정 3모드 Request 모델
# ──────────────────────────────────────────


class DirectModifyRequest(BaseModel):
    """Mode 1: 직접 수정"""

    user_id: str
    ideal: IdealRadarChart
    axis: str = Field(description="수정할 축 key (예: creative_expression)")
    new_value: float = Field(ge=0, le=100, description="새 값 (0~100)")


class DirectModifyResponse(BaseModel):
    updated_ideal: IdealRadarChart
    suggestions: list[str] = Field(description="연관 축 조정 제안 메시지")


class ChatModifyRequest(BaseModel):
    """Mode 2: 대화 수정"""

    user_id: str
    ideal: IdealRadarChart
    user_message: str
    profiler_data: Optional[ProfilerData] = None  # 컨텍스트용 (선택)


class ChatModifyResponse(BaseModel):
    updated_ideal: IdealRadarChart
    adjustments: list[dict] = Field(description="적용된 변경 목록")
    reasoning: str
    reply: str = Field(description="유저에게 보낼 응답")


class AutoOptimalRequest(BaseModel):
    """Mode 3: AI 최적 설계"""

    user_id: str
    profiler_data: ProfilerData
    top5_interests: list[str] = Field(default_factory=list)
    user_goal: Optional[str] = Field(None, description="유저 목표 텍스트 (선택)")


class AutoOptimalResponse(BaseModel):
    ideal: IdealRadarChart
    reasoning: str = Field(description="AI 설계 근거")


# ──────────────────────────────────────────
# 이상향 자동 설계 (수식 기반 3종)
# ──────────────────────────────────────────


@router.post(
    "/design",
    response_model=IdealDesignResponse,
    summary="이상향 자동 설계 — 수식 기반 3종 (OPPOSITE / EXPANSION / BALANCED)",
)
async def design_ideal(req: DesignIdealRequest) -> IdealDesignResponse:
    agent: NavigatorAgent = get_navigator_agent()
    return agent.design_ideal_auto(
        user_id=req.user_id,
        profiler_data=req.profiler_data,
        top5_interests=req.top5_interests,
    )


# ──────────────────────────────────────────
# 이상향 수정 — Mode 1: DIRECT
# ──────────────────────────────────────────


@router.patch(
    "/ideal/direct",
    response_model=DirectModifyResponse,
    summary="이상향 직접 수정 — 특정 축 수치 변경 (모델 없음)",
)
async def modify_ideal_direct(req: DirectModifyRequest) -> DirectModifyResponse:
    """
    슬라이더·직접 입력으로 특정 축 값을 수정.
    AXIS_VECTORS 기반으로 연관 축 조정 제안도 함께 반환.
    """
    try:
        updated, suggestions = modify_direct(req.ideal, req.axis, req.new_value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return DirectModifyResponse(
        updated_ideal=updated,
        suggestions=suggestions,
    )


# ──────────────────────────────────────────
# 이상향 수정 — Mode 2: CHAT (gpt-4o-mini)
# ──────────────────────────────────────────


@router.post(
    "/ideal/chat",
    response_model=ChatModifyResponse,
    summary="이상향 대화 수정 — 자연어 → delta 추출 (gpt-4o-mini)",
)
async def modify_ideal_chat(req: ChatModifyRequest) -> ChatModifyResponse:
    """
    자연어 메시지로 이상향 조율.
    예: "창의표현 좀 올리고 실용지향은 낮춰줘"

    gpt-4o-mini가 의도를 파악해 delta 추출 → 적용 후 반환.
    """
    import os

    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.",
        )

    current_radar = req.profiler_data.layer_a if req.profiler_data else None
    layer_b = req.profiler_data.layer_b if req.profiler_data else None

    try:
        updated, result = modify_by_chat(
            ideal=req.ideal,
            user_message=req.user_message,
            current_radar=current_radar,
            layer_b=layer_b,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 호출 실패: {str(e)}") from e

    return ChatModifyResponse(
        updated_ideal=updated,
        adjustments=[a.model_dump() for a in result.adjustments],
        reasoning=result.reasoning,
        reply=result.reply,
    )


# ──────────────────────────────────────────
# 이상향 수정 — Mode 3: AUTO OPTIMAL (gpt-4o)
# ──────────────────────────────────────────


@router.post(
    "/ideal/auto",
    response_model=AutoOptimalResponse,
    summary="이상향 AI 최적 설계 — Layer A+B 종합 분석 (gpt-4o)",
)
async def optimize_ideal_auto(req: AutoOptimalRequest) -> AutoOptimalResponse:
    """
    gpt-4o가 현재 프로필(Layer A 8각 + Layer B 4지표)을 종합 분석하여
    가장 이상적인 이상향을 자동 설계.

    수식 기반 3종과 나란히 제시 → 유저 선택.
    """
    import os

    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.",
        )

    try:
        ideal = optimize_auto(
            current_radar=req.profiler_data.layer_a,
            layer_b=req.profiler_data.layer_b,
            top5_interests=req.top5_interests,
            user_goal=req.user_goal,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 호출 실패: {str(e)}") from e

    return AutoOptimalResponse(
        ideal=ideal,
        reasoning=ideal.reasoning,
    )


# ──────────────────────────────────────────
# 이상향 확정 + 가이드/퀘스트
# ──────────────────────────────────────────


@router.post(
    "/confirm",
    response_model=ConfirmIdealResponse,
    summary="이상향 확정 → 30일 가이드 + 퀘스트 생성",
)
async def confirm_ideal(req: ConfirmIdealRequest) -> ConfirmIdealResponse:
    agent: NavigatorAgent = get_navigator_agent()
    guide, quests = agent.generate_guide_and_quests(
        profiler_data=req.profiler_data,
        selected_ideal=req.selected_ideal,
        top5_interests=req.top5_interests,
    )
    comparison = compare_radar(req.profiler_data.layer_a, req.selected_ideal)
    gap_summary = f"총 gap: {comparison.total_gap:.1f}점"

    return ConfirmIdealResponse(
        guide=guide,
        quests=quests,
        message=f"이상향이 확정되었습니다! {gap_summary} — 오늘부터 시작해볼까요?",
    )


# ──────────────────────────────────────────
# 대화형 이상향 설계 (SSE)
# ──────────────────────────────────────────


@router.post("/chat", summary="대화형 이상향 설계 (SSE 스트리밍)")
async def chat_design(req: ChatRequest) -> StreamingResponse:
    """
    유저 메시지 → LangGraph chat 루프 → SSE 스트리밍 응답
    이상향 타입 선택, 조율, 확정까지 대화로 진행
    """
    from app.agents.navigator.state import NavigatorState

    state = NavigatorState(
        user_id=req.user_id,
        current_radar=req.profiler_data.layer_a,
        layer_b=req.profiler_data.layer_b,
        top5_interests=req.top5_interests,
        ideal_proposals=req.ideal_proposals,
        selected_ideal=req.selected_ideal,
        is_ideal_confirmed=req.is_ideal_confirmed,
    )

    agent: NavigatorAgent = get_navigator_agent()

    async def event_generator():
        try:
            async for chunk in agent.chat(state, req.user_message):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ──────────────────────────────────────────
# 재생목록
# ──────────────────────────────────────────


@router.post(
    "/playlist", response_model=Playlist, summary="이상향 기반 YouTube 재생목록 생성"
)
async def build_playlist(req: PlaylistRequest) -> Playlist:
    from app.agents.navigator.graph import node_build_playlist
    from app.agents.navigator.state import NavigatorState

    state = NavigatorState(
        user_id=req.user_id,
        current_radar=req.profiler_data.layer_a,
        layer_b=req.profiler_data.layer_b,
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


# ──────────────────────────────────────────
# 퀘스트 조회 (DB 연동 후 구현)
# ──────────────────────────────────────────


@router.get(
    "/quests/{user_id}", response_model=list[Quest], summary="오늘의 퀘스트 조회"
)
async def get_quests(user_id: str) -> list[Quest]:
    raise HTTPException(
        status_code=501,
        detail="DB 연동 후 구현 예정. /confirm으로 퀘스트를 생성하세요.",
    )
