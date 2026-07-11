"""트렌드 키워드 임베딩 캐시 — 조회·ON CONFLICT upsert."""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.shared.embedding import EMBEDDING_MODEL
from app.models.trend_keyword_embedding import TrendKeywordEmbedding


async def fetch_by_embedding_texts(
    session: AsyncSession,
    texts: Sequence[str],
) -> dict[str, list[float]]:
    """embedding_text 목록에 대한 캐시 hit 맵을 반환한다.

    Returns:
        ``{embedding_text: embedding_vector}`` — miss는 키 자체 없음.
    """
    cleaned = [text.strip() for text in texts if text and str(text).strip()]
    if not cleaned:
        return {}

    # 동일 텍스트 중복 요청 제거 (IN 절 축소)
    unique_texts = list(dict.fromkeys(cleaned))
    result = await session.execute(
        select(TrendKeywordEmbedding).where(
            TrendKeywordEmbedding.embedding_text.in_(unique_texts)
        )
    )
    rows = result.scalars().all()
    out: dict[str, list[float]] = {}
    for row in rows:
        vector = row.embedding
        out[row.embedding_text] = (
            list(vector) if not isinstance(vector, list) else vector
        )
    return out


async def upsert_many(
    session: AsyncSession,
    rows: Sequence[dict[str, Any]],
) -> int:
    """힌트 결합 임베딩을 일괄 적재한다.

    ``uq_tke_embedding_text`` 충돌 시:
    - embedding / hint 메타 / model 을 EXCLUDED 값으로 갱신
    - ``updated_at`` 을 now() 로 갱신

    배치 재실행·동시성 상황에서 UniqueViolation 없이 안전하다.
    """
    if not rows:
        return 0

    values: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    for row in rows:
        embedding_text = str(row.get("embedding_text", "")).strip()
        if not embedding_text or embedding_text in seen_texts:
            continue
        embedding = row.get("embedding")
        if embedding is None:
            continue
        seen_texts.add(embedding_text)
        values.append(
            {
                "keyword": str(row.get("keyword", "")).strip()[:256],
                "hint_source": str(row.get("hint_source", "mixed")).strip()[:32],
                "hint_domain": str(row.get("hint_domain", "Tech/Business")).strip()[
                    :64
                ],
                "embedding_text": embedding_text,
                "embedding": list(embedding),
                "model": str(row.get("model") or EMBEDDING_MODEL)[:64],
            }
        )

    if not values:
        return 0

    stmt = pg_insert(TrendKeywordEmbedding).values(values)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_tke_embedding_text",
        set_={
            "keyword": stmt.excluded.keyword,
            "hint_source": stmt.excluded.hint_source,
            "hint_domain": stmt.excluded.hint_domain,
            "embedding": stmt.excluded.embedding,
            "model": stmt.excluded.model,
            "updated_at": func.now(),
        },
    )
    await session.execute(stmt)
    return len(values)
