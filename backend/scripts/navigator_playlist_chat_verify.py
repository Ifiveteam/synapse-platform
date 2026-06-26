"""[검증] 재생목록 채팅 부분수정(SSE) — 생성 → 채팅 요청 → status·최종목록 확인.

실행: cd backend && PYTHONUTF8=1 PYTHONPATH=. uv run python scripts/navigator_playlist_chat_verify.py
"""

import asyncio
import json

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
MESSAGE = "이 중 두 개를 운동·헬스 관련 영상으로 바꿔줘"


def _parse_sse(frames: list[str]):
    status, final = [], None
    for f in frames:
        if "event: status" in f:
            data = f.split("data: ", 1)[1].strip()
            status.append(json.loads(data)["content"])
        elif "event: playlist" in f:
            # SSE 컨벤션: data={"content": "<JSON 문자열>"} → 이중 언랩
            content = json.loads(f.split("data: ", 1)[1].strip())["content"]
            final = json.loads(content)
    return status, final


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
            print(f"생성: {len(before)}개")

            print(f"\n채팅 요청: '{MESSAGE}'")
            frames = [
                frame
                async for frame in svc.chat_edit(
                    user_id=user_id, playlist_id=p.id, message=MESSAGE
                )
            ]
            status, final = _parse_sse(frames)
            print("status 이벤트:")
            for s in status:
                print(f"   - {s}")
            if final is None:
                print("❌ 최종 playlist 이벤트 없음")
                return
            after = [it["video_id"] for it in final["items"]]
            changed = set(before) - set(after)
            added = set(after) - set(before)
            print(f"\n바뀐 영상 {len(changed)}개 → 새 영상 {len(added)}개")
            for it in final["items"]:
                mark = "🆕" if it["video_id"] in added else "  "
                print(f"  {mark} {it['title'][:42]} · {it['channel']}")

            print("\n===== 판정 =====")
            print(f"  status 이벤트 수신: {'✅' if status else '❌'}")
            print(f"  최종 playlist 수신: {'✅' if final else '❌'}")
            print(f"  영상 수 유지(10): {'✅' if len(after) == len(before) else '❌'}")
            print(f"  중복 없음: {'✅' if len(after) == len(set(after)) else '❌'}")
            print(
                f"  부분 변경(전체 아님): {'✅' if 0 < len(changed) < len(before) else ('변경 0' if not changed else '❌ 전체변경')}"
            )
        finally:
            await session.delete(persona)
            await session.commit()
            print(f"\n🧹 cleanup ({persona.id})")


if __name__ == "__main__":
    asyncio.run(main())
