import time

from langgraph.graph import END, StateGraph

from app.agents.indexer.prompt import classify_batch
from app.agents.indexer.state import IndexerState
from app.agents.indexer.tool import add_keywords, parse_takeout_json, parse_takeout_zip, preprocess, vectorize


def node_parse(state: IndexerState) -> IndexerState:
    """노드 1: ZIP 또는 JSON 파싱"""
    try:
        path = state["json_path"]
        raw_data = parse_takeout_zip(path) if path.endswith(".zip") else parse_takeout_json(path)
        return {**state, "raw_data": raw_data, "error": None}
    except Exception as e:
        return {**state, "raw_data": [], "error": str(e)}


def node_preprocess(state: IndexerState) -> IndexerState:
    """노드 2: 전처리"""
    try:
        cleaned_data = preprocess(state["raw_data"])
        return {**state, "cleaned_data": cleaned_data, "filtered_count": len(cleaned_data), "error": None}
    except Exception as e:
        return {**state, "cleaned_data": [], "filtered_count": 0, "error": str(e)}


def node_classify(state: IndexerState) -> IndexerState:
    """노드 3: 카테고리 분류"""
    try:
        limit = state.get("limit", 100)
        cleaned_data = state["cleaned_data"][:limit]
        batch_size = 20
        result = []

        for i in range(0, len(cleaned_data), batch_size):
            batch = cleaned_data[i : i + batch_size]
            titles = [item["title"] for item in batch]
            categories = classify_batch(titles)

            for item, category in zip(batch, categories, strict=False):
                result.append({**item, "category": category})

            total = len(cleaned_data)
            done = min(i + batch_size, total)
            print(f"분류 진행중... {done}/{total}")

        return {**state, "cleaned_data": result, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}


def node_keywords(state: IndexerState) -> IndexerState:
    """노드 4: 키워드 추출"""
    try:
        data_with_keywords = add_keywords(state["cleaned_data"])
        return {**state, "cleaned_data": data_with_keywords, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}


def node_vectorize(state: IndexerState) -> IndexerState:
    """노드 5: 벡터화"""
    try:
        vectorized_data = vectorize(state["cleaned_data"])
        return {**state, "cleaned_data": vectorized_data, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}


async def node_save(state: IndexerState) -> IndexerState:
    """노드 6: DB 저장"""
    try:
        from app.agents.indexer.repository import save_vectors
        from app.core.database.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            await save_vectors(state["cleaned_data"], session)
        return {**state, "saved_count": len(state["cleaned_data"]), "error": None}
    except Exception as e:
        return {**state, "saved_count": 0, "error": str(e)}


def should_continue(state: IndexerState) -> str:
    """에러 있으면 종료"""
    if state.get("error"):
        return "end"
    return "continue"


builder = StateGraph(IndexerState)

builder.add_node("parse", node_parse)
builder.add_node("preprocess", node_preprocess)
builder.add_node("classify", node_classify)
builder.add_node("keywords", node_keywords)
builder.add_node("vectorize", node_vectorize)
builder.add_node("save", node_save)

builder.set_entry_point("parse")

builder.add_conditional_edges(
    "parse", should_continue, {"continue": "preprocess", "end": END}
)
builder.add_conditional_edges(
    "preprocess", should_continue, {"continue": "classify", "end": END}
)
builder.add_conditional_edges(
    "classify", should_continue, {"continue": "keywords", "end": END}
)
builder.add_conditional_edges(
    "keywords", should_continue, {"continue": "vectorize", "end": END}
)
builder.add_conditional_edges(
    "vectorize", should_continue, {"continue": "save", "end": END}
)

builder.add_edge("save", END)

graph = builder.compile()