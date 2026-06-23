"""Archiver SSE status — 사용자-facing 스트리밍 안내 문구 SSOT."""

from __future__ import annotations

from app.agents.archiver.models.state import COLLECT_NODE, RAG_NODE, SEARCH_NODE

# ── Router / 병렬 시작 ────────────────────────────────────────────

MSG_ROUTER_GENERAL = "✨ 질문을 확인했습니다. 답변을 준비하고 있어요..."

MSG_ROUTER_RAG_SEARCH = (
    "🧠 과거 기억을 되짚어보며, 동시에 🌐 최신 웹 트렌드까지 함께 검색하고 있습니다..."
)
MSG_ROUTER_DOM_SEARCH = (
    "📄 현재 화면 정보를 읽어오면서, 🌐 관련 최신 정보도 실시간으로 탐색 중입니다..."
)
MSG_ROUTER_DOM_RAG = (
    "📄 현재 페이지의 정보와 🧠 우리가 나눈 이전 대화 흐름을 매칭하여 분석하고 있습니다..."
)
MSG_ROUTER_ALL_CHANNELS = (
    "🚀 현재 화면, 과거 기억, 실시간 웹 검색까지 모든 채널을 동시 가동해 분석 중입니다..."
)

MSG_ROUTER_DOM_ONLY = "📄 현재 페이지의 화면 정보를 읽어 분석을 시작합니다..."
MSG_ROUTER_RAG_ONLY = (
    "🧠 우리가 이전에 나누었던 대화와 관련 기억들을 되짚어보고 있어요..."
)
MSG_ROUTER_SEARCH_ONLY = (
    "🌐 최신 정보와 트렌드를 파악하기 위해 실시간 웹 검색을 진행하고 있습니다..."
)

# ── DOM / collect_node ────────────────────────────────────────────

MSG_DOM_COLLECTING = "📄 현재 열려 있는 탭의 화면 정보를 안전하게 읽어오는 중입니다..."
MSG_DOM_COLLECTED = "✅ 화면 정보 읽기 완료! 내용을 꼼꼼히 분석하고 있습니다..."
MSG_DOM_SCRAPING = (
    "🌐 더 정확한 분석을 위해 웹페이지 전체 데이터를 추가로 불러오는 중입니다..."
)
MSG_DOM_THIN_REVIEW = "📄 화면에서 읽어 온 내용을 더 꼼꼼히 살펴보고 있어요..."

# need_dom (클라이언트 DOM 선행 수집)
MSG_NEED_DOM = "📄 현재 열려 있는 탭의 화면 정보를 안전하게 읽어오는 중입니다..."

# ── RAG / rag_node ────────────────────────────────────────────────

MSG_RAG_FIRST = "🧠 우리가 이전에 나누었던 대화와 관련 기억들을 되짚어보고 있어요..."
MSG_RAG_RETRY = (
    "🔍 질문과 가장 연관성이 높은 소중한 기억을 한 번 더 꼼꼼히 찾는 중입니다..."
)

# ── Search / search_node ──────────────────────────────────────────

MSG_SEARCH_DEFAULT = (
    "🌐 최신 정보와 트렌드를 파악하기 위해 실시간 웹 검색을 진행하고 있습니다..."
)
MSG_SEARCH_TITLE_BASED = (
    "💡 현재 페이지 제목을 바탕으로 유용한 연관 정보를 넓게 탐색하는 중입니다..."
)

# ── Evaluator ─────────────────────────────────────────────────────

MSG_EVALUATOR_SUFFICIENT = (
    "⚖️ 수집된 정보들이 충분한지 꼼꼼하게 검토를 마쳤습니다. 이제 답변을 작성할게요!"
)
MSG_EVALUATOR_SUPPLEMENTING = (
    "⚙️ 완벽한 답변을 위해 부족한 정보를 추가로 보완하는 중입니다..."
)
MSG_EVALUATOR_BEST_EFFORT = (
    "⚖️ 모아 둔 정보를 바탕으로 최선의 답변을 준비하고 있어요..."
)

# ── Respond ───────────────────────────────────────────────────────

MSG_RESPOND_GENERATING = "✨ 답변을 정리해 작성하고 있어요..."


def _normalize_sse_text(text: str) -> str:
    """SSE status content — 항상 이중 줄바꿈으로 끝난다."""
    stripped = text.strip()
    return f"{stripped}\n\n"


def status_event(content: str) -> dict[str, str]:
    """LangGraph stream writer용 status 이벤트 dict."""
    return {"event": "status", "content": _normalize_sse_text(content)}


def need_dom_event() -> dict[str, str]:
    """need_dom SSE 이벤트 dict."""
    return {"event": "need_dom", "content": _normalize_sse_text(MSG_NEED_DOM)}


def router_parallel_message(targets: list[str]) -> str:
    """target_engines 조합에 맞는 통합 멀티태스킹 안내 문구."""
    engine_set = set(targets)
    has_dom = COLLECT_NODE in engine_set
    has_rag = RAG_NODE in engine_set
    has_search = SEARCH_NODE in engine_set

    if has_dom and has_rag and has_search:
        return MSG_ROUTER_ALL_CHANNELS
    if has_rag and has_search and not has_dom:
        return MSG_ROUTER_RAG_SEARCH
    if has_dom and has_search and not has_rag:
        return MSG_ROUTER_DOM_SEARCH
    if has_dom and has_rag and not has_search:
        return MSG_ROUTER_DOM_RAG
    if has_dom:
        return MSG_ROUTER_DOM_ONLY
    if has_rag:
        return MSG_ROUTER_RAG_ONLY
    if has_search:
        return MSG_ROUTER_SEARCH_ONLY
    return MSG_ROUTER_GENERAL


def evaluator_message(evaluation: object) -> str:
    """Evaluation 결과에 따른 사용자-facing 채점 안내."""
    from app.agents.archiver.models import Evaluation

    if not isinstance(evaluation, Evaluation):
        return MSG_EVALUATOR_BEST_EFFORT

    if evaluation.is_sufficient:
        return MSG_EVALUATOR_SUFFICIENT

    if evaluation.normalized_action() != "none":
        return MSG_EVALUATOR_SUPPLEMENTING

    return MSG_EVALUATOR_BEST_EFFORT
