import time

from app.agents.indexer.state import IndexerState


async def node_delete(state: IndexerState) -> IndexerState:
    """재분석 시 해당 유저의 기존 데이터 삭제"""
    try:
        from sqlalchemy import delete as sa_delete

        from app.core.database.session import AsyncSessionLocal
        from app.models.user_feature_snapshot import UserFeatureSnapshot
        from app.models.user_video_watch import UserVideoWatch

        async with AsyncSessionLocal() as session:
            user_id = state.get("user_id")
            if user_id is None:
                return {**state, "error": "user_id is required for reindex delete"}
            await session.execute(
                sa_delete(UserFeatureSnapshot).where(
                    UserFeatureSnapshot.user_id == user_id
                )
            )
            await session.execute(
                sa_delete(UserVideoWatch).where(UserVideoWatch.user_id == user_id)
            )
            await session.commit()
        return {**state, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}


async def node_snapshot(state: IndexerState) -> IndexerState:
    """2개월 전체 기준 user_feature_snapshot 저장."""
    try:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.indexer_repository import (
            parse_watched_at,
            upsert_feature_snapshot,
        )

        user_id = state.get("user_id")
        if user_id is None:
            return {**state, "error": "user_id is required for snapshot save"}

        analysis_start = parse_watched_at(state.get("analysis_start"))
        analysis_end = parse_watched_at(state.get("analysis_end"))

        async with AsyncSessionLocal() as session:
            await upsert_feature_snapshot(
                session,
                user_id,
                state["cleaned_data"],
                analysis_start,
                analysis_end,
            )
            await session.commit()
        return {**state, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}


async def node_save(state: IndexerState) -> IndexerState:
    """샘플 영상만 user_video_watch 저장."""
    try:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.indexer_repository import save_watch_records

        user_id = state.get("user_id")
        if user_id is None:
            return {**state, "error": "user_id is required for watch save"}

        samples = state.get("sampled_data") or []
        async with AsyncSessionLocal() as session:
            await save_watch_records(session, user_id, samples)
            await session.commit()
        return {**state, "saved_count": len(samples), "error": None}
    except Exception as e:
        return {**state, "saved_count": 0, "error": str(e)}


def node_log(state: IndexerState) -> IndexerState:
    elapsed = time.time() - (state.get("started_at") or time.time())
    saved = state.get("saved_count") or 0
    filtered = state.get("filtered_count") or 0
    sample_count = state.get("sample_count") or 0
    raw_total = len(state.get("raw_data") or [])

    cleaned = state.get("cleaned_data") or []
    shorts_count = sum(1 for item in cleaned if item.get("is_shorts"))
    url_shorts = sum(1 for item in cleaned if "/shorts/" in item.get("url", ""))
    has_keywords = sum(1 for item in cleaned if item.get("keywords"))

    lines = [
        "=" * 50,
        "[Indexer] 파이프라인 완료",
        f"  원본 파싱:    {raw_total:,}건",
        f"  2개월 필터:   {filtered:,}건",
        f"  스냅샷 기준:  {filtered:,}건 (전체)",
        f"  샘플 선정:    {sample_count:,}건",
        f"  DB 저장:      {saved:,}건 (watch)",
        f"  숏츠:         {shorts_count:,}건 (URL기반: {url_shorts:,}건)",
        f"  키워드 있음:  {has_keywords:,}건 / {len(cleaned):,}건",
        f"  소요시간:     {elapsed:.1f}s",
    ]

    anomalies = []
    if state.get("error"):
        anomalies.append(f"  [이상] 에러 발생: {state['error']}")
    if filtered > 0 and saved == 0 and not state.get("error"):
        anomalies.append("  [이상] 샘플 저장 0건")
    if raw_total > 0 and filtered < raw_total * 0.01:
        anomalies.append(
            f"  [이상] 2개월 필터 후 건수 매우 적음 ({filtered}/{raw_total})"
        )

    if anomalies:
        lines.append("[이상 탐지]")
        lines.extend(anomalies)

    lines.append("=" * 50)
    run_log = "\n".join(lines)
    print(run_log)
    return {**state, "run_log": run_log}
