"""[검증] YouTube 재생목록 서브에이전트 — 실 DB 유저 + 실 store로 생성.

generate_playlist(store=repo) 가 실재 영상 10개를 시청기록 근거+이상향으로 뽑고,
watched 제외·자기교정 루프가 도는지 확인.
실행: cd backend && PYTHONUTF8=1 PYTHONPATH=. uv run python scripts/navigator_youtube_playlist_verify.py
"""

import asyncio

from app.core.env import load_backend_env

load_backend_env()

from sqlalchemy import select  # noqa: E402

from app.agents.navigator import get_navigator_agent  # noqa: E402
from app.core.database.session import AsyncSessionLocal  # noqa: E402
from app.models.user_watch_catalog import UserWatchCatalog  # noqa: E402
from app.repositories.navigator_repository import NavigatorRepository  # noqa: E402

# 분석형 이상향 페르소나 (13축)
VALUES13 = {
    "self_direction": 85,
    "stimulation": 55,
    "achievement": 70,
    "power": 30,
    "security": 45,
    "benevolence": 60,
    "universalism": 80,
    "hedonism": 35,
    "conformity": 30,
    "tradition": 25,
    "novelty_seeking": 80,
    "persistence": 78,
    "self_transcendence": 65,
}
REASONING = "데이터와 논리로 세상을 깊이 파고들고, 표면적 재미보다 '왜'를 따지는 사람."


async def main() -> None:
    async with AsyncSessionLocal() as session:
        user_id = (
            await session.execute(select(UserWatchCatalog.user_id).limit(1))
        ).scalar_one()
        repo = NavigatorRepository(session)

        print(f"===== 대상 유저 {user_id} =====")
        g = await repo.fetch_watch_grounding(user_id)
        watched = await repo.fetch_watched_video_ids(user_id)
        print(f"  카테고리: {g.categories}")
        print(f"  채널: {g.channels[:5]}")
        print(f"  대표 영상: {g.sample_titles[:3]}")
        print(f"  watched video_ids: {len(watched)}개")

        print("\n===== generate_playlist (store=repo) =====")
        agent = get_navigator_agent()
        build = await agent.generate_playlist(
            store=repo,
            user_id=user_id,
            persona_label="분석적인 탐구가",
            values13=VALUES13,
            ideal_type="BALANCE",
            reasoning=REASONING,
        )
        pl = build.playlist
        print(f"요약: {pl.summary}")
        for i, it in enumerate(pl.items, 1):
            in_w = "⚠️watched" if it.video_id in watched else "✅"
            vid_ok = "" if len(it.video_id) == 11 else " (id 길이 이상!)"
            print(
                f"  {i:2}. {in_w} [{it.video_id}{vid_ok}] {it.title[:42]} · {it.channel}"
            )
            print(f"       이유: {it.reason[:70]}")

        print(f"\n  저수지(reservoir): {len(build.reservoir)}개")
        print(f"  발굴 채널(channels): {len(build.channels)}개")

        print("\n===== 판정 =====")
        ids = [it.video_id for it in pl.items]
        print(
            f"  영상 수 ≤10: {'✅' if len(pl.items) <= 10 else '❌'} ({len(pl.items)})"
        )
        print(
            f"  모든 video_id 11자: {'✅' if all(len(v) == 11 for v in ids) else '❌'}"
        )
        print(f"  watched 제외: {'✅' if not (set(ids) & watched) else '❌'}")
        print(f"  중복 없음: {'✅' if len(ids) == len(set(ids)) else '❌'}")


if __name__ == "__main__":
    asyncio.run(main())
