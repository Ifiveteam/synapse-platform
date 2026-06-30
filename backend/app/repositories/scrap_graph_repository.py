"""스크랩 그래프용 pgvector 조회 레포지토리."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import String, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession


class ScrapGraphRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def fetch_graph_nodes(
        self,
        *,
        user_id: uuid.UUID,
        categories: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """임베딩이 있는 스크랩 노드를 유저 스코프로 조회한다."""
        conditions = [
            "s.user_id = :user_id",
            "e.embedding IS NOT NULL",
        ]
        params: dict[str, Any] = {"user_id": user_id}

        if categories:
            conditions.append("s.category = ANY(:categories)")
            params["categories"] = categories

        if tags:
            conditions.append("s.tags ?| :tags")
            params["tags"] = tags

        where_clause = " AND ".join(conditions)
        stmt = text(
            f"""
            SELECT
                s.id,
                s.title,
                s.category,
                s.tags
            FROM scraps s
            INNER JOIN scrap_embeddings e ON e.scrap_id = s.id
            WHERE {where_clause}
            ORDER BY s.created_at DESC
            """
        )

        if categories:
            stmt = stmt.bindparams(bindparam("categories", type_=ARRAY(String)))
        if tags:
            stmt = stmt.bindparams(bindparam("tags", type_=ARRAY(String)))

        result = await self.db.execute(stmt, params)
        rows = result.mappings().all()
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "category": row["category"],
                "tags": list(row["tags"] or []),
            }
            for row in rows
        ]

    async def fetch_graph_links(
        self,
        *,
        user_id: uuid.UUID,
        categories: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """필터된 스크랩 쌍의 코사인 유사도를 pgvector로 계산한다."""
        conditions = [
            "s1.user_id = :user_id",
            "s2.user_id = :user_id",
            "e1.embedding IS NOT NULL",
            "e2.embedding IS NOT NULL",
        ]
        params: dict[str, Any] = {"user_id": user_id}

        if categories:
            conditions.append("s1.category = ANY(:categories)")
            conditions.append("s2.category = ANY(:categories)")
            params["categories"] = categories

        if tags:
            conditions.append("s1.tags ?| :tags")
            conditions.append("s2.tags ?| :tags")
            params["tags"] = tags

        where_clause = " AND ".join(conditions)
        stmt = text(
            f"""
            SELECT
                s1.id AS source,
                s2.id AS target,
                1 - (e1.embedding <=> e2.embedding) AS similarity
            FROM scraps s1
            INNER JOIN scrap_embeddings e1 ON e1.scrap_id = s1.id
            INNER JOIN scraps s2 ON s2.id > s1.id
            INNER JOIN scrap_embeddings e2 ON e2.scrap_id = s2.id
            WHERE {where_clause}
            ORDER BY similarity DESC
            """
        )

        if categories:
            stmt = stmt.bindparams(bindparam("categories", type_=ARRAY(String)))
        if tags:
            stmt = stmt.bindparams(bindparam("tags", type_=ARRAY(String)))

        result = await self.db.execute(stmt, params)
        rows = result.mappings().all()
        return [
            {
                "source": row["source"],
                "target": row["target"],
                "similarity": round(float(row["similarity"]), 4),
            }
            for row in rows
        ]
