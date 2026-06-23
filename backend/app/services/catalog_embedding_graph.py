"""catalog 임베딩 → 코사인 유사도 엣지 (좌표는 FE force layout)."""

from __future__ import annotations

import numpy as np

MAX_EDGES_PER_NODE = 5
MIN_SIMILARITY = 0.60


def build_cosine_capped_edges(
    ids: list[str],
    vectors: list[list[float]],
    *,
    max_per_node: int = MAX_EDGES_PER_NODE,
    min_similarity: float = MIN_SIMILARITY,
) -> list[dict]:
    """유사도 min_similarity 이상 쌍 중, 노드당 최대 max_per_node개만 연결."""
    n = len(ids)
    if n < 2:
        return []

    matrix = np.asarray(vectors, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = matrix / np.clip(norms, 1e-12, None)
    similarity = matrix @ matrix.T

    pairs: list[tuple[float, int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            weight = float(similarity[i, j])
            if weight >= min_similarity:
                pairs.append((weight, i, j))

    pairs.sort(key=lambda item: item[0], reverse=True)

    degree = [0] * n
    edges: list[dict] = []
    for weight, i, j in pairs:
        if degree[i] >= max_per_node or degree[j] >= max_per_node:
            continue
        left, right = ids[i], ids[j]
        if left > right:
            left, right = right, left
        edges.append(
            {
                "source": left,
                "target": right,
                "similarity": round(weight, 4),
            }
        )
        degree[i] += 1
        degree[j] += 1

    return edges


def _is_classified_row(row: dict) -> bool:
    cat = row.get("youtube_category_id")
    if cat is None:
        return False
    text = str(cat).strip()
    return bool(text) and text.lower() != "unknown"


def build_embedding_graph_payload(rows: list[dict]) -> dict:
    """노드 + 유사도 엣지 반환. 2D 좌표는 클라이언트 force layout."""
    with_vectors = [
        row for row in rows if row.get("embedding") and _is_classified_row(row)
    ]
    if not with_vectors:
        return {
            "total": 0,
            "method": "force",
            "layout": "force",
            "max_edges_per_node": MAX_EDGES_PER_NODE,
            "min_similarity": MIN_SIMILARITY,
            "nodes": [],
            "edges": [],
        }

    vectors = [row["embedding"] for row in with_vectors]
    ids = [str(row["id"]) for row in with_vectors]
    edges = build_cosine_capped_edges(ids, vectors)

    nodes = [
        {
            "id": str(row["id"]),
            "title": row.get("title") or "",
            "channel": row.get("channel") or "",
            "category_id": str(row.get("youtube_category_id")),
            "is_shorts": bool(row.get("is_shorts")),
        }
        for row in with_vectors
    ]

    return {
        "total": len(nodes),
        "method": "force",
        "layout": "force",
        "max_edges_per_node": MAX_EDGES_PER_NODE,
        "min_similarity": MIN_SIMILARITY,
        "nodes": nodes,
        "edges": edges,
    }
