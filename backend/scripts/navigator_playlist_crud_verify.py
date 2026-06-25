"""[검증] 재생목록 CRUD 서비스 E2E — 실 DB에 임시 이상향 + create/list/get/rename/delete.

실행: cd backend && PYTHONUTF8=1 PYTHONPATH=. uv run python scripts/navigator_playlist_crud_verify.py
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

        # 임시 이상향 생성
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
        ideal_id = persona.id
        print(f"임시 이상향 {ideal_id}")

        try:
            print("\n===== create_playlist =====")
            p1 = await svc.create_playlist(user_id=user_id, ideal_id=ideal_id)
            print(f"  id={p1.id} title='{p1.title}' items={len(p1.items)}")
            print(f"  summary: {p1.summary[:60]}")
            for it in p1.items[:3]:
                print(f"   - {it.title[:40]} | url={it.url[:40]}")

            print("\n===== create 두 번째 =====")
            p2 = await svc.create_playlist(user_id=user_id, ideal_id=ideal_id)
            print(f"  id={p2.id} title='{p2.title}'")

            print("\n===== list_playlists =====")
            lst = await svc.list_playlists(user_id=user_id, ideal_id=ideal_id)
            print(f"  {len(lst)}개: {[(s.title, s.item_count) for s in lst]}")

            print("\n===== get_playlist(p1) =====")
            got = await svc.get_playlist(user_id=user_id, playlist_id=p1.id)
            print(f"  {got.id} title='{got.title}' items={len(got.items)}")

            print("\n===== rename_playlist(p1) =====")
            rn = await svc.rename_playlist(
                user_id=user_id, playlist_id=p1.id, title="내 분석 리스트"
            )
            print(f"  title='{rn.title}'")

            print("\n===== delete_playlist(p2) =====")
            await svc.delete_playlist(user_id=user_id, playlist_id=p2.id)
            lst2 = await svc.list_playlists(user_id=user_id, ideal_id=ideal_id)
            print(f"  남은 {len(lst2)}개: {[s.title for s in lst2]}")

            print("\n===== 판정 =====")
            print(f"  생성 후 목록 2개였나: {'✅' if len(lst) == 2 else '❌'}")
            print(f"  rename 반영: {'✅' if rn.title == '내 분석 리스트' else '❌'}")
            print(f"  delete 후 1개: {'✅' if len(lst2) == 1 else '❌'}")
            print(f"  reservoir/channels 저장: items={len(p1.items)} (행 영속 OK)")
        finally:
            # 정리: 임시 이상향 삭제 → 재생목록 cascade
            await session.delete(persona)
            await session.commit()
            print(f"\n🧹 cleanup: 임시 이상향+재생목록 삭제 ({ideal_id})")


if __name__ == "__main__":
    asyncio.run(main())
