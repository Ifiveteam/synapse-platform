"""[검증] 재생목록 전체 재생성 — 생성 → regenerate → 같은 행 갱신 확인.

실행: cd backend && PYTHONUTF8=1 PYTHONPATH=. uv run python scripts/navigator_playlist_regenerate_verify.py
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
            before = [it.video_id for it in p.items]
            print(f"생성: id={p.id} 영상 {len(before)}개")

            r = await svc.regenerate_playlist(user_id=user_id, playlist_id=p.id)
            after = [it.video_id for it in r.items]
            changed = len(set(before) - set(after))
            print(f"재생성: id={r.id} 영상 {len(after)}개, 바뀐 영상 {changed}개")

            print("\n===== 판정 =====")
            print(f"  같은 재생목록 행: {'✅' if r.id == p.id else '❌'}")
            print(f"  영상 10개: {'✅' if len(after) == 10 else '❌'}")
            print(
                f"  모든 11자 video_id: {'✅' if all(len(v) == 11 for v in after) else '❌'}"
            )
            print(f"  중복 없음: {'✅' if len(after) == len(set(after)) else '❌'}")
            print(f"  내용 갱신됨: {'✅' if changed > 0 else '⚠️ 동일(후보 부족 가능)'}")
        finally:
            await session.delete(persona)
            await session.commit()
            print(f"\n🧹 cleanup ({persona.id})")


if __name__ == "__main__":
    asyncio.run(main())
