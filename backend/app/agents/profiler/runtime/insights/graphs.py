"""Taste and knowledge graph builders for profile visualization."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

from app.agents.profiler.base import (
    SYNAPSE_AXIS_KEYS,
    GraphEdge,
    GraphNode,
    GraphViewData,
    IndexedRecord,
    ProfilerResult,
)
from app.agents.profiler.subagent.scoring import (
    TAG_AXIS_WEIGHTS,
    filter_search_records,
    filter_watch_records,
    trail_from_search,
)


def _undirected_key(a: str, b: str, relation: str) -> tuple[str, str, str]:
    if a <= b:
        return (a, b, relation)
    return (b, a, relation)


def _finalize_edges(
    edges: Counter[tuple[str, str, str]],
    nodes: dict[str, GraphNode],
) -> list[GraphEdge]:
    return [
        GraphEdge(
            source=src,
            target=tgt,
            weight=float(weight),
            relation=rel,
            directed=False,
        )
        for (src, tgt, rel), weight in edges.items()
        if src in nodes and tgt in nodes
    ]


def build_taste_graph(
    records: list[IndexedRecord],
    result: ProfilerResult | None = None,
) -> GraphViewData:
    nodes: dict[str, GraphNode] = {}
    edges: Counter[tuple[str, str, str]] = Counter()

    tag_weight: Counter[str] = Counter()
    channel_weight: Counter[str] = Counter()

    for record in records:
        for tag in record.tags:
            weight = record.duration_sec or 30 if record.source_type == "watch" else 20
            tag_weight[tag] += weight
            node_id = f"tag:{tag}"
            nodes[node_id] = GraphNode(
                id=node_id,
                type="tag",
                label=tag,
                weight=float(tag_weight[tag]),
            )
        if record.source_type == "watch" and record.tags and record.channel:
            channel_weight[record.channel] += record.duration_sec or 60
            ch_id = f"channel:{record.channel}"
            nodes[ch_id] = GraphNode(
                id=ch_id,
                type="channel",
                label=record.channel,
                weight=float(channel_weight[record.channel]),
            )
            for tag in record.tags:
                edge_key = _undirected_key(ch_id, f"tag:{tag}", "watch")
                edges[edge_key] += record.duration_sec or 60

        if len(record.tags) >= 2:
            for a, b in combinations(sorted(record.tags), 2):
                edge_key = _undirected_key(f"tag:{a}", f"tag:{b}", "co_occur")
                edges[edge_key] += 1

    if result is not None:
        for key in SYNAPSE_AXIS_KEYS:
            score = float(getattr(result.axes, key))
            axis_id = f"axis:{key}"
            nodes[axis_id] = GraphNode(
                id=axis_id,
                type="axis",
                label=key,
                weight=score,
            )

        for node in list(nodes.values()):
            if node.type != "tag":
                continue
            tag_name = node.label
            axis_weights = TAG_AXIS_WEIGHTS.get(tag_name, {})
            for axis_key, mapping in axis_weights.items():
                if mapping <= 0:
                    continue
                edge_key = _undirected_key(f"axis:{axis_key}", node.id, "maps_to")
                edges[edge_key] += node.weight * mapping

    return GraphViewData(
        kind="taste",
        nodes=list(nodes.values()),
        edges=_finalize_edges(edges, nodes),
    )


def build_knowledge_graph(records: list[IndexedRecord]) -> GraphViewData:
    nodes: dict[str, GraphNode] = {}
    edges: Counter[tuple[str, str, str]] = Counter()

    tag_weight: Counter[str] = Counter()
    for record in records:
        base = 30 if record.source_type == "search" else (record.duration_sec or 45)
        for tag in record.tags:
            tag_weight[tag] += base
            node_id = f"domain:{tag}"
            nodes[node_id] = GraphNode(
                id=node_id,
                type="domain",
                label=tag,
                weight=float(tag_weight[tag]),
            )
        if len(record.tags) >= 2:
            for a, b in combinations(sorted(record.tags), 2):
                edge_key = _undirected_key(f"domain:{a}", f"domain:{b}", "same_content")
                edges[edge_key] += 1

    searches = filter_search_records(records)
    watches = filter_watch_records(records)
    for search in searches:
        if not search.tags:
            continue
        trail = trail_from_search(search, watches)
        for watch in trail:
            for s_tag in search.tags:
                for w_tag in watch.tags:
                    edge_key = _undirected_key(
                        f"domain:{s_tag}",
                        f"domain:{w_tag}",
                        "related",
                    )
                    edges[edge_key] += 1

    return GraphViewData(
        kind="knowledge",
        nodes=list(nodes.values()),
        edges=_finalize_edges(edges, nodes),
    )
