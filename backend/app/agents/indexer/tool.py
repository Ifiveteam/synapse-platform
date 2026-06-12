import asyncio
import json
import os
import re
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)
_openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def parse_takeout_zip(zip_path: str) -> list[dict]:
    """구글 테이크아웃 ZIP 파일에서 시청 기록 파싱"""
    target_names = ["watch-history.json", "시청_기록.json", "시청 기록.json"]

    with zipfile.ZipFile(zip_path, "r") as z:
        all_names = z.namelist()
        print(f"[ZIP] 파일 목록 ({len(all_names)}개): {all_names[:20]}")
        for name in all_names:
            if any(target in name for target in target_names):
                print(f"[ZIP] 시청 기록 발견: {name}")
                with z.open(name) as f:
                    data = json.load(f)
                    print(f"[ZIP] 항목 수: {len(data)}")
                    return data
    print(f"[ZIP] 시청 기록 파일 없음. 전체 목록: {all_names}")
    return []


def parse_takeout_json(json_path: str) -> list[dict]:
    """ZIP 없이 JSON 파일 직접 파싱 (테스트용)"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_ad(item: dict) -> bool:
    """광고 여부 판별"""
    details = item.get("details", [])
    return any("광고" in d.get("name", "") for d in details)


def extract_title(raw_title: str) -> str:
    """'영상제목 을(를) 시청했습니다.' → '영상제목' 추출"""
    return re.sub(r"\s*을\(를\)\s*시청했습니다\.$", "", raw_title).strip()


def normalize_timestamp(time_str: str) -> str:
    """타임스탬프 UTC 기준으로 정규화 → 'YYYY-MM-DD HH:MM:SS' 형식"""
    if not time_str:
        return ""
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return time_str


def preprocess(data: list[dict]) -> list[dict]:
    """전처리 - 노이즈 제거 + 텍스트 클렌징 + 타임스탬프 정규화"""
    cleaned = []
    for item in data:
        if is_ad(item):
            continue

        if not item.get("titleUrl"):
            continue

        raw_title = item.get("title", "")
        title = extract_title(raw_title)
        title = title.strip()

        if not title:
            continue

        subtitles = item.get("subtitles", [])
        channel = subtitles[0].get("name", "") if subtitles else ""
        channel_url = subtitles[0].get("url", "") if subtitles else ""
        watched_at = normalize_timestamp(item.get("time", ""))

        cleaned.append(
            {
                "title": title,
                "channel": channel,
                "channel_url": channel_url,
                "url": item.get("titleUrl", ""),
                "watched_at": watched_at,
            }
        )

    return cleaned


def vectorize(items: list[dict]) -> list[dict]:
    """제목 + 채널명 벡터화 (OpenAI text-embedding-3-small)"""
    if not items:
        return []
    texts = [f"{item['title']} {item['channel']}" for item in items]
    response = _openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    result = []
    for item, emb_data in zip(items, response.data, strict=False):
        result.append({**item, "embedding": emb_data.embedding})
    return result


def is_shorts_by_redirect(video_url: str) -> bool:
    """shorts/ URL 리다이렉트로 쇼츠 여부 판별"""
    match = re.search(r"(?:v=|shorts/)([^&?]+)", video_url)
    if not match:
        return False
    video_id = match.group(1)
    shorts_url = f"https://www.youtube.com/shorts/{video_id}"
    try:
        req = urllib.request.Request(
            shorts_url,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            final_url = response.url
            return "shorts" in final_url
    except Exception:
        return False


def get_video_info(video_url: str) -> dict:
    """YouTube URL에서 description, duration, is_shorts 한 번에 가져오기"""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return {"description": "", "duration": 0, "is_shorts": False}

    match = re.search(r"(?:v=|shorts/)([^&?]+)", video_url)
    if not match:
        return {"description": "", "duration": 0, "is_shorts": False}

    video_id = match.group(1)
    url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet,contentDetails&id={video_id}&key={api_key}"
    )

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
            items = data.get("items", [])
            if not items:
                return {"description": "", "duration": 0, "is_shorts": False}

            snippet = items[0].get("snippet", {})
            content = items[0].get("contentDetails", {})

            description = snippet.get("description", "")
            tags = snippet.get("tags", [])
            is_shorts = any(t.lower() in ("#shorts", "shorts") for t in tags)

            duration_str = content.get("duration", "PT0S")
            m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
            duration = 0
            if m:
                h = int(m.group(1) or 0)
                mins = int(m.group(2) or 0)
                s = int(m.group(3) or 0)
                duration = h * 3600 + mins * 60 + s

            # 태그에 없으면 리다이렉트로 확인
            if not is_shorts:
                is_shorts = is_shorts_by_redirect(video_url)

            # 그래도 안되면 60초 기준
            if not is_shorts and duration <= 60:
                is_shorts = True

            return {
                "description": description,
                "duration": duration,
                "is_shorts": is_shorts,
            }
    except Exception:
        return {"description": "", "duration": 0, "is_shorts": False}


def add_keywords(items: list[dict]) -> list[dict]:
    """LLM으로 제목 + description 키워드 추출 + 쇼츠 여부 (YouTube API 병렬 호출)"""
    from app.agents.indexer.prompt import extract_keywords_batch

    # YouTube API 병렬 호출
    urls = [item.get("url", "") for item in items]
    with ThreadPoolExecutor(max_workers=20) as executor:
        video_infos = list(executor.map(get_video_info, urls))

    # LLM 키워드 추출 (배치)
    batch_size = 20
    result = []

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        infos = video_infos[i : i + batch_size]

        texts = []
        for item, info in zip(batch, infos):
            text = item["title"]
            if info["description"]:
                text += " " + info["description"][:100]
            texts.append(text)

        keywords_list = extract_keywords_batch(texts)

        for item, keywords, info in zip(batch, keywords_list, infos, strict=False):
            result.append({
                **item,
                "keywords": keywords,
                "title_keywords": keywords,
                "desc_keywords": [],
                "duration": info["duration"],
                "is_shorts": info["is_shorts"],
            })

    return result