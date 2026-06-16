from langgraph.graph import END, StateGraph

from app.agents.indexer.nodes import (
    node_classify,
    node_delete,
    node_heavy_enrich,
    node_light_enrich,
    node_log,
    node_parse,
    node_preprocess,
    node_sample,
    node_save,
    node_snapshot,
    node_start,
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
builder.add_node("light_enrich", node_light_enrich)
builder.add_node("classify", node_classify)
builder.add_node("snapshot", node_snapshot)
builder.add_node("sample", node_sample)
builder.add_node("heavy_enrich", node_heavy_enrich)
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
    "preprocess", should_continue, {"continue": "light_enrich", "end": END}
)
builder.add_conditional_edges(
    "light_enrich", should_continue, {"continue": "classify", "end": END}
)
builder.add_conditional_edges(
    "classify", should_continue, {"continue": "snapshot", "end": END}
)
builder.add_conditional_edges(
    "snapshot", should_continue, {"continue": "sample", "end": END}
)
builder.add_conditional_edges(
    "sample", should_continue, {"continue": "heavy_enrich", "end": END}
)
builder.add_conditional_edges(
    "heavy_enrich", should_continue, {"continue": "save", "end": END}
)
builder.add_edge("save", "log")
builder.add_edge("log", END)

graph = builder.compile()
