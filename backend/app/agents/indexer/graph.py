from langgraph.graph import END, StateGraph

from app.agents.indexer.nodes import (
    node_embed,
    node_enrich,
    node_preprocess,
    node_save_catalog,
)
from app.agents.indexer.state import IndexerState


def should_continue(state: IndexerState) -> str:
    return "end" if state.get("error") else "continue"


builder = StateGraph(IndexerState)

builder.add_node("preprocess", node_preprocess)
builder.add_node("enrich", node_enrich)
builder.add_node("embed", node_embed)
builder.add_node("save_catalog", node_save_catalog)

builder.set_entry_point("preprocess")

builder.add_conditional_edges(
    "preprocess", should_continue, {"continue": "enrich", "end": END}
)
builder.add_conditional_edges(
    "enrich", should_continue, {"continue": "embed", "end": END}
)
builder.add_conditional_edges(
    "embed", should_continue, {"continue": "save_catalog", "end": END}
)
builder.add_edge("save_catalog", END)

graph = builder.compile()
