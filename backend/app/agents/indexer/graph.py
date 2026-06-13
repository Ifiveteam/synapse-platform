from langgraph.graph import END, StateGraph

from app.agents.indexer.nodes import (
    node_delete,
    node_enrich,
    node_log,
    node_parse,
    node_preprocess,
    node_save,
    node_start,
    node_vectorize,
)
from app.agents.indexer.state import IndexerState


def should_continue(state: IndexerState) -> str:
    return "end" if state.get("error") else "continue"


def should_reindex(state: IndexerState) -> str:
    return "delete" if state.get("reindex") else "parse"


builder = StateGraph(IndexerState)

builder.add_node("start", node_start)
builder.add_node("delete", node_delete)
builder.add_node("parse", node_parse)
builder.add_node("preprocess", node_preprocess)
builder.add_node("enrich", node_enrich)
builder.add_node("vectorize", node_vectorize)
builder.add_node("save", node_save)
builder.add_node("log", node_log)

builder.set_entry_point("start")

builder.add_conditional_edges(
    "start", should_reindex, {"delete": "delete", "parse": "parse"}
)
builder.add_conditional_edges(
    "delete", should_continue, {"continue": "parse", "end": END}
)
builder.add_conditional_edges(
    "parse", should_continue, {"continue": "preprocess", "end": END}
)
builder.add_conditional_edges(
    "preprocess", should_continue, {"continue": "enrich", "end": END}
)
builder.add_conditional_edges(
    "enrich", should_continue, {"continue": "vectorize", "end": END}
)
builder.add_conditional_edges(
    "vectorize", should_continue, {"continue": "save", "end": END}
)
builder.add_edge("save", "log")
builder.add_edge("log", END)

graph = builder.compile()
