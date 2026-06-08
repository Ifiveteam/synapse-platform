"""
Navigator Agent - LangGraph Workflow
이상향 설계 전체 플로우:
  init → analyze_profile → generate_ideals → chat_design
       → confirm_ideal → generate_guide → generate_quest
       → build_playlist → complete
"""

import json
import os
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from .prompt import (
    CHAT_DESIGN_PROMPT,
    GUIDE_PROMPT,
    IDEAL_DESIGN_PROMPT,
    PLAYLIST_PROMPT,
    QUEST_PROMPT,
    SYSTEM_PROMPT,
)
from .schemas import (
    Guide,
    IdealDesignResponse,
    IdealRadarChart,
    IdealType,
    Quest,
)
from .state import NavigatorState, NavigatorStep
from .tool import (
    compare_radar,
    generate_all_ideals,
    generate_guide,
    generate_quests,
)
from .youtube import build_playlist_from_ideal


# ──────────────────────────────────────────
# LLM 초기화
# ──────────────────────────────────────────


def _get_llm(temperature: float = 0.7) -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("NAVIGATOR_MODEL", "gpt-4o"),
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def _safe_parse_json(text: str) -> dict:
    """LLM 응답에서 JSON 블록 추출"""
    # ```json ... ``` 블록 우선
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()
    return json.loads(text)


# ──────────────────────────────────────────
# 노드 정의
# ──────────────────────────────────────────


def node_analyze_profile(state: NavigatorState) -> dict:
    """
    현재 레이더 차트 수신 확인 + 프로필 분석 메시지 생성
    """
    if not state.current_radar:
        return {"error": "current_radar 데이터가 없습니다. 프로파일러 에이전트 확인 필요."}

    radar = state.current_radar
    scores = radar.to_dict()

    # 편향 축 찾기
    bias_axes = []
    for key, score in scores.items():
        if score < 30:
            bias_axes.append(f"{key.value}({score:.0f}점, 낮음)")
        elif score > 70:
            bias_axes.append(f"{key.value}({score:.0f}점, 높음)")

    summary = f"프로필 분석 완료. 편향 축: {', '.join(bias_axes) if bias_axes else '없음'}"

    return {
        "current_step": NavigatorStep.ANALYZE_PROFILE,
        "messages": [AIMessage(content=summary)],
    }


def node_generate_ideals(state: NavigatorState) -> dict:
    """
    수식 기반으로 3가지 이상향 자동 생성 + LLM 메시지 작성
    """
    if not state.current_radar:
        return {"error": "current_radar 없음"}

    # 수식 기반 이상향 3종 생성
    proposals = generate_all_ideals(state.current_radar)

    # LLM으로 소개 메시지 생성
    llm = _get_llm(temperature=0.7)
    prompt = IDEAL_DESIGN_PROMPT.format(
        current_radar=json.dumps(state.current_radar.to_dict(), ensure_ascii=False),
        top5_interests=", ".join(state.top5_interests),
    )

    response = llm.invoke([
        HumanMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    agent_message = response.content

    ideal_response = IdealDesignResponse(
        user_id=state.user_id,
        proposals=proposals,
        agent_message=agent_message,
    )

    return {
        "current_step": NavigatorStep.GENERATE_IDEALS,
        "ideal_proposals": ideal_response,
        "messages": [AIMessage(content=agent_message)],
    }


def node_chat_design(state: NavigatorState) -> dict:
    """
    대화형 이상향 설계 노드
    유저 메시지에 응답하고, 이상향을 조율함
    """
    llm = _get_llm(temperature=0.8)

    proposals_json = ""
    if state.ideal_proposals:
        proposals_json = json.dumps(
            [p.to_dict() for p in state.ideal_proposals.proposals],
            ensure_ascii=False,
        )

    system = CHAT_DESIGN_PROMPT.format(
        current_radar=json.dumps(
            state.current_radar.to_dict() if state.current_radar else {},
            ensure_ascii=False,
        ),
        ideal_proposals=proposals_json,
    )

    messages = [HumanMessage(content=SYSTEM_PROMPT + "\n\n" + system)]
    messages.extend(state.messages)

    response = llm.invoke(messages)
    return {
        "current_step": NavigatorStep.CHAT_DESIGN,
        "messages": [response],
    }


def node_confirm_ideal(state: NavigatorState) -> dict:
    """
    이상향 확정 + gap 계산
    selected_ideal이 없으면 adjacent(인접형) 기본 선택
    """
    if not state.selected_ideal and state.ideal_proposals:
        # 기본값: ADJACENT
        for p in state.ideal_proposals.proposals:
            if p.ideal_type == IdealType.ADJACENT:
                selected = p
                break
        else:
            selected = state.ideal_proposals.proposals[0]
    else:
        selected = state.selected_ideal

    comparison = compare_radar(state.current_radar, selected)

    return {
        "current_step": NavigatorStep.CONFIRM_IDEAL,
        "selected_ideal": selected,
        "ideal_type": selected.ideal_type,
        "comparison": comparison,
        "is_ideal_confirmed": True,
        "messages": [AIMessage(content=f"이상향이 확정되었습니다: {selected.summary}")],
    }


def node_generate_guide(state: NavigatorState) -> dict:
    """
    gap 분석 기반 30일 가이드 생성
    수식 기반 우선, LLM으로 자연어 보강
    """
    if not state.comparison:
        return {"error": "comparison 없음"}

    guide = generate_guide(state.comparison, state.top5_interests)

    # LLM으로 가이드 메시지 자연어화
    llm = _get_llm(temperature=0.6)
    prompt = GUIDE_PROMPT.format(
        comparison=json.dumps({
            "gap": state.comparison.gap,
            "total_gap": state.comparison.total_gap,
        }, ensure_ascii=False),
        top5_interests=", ".join(state.top5_interests),
    )

    response = llm.invoke([
        HumanMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    # LLM 응답으로 가이드 메시지 보강
    guide_message = f"📋 **{guide.title}**\n\n"
    for step in guide.steps:
        guide_message += f"• {step}\n"

    return {
        "current_step": NavigatorStep.GENERATE_GUIDE,
        "guide": guide,
        "messages": [AIMessage(content=guide_message)],
    }


def node_generate_quest(state: NavigatorState) -> dict:
    """
    오늘의 퀘스트 3개 생성
    """
    if not state.comparison:
        return {"error": "comparison 없음"}

    quests = generate_quests(state.comparison, state.top5_interests, count=3)

    quest_message = "🎯 **오늘의 퀘스트**\n\n"
    for i, q in enumerate(quests, 1):
        quest_message += f"{i}. **{q.title}** (+{q.reward_point}pt)\n"
        quest_message += f"   {q.description}\n"
        quest_message += f"   → {q.action}\n\n"

    return {
        "current_step": NavigatorStep.GENERATE_QUEST,
        "quests": quests,
        "messages": [AIMessage(content=quest_message)],
    }


async def node_build_playlist(state: NavigatorState) -> dict:
    """
    이상향 기반 YouTube 재생목록 생성
    LLM으로 검색어 생성 → YouTube API 검색 → 플레이리스트 빌드
    """
    if not state.selected_ideal:
        return {"error": "selected_ideal 없음"}

    llm = _get_llm(temperature=0.7)
    prompt = PLAYLIST_PROMPT.format(
        ideal_radar=json.dumps(state.selected_ideal.to_dict(), ensure_ascii=False),
        top5_interests=", ".join(state.top5_interests),
    )

    response = llm.invoke([
        HumanMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    try:
        parsed = _safe_parse_json(response.content)
        playlist_title = parsed.get("playlist_title", "나의 이상향 플레이리스트")
        playlist_description = parsed.get("playlist_description", "")
        search_queries = parsed.get("search_queries", [])
    except (json.JSONDecodeError, ValueError):
        search_queries = [{"query": interest, "reason": "관심사 기반"} for interest in state.top5_interests]
        playlist_title = "나의 이상향 플레이리스트"
        playlist_description = "Synapse Navigator가 설계한 버블 탈출 재생목록"

    playlist = await build_playlist_from_ideal(
        user_id=state.user_id,
        ideal=state.selected_ideal,
        search_queries=search_queries,
        playlist_title=playlist_title,
        playlist_description=playlist_description,
        access_token=None,  # TODO: OAuth 연동 시 토큰 전달
    )

    playlist_message = f"🎬 **{playlist.title}**\n{playlist.description}\n\n"
    for item in playlist.items[:5]:
        playlist_message += f"• {item.title} - {item.channel}\n"
    if len(playlist.items) > 5:
        playlist_message += f"...외 {len(playlist.items) - 5}개\n"

    return {
        "current_step": NavigatorStep.BUILD_PLAYLIST,
        "playlist": playlist,
        "messages": [AIMessage(content=playlist_message)],
    }


def node_complete(state: NavigatorState) -> dict:
    """워크플로우 완료"""
    return {
        "current_step": NavigatorStep.COMPLETE,
        "messages": [AIMessage(content="✅ 이상향 설계가 완료되었습니다. 오늘부터 시작해볼까요?")],
    }


# ──────────────────────────────────────────
# 라우팅 함수
# ──────────────────────────────────────────


def route_after_chat(state: NavigatorState) -> str:
    """대화 완료 여부에 따라 라우팅"""
    if state.is_ideal_confirmed:
        return "confirm_ideal"
    return "chat_design"  # 계속 대화


def route_after_confirm(state: NavigatorState) -> str:
    """확정 후 가이드 생성으로"""
    return "generate_guide"


# ──────────────────────────────────────────
# 그래프 빌드
# ──────────────────────────────────────────


def build_navigator_graph() -> StateGraph:
    """Navigator LangGraph 워크플로우 빌드"""

    graph = StateGraph(NavigatorState)

    # 노드 등록
    graph.add_node("analyze_profile", node_analyze_profile)
    graph.add_node("generate_ideals", node_generate_ideals)
    graph.add_node("chat_design", node_chat_design)
    graph.add_node("confirm_ideal", node_confirm_ideal)
    graph.add_node("generate_guide", node_generate_guide)
    graph.add_node("generate_quest", node_generate_quest)
    graph.add_node("build_playlist", node_build_playlist)
    graph.add_node("complete", node_complete)

    # 엣지 연결
    graph.add_edge(START, "analyze_profile")
    graph.add_edge("analyze_profile", "generate_ideals")
    graph.add_edge("generate_ideals", "chat_design")

    # 대화 → 이상향 확정 또는 계속 대화
    graph.add_conditional_edges(
        "chat_design",
        route_after_chat,
        {
            "confirm_ideal": "confirm_ideal",
            "chat_design": "chat_design",
        },
    )

    graph.add_edge("confirm_ideal", "generate_guide")
    graph.add_edge("generate_guide", "generate_quest")
    graph.add_edge("generate_quest", "build_playlist")
    graph.add_edge("build_playlist", "complete")
    graph.add_edge("complete", END)

    return graph


# 컴파일된 그래프 (싱글톤)
_compiled_graph = None


def get_navigator_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_navigator_graph().compile()
    return _compiled_graph
