"""[검증] 재생목록 영상 새로고침(교체) — 생성 → item[0] 교체 → 변경 확인.

실행: cd backend && PYTHONUTF8=1 PYTHONPATH=. uv run python scripts/navigator_playlist_refresh_verify.py
"""

import asyncio

from app.core.env import load_backend_env

load_backend_env()

from sqlalchemy import select  # noqa: E402

from app.agents.navigator.facade import get_navigator_agent  # noqa: E402
from app.core.database.session import AsyncSessionLocal  # noqa: E402
from app.models.user_watch_catalog import UserWatchCatalog  # noqa: E402
from app.repositories.navigator_repository import NavigatorRepository  # noqa: E402
from app.services.navigator.service import NavigatorService  # noqa: E402

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


async def main() -> None:
    async with AsyncSessionLocal() as session:
        user_id = (
            await session.execute(select(UserWatchCatalog.user_id).limit(1))
        ).scalar_one()
        repo = NavigatorRepository(session)
        svc = NavigatorService(db=session, agent=get_navigator_agent())
        persona = await repo.create_ideal(
            user_id=user_id,
            scores8={
                a: 50.0
                for a in [
                    "exploration",
                    "analytical",
                    "creativity",
                    "execution",
                    "achievement_drive",
                    "autonomy",
                    "sociality",
                    "sensitivity",
                ]
            },
            ideal_type="BALANCE",
            reasoning="데이터와 논리로 깊이 파고드는 분석형",
            persona_label="분석적인 탐구가",
            values_temperament=VALUES13,
        )
        try:
            p = await svc.create_playlist(user_id=user_id, ideal_id=persona.id)
            target = p.items[0]
            print(f"교체 전 [0]: {target.title[:40]} ({target.video_id})")
            before_ids = [it.video_id for it in p.items]

            updated = await svc.refresh_item(
                user_id=user_id, playlist_id=p.id, video_id=target.video_id
            )
            after_ids = [it.video_id for it in updated.items]
            new0 = updated.items[0]
            print(f"교체 후 [0]: {new0.title[:40]} ({new0.video_id})")

            print("\n===== 판정 =====")
            print(f"  [0] 교체됨: {'✅' if new0.video_id != target.video_id else '❌'}")
            print(
                f"  타깃 video_id 사라짐: {'✅' if target.video_id not in after_ids else '❌'}"
            )
            print(
                f"  영상 수 유지(10): {'✅' if len(after_ids) == len(before_ids) else '❌'}"
            )
            print(
                f"  나머지 9개 유지: {'✅' if set(before_ids) - {target.video_id} <= set(after_ids) else '❌'}"
            )
            print(
                f"  중복 없음: {'✅' if len(after_ids) == len(set(after_ids)) else '❌'}"
            )
        finally:
            await session.delete(persona)
            await session.commit()
            print(f"\n🧹 cleanup ({persona.id})")


if __name__ == "__main__":
    asyncio.run(main())
