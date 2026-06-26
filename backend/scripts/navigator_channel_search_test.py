"""[스파이크] search?type=channel 1콜이 실재 채널 몇 개를 주나 확인.

1콜 = 100유닛. maxResults=25로 채널을 받아 channel_id/제목 출력 + RSS로 실재·활동 확인.
실행: cd backend && PYTHONUTF8=1 PYTHONPATH=. uv run python scripts/navigator_channel_search_test.py
"""

import asyncio
import os
import xml.etree.ElementTree as ET

from app.core.env import load_backend_env

load_backend_env()

import httpx  # noqa: E402

SEARCH = "https://www.googleapis.com/youtube/v3/search"
RSS = "https://www.youtube.com/feeds/videos.xml"

# 분석형 이상향 페르소나에서 LLM이 뽑을 법한 검색어 2종
QUERIES = ["경제 시사 심층 분석", "과학 교양 탐구"]


async def rss_ok(hc, channel_id):
    try:
        r = await hc.get(RSS, params={"channel_id": channel_id}, timeout=15)
        if r.status_code != 200:
            return None
        root = ET.fromstring(r.text)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        first = root.find("a:entry/a:title", ns)
        return first.text if first is not None else "(업로드 없음)"
    except Exception:
        return None


async def main():
    key = os.getenv("YOUTUBE_API_KEY")
    print(f"YOUTUBE_API_KEY={'있음' if key else '없음'}\n")
    async with httpx.AsyncClient() as hc:
        for q in QUERIES:
            print(f"===== search type=channel q='{q}' (maxResults=25, 100유닛) =====")
            r = await hc.get(
                SEARCH,
                params={
                    "part": "snippet",
                    "type": "channel",
                    "q": q,
                    "maxResults": 25,
                    "regionCode": "KR",
                    "relevanceLanguage": "ko",
                    "key": key,
                },
                timeout=20,
            )
            data = r.json()
            if "error" in data:
                print(f"  ERROR: {data['error'].get('message')}")
                continue
            items = data.get("items", [])
            print(f"  반환 채널 {len(items)}개\n")
            # RSS 실재 확인 (상위 8개만 — 무쿼터)
            checks = await asyncio.gather(
                *(rss_ok(hc, it["id"]["channelId"]) for it in items[:8])
            )
            for i, it in enumerate(items):
                cid = it["id"]["channelId"]
                title = it["snippet"]["title"]
                if i < 8:
                    live = checks[i]
                    mark = "✅실재" if live else "❌RSS실패"
                    extra = f" | 최근: {live[:40]}" if live else ""
                    print(f"  {mark} {title}  ({cid}){extra}")
                else:
                    print(f"  ·     {title}  ({cid})")
            print()


if __name__ == "__main__":
    asyncio.run(main())
