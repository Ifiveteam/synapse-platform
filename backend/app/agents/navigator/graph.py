"""
Navigator Agent - LangGraph Workflow (Dual-Layer)

init → analyze_profile (Layer A + Layer B 파생)
     → generate_ideals (12차원 기반 이상향 3종)
     → chat_design
     → confirm_ideal
     → generate_guide
     → generate_quest
     → build_playlist
     → complete
"""

import json
import os

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from .prompt import (
    CHAT_DESIGN_PROMPT,
    GUIDE_PROMPT,
    IDEAL_DESIGN_PROMPT,
    PLAYLIST_PROMPT,
    SYSTEM_PROMPT,
)
from .schemas import (
    IdealDesignResponse,
    IdealType,
)
from .state import NavigatorState, NavigatorStep
from .tool import (
    compare_radar,
    compute_dominant_weak,
    enrich_quests_with_layer_b,
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
    Layer A 수신 확인 + dominant/weak 런타임 계산 (v1.1)
    Layer B는 Profiler가 산출 — Navigator는 읽기만 함
    """
    if not state.current_radar:
        return {
            "error": "current_radar 데이터가 없습니다. Profiler 에이전트 확인 필요."
        }

    radar = state.current_radar
    dominant, weak = compute_dominant_weak(radar)

    # ── 분석 요약 ──
    scores = radar.to_dict()
    bias_axes = []
    for key, score in scores.items():
        if score < 30:
            bias_axes.append(f"{key.value}({score:.0f}점↓)")
        elif score > 70:
            bias_axes.append(f"{key.value}({score:.0f}점↑)")

    lines = [
        f"【Layer A 분석】 편향 축: {', '.join(bias_axes) if bias_axes else '없음'}",
        f"【dominant】 {', '.join(dominant) or '없음'}",
        f"【weak】 {', '.join(weak) or '없음'}",
    ]
    if state.layer_b:
        lb = state.layer_b
        lines.append(
            f"【Layer B】 주체성={lb.search_active_ratio:.2f} / "
            f"채널편중={lb.viewing_concentration:.2f}(↑나쁨) / "
            f"취향다양성={lb.taste_diversity_index} / "
            f"탐색깊이={lb.exploration_depth:.2f}"
        )

    summary = "\n".join(lines)
    return {
        "current_step": NavigatorStep.ANALYZE_PROFILE,
        "messages": [AIMessage(content=summary)],
    }


def node_generate_ideals(state: NavigatorState) -> dict:
    """
    12차원 기반으로 3가지 이상향 자동 생성 + LLM 소개 메시지
    Layer A 8각 + ProfilerMeta(dominant/weak axes) 반영
    """
    if not state.current_radar:
        return {"error": "current_radar 없음"}

    dominant, weak = compute_dominant_weak(state.current_radar)

    # 이상향 3종 생성 (반대방향형=LLM, 확장/균형=수식)
    proposals = generate_all_ideals(
        state.current_radar,
        dominant,
        weak,
        layer_b=state.layer_b,
        top5_interests=state.top5_interests,
    )

    # LLM으로 소개 메시지
    llm = _get_llm(temperature=0.7)

    indices_json = state.layer_b.model_dump_json() if state.layer_b else "{}"

    prompt = IDEAL_DESIGN_PROMPT.format(
        current_radar=json.dumps(
            {k.value: v for k, v in state.current_radar.to_dict().items()},
            ensure_ascii=False,
        ),
        navigator_indices=indices_json,
        dominant_axes=", ".join(dominant) or "없음",
        weak_axes=", ".join(weak) or "없음",
        top5_interests=", ".join(state.top5_interests),
    )

    response = llm.invoke(
        [
            HumanMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
    )
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
    대화형 이상향 설계 노드 — Layer B 인지주권 4지수 컨텍스트 포함
    """
    llm = _get_llm(temperature=0.8)

    proposals_json = ""
    if state.ideal_proposals:
        proposals_json = json.dumps(
            [
                {k.value: v for k, v in p.to_dict().items()}
                for p in state.ideal_proposals.proposals
            ],
            ensure_ascii=False,
        )

    indices_json = state.layer_b.model_dump_json() if state.layer_b else "{}"

    system = CHAT_DESIGN_PROMPT.format(
        current_radar=json.dumps(
            {k.value: v for k, v in state.current_radar.to_dict().items()}
            if state.current_radar
            else {},
            ensure_ascii=False,
        ),
        navigator_indices=indices_json,
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
    이상향 확정 + Layer A gap 계산
    selected_ideal이 없으면 ADJACENT(인접형) 기본 선택
    """
    if not state.selected_ideal and state.ideal_proposals:
        for p in state.ideal_proposals.proposals:
            if p.ideal_type == IdealType.EXPANSION:
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
    12차원 gap 기반 30일 가이드 생성
    Layer B 주체성 낮으면 알고리즘 OFF 액션 자동 추가
    """
    if not state.comparison:
        return {"error": "comparison 없음"}

    guide = generate_guide(state.comparison, state.top5_interests)

    indices_json = state.layer_b.model_dump_json() if state.layer_b else "{}"

    llm = _get_llm(temperature=0.6)
    prompt = GUIDE_PROMPT.format(
        comparison=json.dumps(
            {
                "gap": {k.value: v for k, v in state.comparison.gap.items()},
                "total_gap": state.comparison.total_gap,
            },
            ensure_ascii=False,
        ),
        navigator_indices=indices_json,
        top5_interests=", ".join(state.top5_interests),
    )

    llm.invoke(
        [
            HumanMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
    )

    guide_message = f"📋 **{guide.title}**\n\n"
    for step in guide.steps:
        guide_message += f"• {step}\n"

    # Layer B 주체성 경고
    if state.layer_b and state.layer_b.search_active_ratio < 0.4:
        guide_message += (
            "\n⚠️ **주체성 지수가 낮습니다.** "
            "홈 피드 대신 검색 탭 사용 습관을 우선 들여보세요."
        )

    return {
        "current_step": NavigatorStep.GENERATE_GUIDE,
        "guide": guide,
        "messages": [AIMessage(content=guide_message)],
    }


def node_generate_quest(state: NavigatorState) -> dict:
    """
    오늘의 퀘스트 3개 생성 + Layer B 가중치 보강
    """
    if not state.comparison:
        return {"error": "comparison 없음"}

    quests = generate_quests(state.comparison, state.top5_interests, count=3)

    # Layer B 기반 보강
    if state.layer_b:
        quests = enrich_quests_with_layer_b(quests, state.layer_b)

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
        ideal_radar=json.dumps(
            {k.value: v for k, v in state.selected_ideal.to_dict().items()},
            ensure_ascii=False,
        ),
        top5_interests=", ".join(state.top5_interests),
    )

    response = llm.invoke(
        [
            HumanMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
    )

    try:
        parsed = _safe_parse_json(response.content)
        playlist_title = parsed.get("playlist_title", "나의 이상향 플레이리스트")
        playlist_description = parsed.get("playlist_description", "")
        search_queries = parsed.get("search_queries", [])
    except (json.JSONDecodeError, ValueError):
        search_queries = [
            {"query": i, "reason": "관심사 기반"} for i in state.top5_interests
        ]
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
        "messages": [
            AIMessage(content="✅ 이상향 설계가 완료되었습니다. 오늘부터 시작해볼까요?")
        ],
    }


# ──────────────────────────────────────────
# 라우팅
# ──────────────────────────────────────────


def route_after_chat(state: NavigatorState) -> str:
    if state.is_ideal_confirmed:
        return "confirm_ideal"
    return "chat_design"


# ──────────────────────────────────────────
# 그래프 빌드
# ──────────────────────────────────────────


def build_navigator_graph() -> StateGraph:
    graph = StateGraph(NavigatorState)

    graph.add_node("analyze_profile", node_analyze_profile)
    graph.add_node("generate_ideals", node_generate_ideals)
    graph.add_node("chat_design", node_chat_design)
    graph.add_node("confirm_ideal", node_confirm_ideal)
    graph.add_node("generate_guide", node_generate_guide)
    graph.add_node("generate_quest", node_generate_quest)
    graph.add_node("build_playlist", node_build_playlist)
    graph.add_node("complete", node_complete)

    graph.add_edge(START, "analyze_profile")
    graph.add_edge("analyze_profile", "generate_ideals")
    graph.add_edge("generate_ideals", "chat_design")

    graph.add_conditional_edges(
        "chat_design",
        route_after_chat,
        {"confirm_ideal": "confirm_ideal", "chat_design": "chat_design"},
    )

    graph.add_edge("confirm_ideal", "generate_guide")
    graph.add_edge("generate_guide", "generate_quest")
    graph.add_edge("generate_quest", "build_playlist")
    graph.add_edge("build_playlist", "complete")
    graph.add_edge("complete", END)

    return graph


_compiled_graph = None


def get_navigator_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_navigator_graph().compile()
    return _compiled_graph
