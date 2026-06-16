from langgraph.graph import END, StateGraph

from app.agents.indexer.prompt import classify_batch, extract_keywords_batch
from app.agents.indexer.state import ExtensionState
from app.agents.indexer.tool import get_video_info


async def node_noise_filter(state: ExtensionState) -> ExtensionState:
    """노드 1: 노이즈 필터링 — 쇼츠 제외, 중복 제거"""
    from app.core.database.session import AsyncSessionLocal
    from app.repositories.indexer_repository import is_duplicate

    filtered = []
    async with AsyncSessionLocal() as session:
        for v in state["videos"]:
            if not v.get("is_shorts") and v.get("duration", 999) < 60:
                continue
            if await is_duplicate(v["url"], session):
                continue
            filtered.append(v)
    return {**state, "cleaned_data": filtered, "error": None}


def node_keywords(state: ExtensionState) -> ExtensionState:
    """노드 2: YouTube API로 description 수집 + 키워드 추출"""
    try:
        data = state["cleaned_data"]
        texts = []
        enriched = []
        for item in data:
            info = get_video_info(item.get("url", ""))
            description = info.get("description") or ""
            text = item["title"]
            if description:
                text += " " + description
            texts.append(text)
            enriched.append({**item, "description": description})

        keywords_list = extract_keywords_batch(texts)
        result = [
            {**item, "keywords": kw}
            for item, kw in zip(enriched, keywords_list, strict=False)
        ]
        return {**state, "cleaned_data": result, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}


def node_classify(state: ExtensionState) -> ExtensionState:
    """노드 3: 카테고리 분류 (제목 + description)"""
    try:
        data = state["cleaned_data"]
        texts = []
        for item in data:
            text = item["title"]
            if item.get("description"):
                text += " " + item["description"]
            texts.append(text)
        categories = classify_batch(texts)
        result = [
            {**item, "category": cat}
            for item, cat in zip(data, categories, strict=False)
        ]
        return {**state, "cleaned_data": result, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}


async def node_save(state: ExtensionState) -> ExtensionState:
    """노드 5: DB 저장"""
    try:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.indexer_repository import save_vectors

        async with AsyncSessionLocal() as session:
            await save_vectors(state["cleaned_data"], session)
        return {**state, "saved_count": len(state["cleaned_data"]), "error": None}
    except Exception as e:
        return {**state, "saved_count": 0, "error": str(e)}


def should_continue(state: ExtensionState) -> str:
    if state.get("error"):
        return "end"
    if not state.get("cleaned_data"):
        return "end"
    return "continue"


builder = StateGraph(ExtensionState)

builder.add_node("noise_filter", node_noise_filter)
builder.add_node("keywords", node_keywords)
builder.add_node("classify", node_classify)
builder.add_node("save", node_save)

builder.set_entry_point("noise_filter")

builder.add_conditional_edges(
    "noise_filter", should_continue, {"continue": "keywords", "end": END}
)
builder.add_conditional_edges(
    "keywords", should_continue, {"continue": "classify", "end": END}
)
builder.add_conditional_edges(
    "classify", should_continue, {"continue": "save", "end": END}
)
builder.add_edge("save", END)

extension_graph = builder.compile()
