import time

from app.agents.indexer.state import IndexerState
from app.agents.indexer.tool import vectorize


async def node_delete(state: IndexerState) -> IndexerState:
    """재분석 시 해당 유저의 기존 데이터 삭제"""
    try:
        from sqlalchemy import delete as sa_delete

        from app.core.database.session import AsyncSessionLocal
        from app.models.video_vector import VideoVector

        async with AsyncSessionLocal() as session:
            stmt = sa_delete(VideoVector)
            if state.get("user_id"):
                stmt = stmt.where(VideoVector.user_id == state["user_id"])
            await session.execute(stmt)
            await session.commit()
        return {**state, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}


def node_vectorize(state: IndexerState) -> IndexerState:
    try:
        return {
            **state,
            "cleaned_data": vectorize(state["cleaned_data"]),
            "error": None,
        }
    except Exception as e:
        return {**state, "error": str(e)}


async def node_save(state: IndexerState) -> IndexerState:
    try:
        from app.agents.indexer.repository import save_vectors
        from app.core.database.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            await save_vectors(
                state["cleaned_data"], session, user_id=state.get("user_id")
            )
        return {**state, "saved_count": len(state["cleaned_data"]), "error": None}
    except Exception as e:
        return {**state, "saved_count": 0, "error": str(e)}


def node_log(state: IndexerState) -> IndexerState:
    elapsed = time.time() - (state.get("started_at") or time.time())
    saved = state.get("saved_count") or 0
    filtered = state.get("filtered_count") or 0
    raw_total = len(state.get("raw_data") or [])

    cleaned = state.get("cleaned_data") or []
    shorts_count = sum(1 for item in cleaned if item.get("is_shorts"))
    url_shorts = sum(1 for item in cleaned if "/shorts/" in item.get("url", ""))
    has_keywords = sum(1 for item in cleaned if item.get("keywords"))

    lines = [
        "=" * 50,
        "[Indexer] 파이프라인 완료",
        f"  원본 파싱:    {raw_total:,}건",
        f"  전처리 후:    {filtered:,}건",
        f"  DB 저장:      {saved:,}건",
        f"  숏츠:         {shorts_count:,}건 (URL기반: {url_shorts:,}건)",
        f"  키워드 있음:  {has_keywords:,}건 / {len(cleaned):,}건",
        f"  소요시간:     {elapsed:.1f}s",
    ]

    anomalies = []
    if state.get("error"):
        anomalies.append(f"  [이상] 에러 발생: {state['error']}")
    if saved < 10 and not state.get("error"):
        anomalies.append(f"  [이상] 저장 건수 비정상적으로 낮음 ({saved}건)")
    if raw_total > 0 and saved < raw_total * 0.01:
        anomalies.append(f"  [이상] 저장률 1% 미만 ({saved}/{filtered})")

    if anomalies:
        lines.append("[이상 탐지]")
        lines.extend(anomalies)

    lines.append("=" * 50)
    run_log = "\n".join(lines)
    print(run_log)
    return {**state, "run_log": run_log}
