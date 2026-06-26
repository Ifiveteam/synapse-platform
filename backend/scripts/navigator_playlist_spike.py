"""[스파이크] YouTube 재생목록 채널 발굴 검증 — 구현 전 go/no-go.

이상향 페르소나로 Gemini Google 검색 그라운딩 → 실재 채널 텍스트 →
핸들/URL 추출 → forHandle(1유닛)/URL 파싱으로 channel_id 확보 → RSS 신선 영상 확인.
핵심 질문: "그라운딩이 실재하는 한국 채널을 얼마나 정확히 주는가?"

실행: cd backend && PYTHONUTF8=1 PYTHONPATH=. uv run python scripts/navigator_playlist_spike.py
"""

import asyncio
import os
import re
import xml.etree.ElementTree as ET

from app.core.env import load_backend_env

load_backend_env()

import httpx  # noqa: E402
from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

GEMINI_MODEL = "gemini-2.5-flash"
YT_API = "https://www.googleapis.com/youtube/v3/channels"
RSS = "https://www.youtube.com/feeds/videos.xml"

# ── 테스트 페르소나 (dev 유저는 엔터/스포츠 편중 → 분석형 이상향으로 '새 채널 발굴' 테스트) ──
PERSONA = """[이상향 페르소나] 분석적인 탐구가
[설계 근거] 데이터와 논리로 세상을 깊이 파고들고, 표면적 재미보다 '왜'를 따지는 사람.
경제·과학·시사를 비판적으로 해부하는 콘텐츠를 즐기며, 한 주제를 끝까지 파고든다.
[이상향 13축 요지] 자기지향·보편성·탐구성·지속성·성취 높음 / 쾌락·순응 낮음
[현재 성향] 평소 예능·스포츠·게임 위주 시청 (분석/교육 콘텐츠 거의 없음)
[관심사] 자주 본 채널: 야구 하이라이트, 게임 방송 / 카테고리: 스포츠·엔터·게임"""

SYSTEM = """당신은 사용자에게 YouTube 채널을 추천하는 큐레이터입니다.
주어진 '이상향 페르소나'에 맞는 **실재하는 한국 YouTube 채널**을 웹 검색으로 찾아 8~10개 추천하세요.
각 채널마다 반드시 **그 채널의 실제 YouTube URL 전체**(예: https://www.youtube.com/@핸들 또는
https://www.youtube.com/channel/UC...)와 한 줄 추천 이유를 적으세요. 검색으로 확인한 실제 URL만 적으세요.
사용자가 평소 보던 분야(예능·스포츠)가 아니라 이상향(분석·탐구) 방향의 새 채널을 발굴하세요."""

HANDLE_RE = re.compile(r"youtube\.com/(@[A-Za-z0-9._\-]+)")
CHANNEL_URL_RE = re.compile(r"youtube\.com/channel/(UC[\w-]{20,})")
REDIRECT_YT_RE = re.compile(r"youtube\.com/(channel/UC[\w-]{20,}|@[A-Za-z0-9._\-]+)")


async def resolve_handle(client: httpx.AsyncClient, handle: str, key: str):
    h = handle if handle.startswith("@") else f"@{handle}"
    try:
        r = await client.get(
            YT_API,
            params={"part": "id,snippet", "forHandle": h, "key": key},
            timeout=15,
        )
        items = r.json().get("items") or []
        if items:
            return items[0]["id"], items[0]["snippet"]["title"]
    except Exception as e:
        print(f"    forHandle 실패 {h}: {e}")
    return None, None


async def fetch_rss(client: httpx.AsyncClient, channel_id: str, limit: int = 5):
    try:
        r = await client.get(RSS, params={"channel_id": channel_id}, timeout=15)
        root = ET.fromstring(r.text)
        ns = {
            "a": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }
        out = []
        for entry in root.findall("a:entry", ns)[:limit]:
            vid = entry.find("yt:videoId", ns)
            title = entry.find("a:title", ns)
            out.append(
                (
                    vid.text if vid is not None else "?",
                    title.text if title is not None else "?",
                )
            )
        return out
    except Exception as e:
        print(f"    RSS 실패 {channel_id}: {e}")
        return []


async def main() -> None:
    yt_key = os.getenv("YOUTUBE_API_KEY")
    gem_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    print(
        f"YOUTUBE_API_KEY={'있음' if yt_key else '없음'} / GEMINI={'있음' if gem_key else '없음'}\n"
    )

    print("===== ① Gemini 그라운딩(google_search) 채널 발굴 =====")
    client = genai.Client(api_key=gem_key)
    resp = await client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=PERSONA,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.4,
        ),
    )
    text = (resp.text or "").strip()
    print(text)

    print("\n===== ②-A 본문 텍스트에서 URL 추출 =====")
    handles = sorted(set(HANDLE_RE.findall(text)))
    url_ids = sorted(set(CHANNEL_URL_RE.findall(text)))
    print(f"  본문 @핸들 URL {len(handles)}개: {handles}")
    print(f"  본문 /channel/UC URL {len(url_ids)}개: {url_ids}")

    print("\n===== ②-B 그라운딩 메타데이터(실제 출처) → 진짜 채널 URL 추적 =====")
    grounded_handles: set[str] = set()
    grounded_ids: set[str] = set()
    try:
        gm = resp.candidates[0].grounding_metadata
        chunks = getattr(gm, "grounding_chunks", None) or []
        print(f"  grounding_chunks {len(chunks)}개")
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as hc:
            for ch in chunks:
                web = getattr(ch, "web", None)
                if not web:
                    continue
                uri, title = getattr(web, "uri", ""), getattr(web, "title", "")
                final = uri
                try:  # vertex redirect → 실제 출처 URL
                    r = await hc.get(uri)
                    final = str(r.url)
                except Exception:
                    pass
                m = REDIRECT_YT_RE.search(final)
                hit = m.group(1) if m else ""
                if hit.startswith("channel/"):
                    grounded_ids.add(hit.split("/", 1)[1])
                elif hit.startswith("@"):
                    grounded_handles.add(hit)
                flag = f"→ {hit}" if hit else "(유튜브 채널 아님)"
                print(f"    [{title}] {final[:70]} {flag}")
    except Exception as e:
        print(f"  grounding_metadata 접근 실패: {e}")
    print(
        f"  그라운딩 출처에서: channel_id {len(grounded_ids)}개, @핸들 {len(grounded_handles)}개"
    )
    handles = sorted(set(handles) | grounded_handles)
    url_ids = sorted(set(url_ids) | grounded_ids)

    print("\n===== ③ channel_id 해석 (forHandle 1유닛 / URL 0유닛) =====")
    resolved: list[tuple[str, str]] = [(uid, "(URL)") for uid in url_ids]
    async with httpx.AsyncClient() as hc:
        results = await asyncio.gather(
            *(resolve_handle(hc, h, yt_key) for h in handles)
        )
        for h, (cid, title) in zip(handles, results, strict=True):
            mark = "✅" if cid else "❌"
            print(f"  {mark} {h} → {cid or '해석 실패'} {title or ''}")
            if cid:
                resolved.append((cid, title or ""))

        print(
            f"\n  → 유효 채널 {len(resolved)}개 / 추출 {len(handles) + len(url_ids)}개"
        )

        print("\n===== ④ RSS 신선 영상 샘플 (상위 3채널) =====")
        for cid, title in resolved[:3]:
            print(f"  [{title}] {cid}")
            for vid, vtitle in await fetch_rss(hc, cid):
                print(f"     - {vid}  {vtitle}")

    print("\n===== 판정 =====")
    print(f"  발굴 채널 유효율: {len(resolved)}/{len(handles) + len(url_ids)}")
    print("  → 유효 채널이 충분(≥8)하고 RSS 신선 영상이 나오면 GO")


if __name__ == "__main__":
    asyncio.run(main())
