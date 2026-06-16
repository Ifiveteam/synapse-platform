import json
import os
import re
import urllib.request
import zipfile
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
    details = item.get("details", [])
    return any("광고" in d.get("name", "") for d in details)


def extract_title(raw_title: str) -> str:
    return re.sub(r"\s*을\(를\)\s*시청했습니다\.$", "", raw_title).strip()


def normalize_timestamp(time_str: str) -> str:
    if not time_str:
        return ""
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return time_str


def preprocess(data: list[dict]) -> list[dict]:
    cleaned = []
    for item in data:
        if is_ad(item):
            continue
        url = item.get("titleUrl", "")
        if "watch?v=" not in url and "/shorts/" not in url:
            continue
        title = extract_title(item.get("title", "")).strip()
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
                "url": url,
                "watched_at": watched_at,
            }
        )
    return cleaned


def vectorize(items: list[dict]) -> list[dict]:
    if not items:
        return []
    texts = [f"{item['title']} {item['channel']}" for item in items]
    response = _openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [
        {**item, "embedding": emb.embedding} for item, emb in zip(items, response.data)
    ]


def extract_video_id(url: str) -> str | None:
    m = re.search(r"(?:v=|shorts/)([^&?/]+)", url)
    return m.group(1) if m else None


def thumbnail_url_for(url: str) -> str | None:
    """공개 썸네일 URL (API 없이 사용 가능)."""
    video_id = extract_video_id(url)
    if not video_id:
        return None
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


_extract_video_id = extract_video_id


def _parse_duration(duration_str: str) -> int:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str or "PT0S")
    if not m:
        return 0
    return (
        int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)
    )


def get_videos_info_batch(urls: list[str]) -> list[dict]:
    """YouTube API 배치 호출 (50개/요청) — 2000개 → 40번 호출"""
    api_key = os.getenv("YOUTUBE_API_KEY")
    url_is_shorts = {url: "/shorts/" in url for url in urls}

    if not api_key:
        return [
            {
                "description": "",
                "duration": 0,
                "is_shorts": url_is_shorts[u],
                "tags": [],
                "thumbnail_url": thumbnail_url_for(u),
            }
            for u in urls
        ]

    id_to_url: dict[str, str] = {}
    for url in urls:
        vid_id = _extract_video_id(url)
        if vid_id:
            id_to_url[vid_id] = url

    api_results: dict[str, dict] = {}
    video_ids = list(id_to_url.keys())

    total_batches = (len(video_ids) + 49) // 50
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        batch_num = i // 50 + 1
        print(f"[YouTube API] 배치 {batch_num}/{total_batches} ({len(batch)}개)")
        api_url = (
            "https://www.googleapis.com/youtube/v3/videos"
            f"?part=snippet,contentDetails&id={','.join(batch)}&key={api_key}"
        )
        try:
            with urllib.request.urlopen(api_url, timeout=15) as resp:
                data = json.loads(resp.read())
                for item in data.get("items", []):
                    vid_id = item["id"]
                    snippet = item.get("snippet", {})
                    content = item.get("contentDetails", {})
                    tags = snippet.get("tags", [])
                    duration = _parse_duration(content.get("duration", "PT0S"))
                    tag_shorts = any(t.lower() in ("#shorts", "shorts") for t in tags)
                    thumbs = snippet.get("thumbnails", {})
                    thumb = (
                        thumbs.get("high", {}).get("url")
                        or thumbs.get("medium", {}).get("url")
                        or thumbs.get("default", {}).get("url")
                    )
                    api_results[vid_id] = {
                        "description": snippet.get("description", ""),
                        "duration": duration,
                        "tags": [
                            t for t in tags if t.lower() not in ("#shorts", "shorts")
                        ],
                        "tag_is_shorts": tag_shorts,
                        "duration_is_shorts": 0 < duration <= 60,
                        "thumbnail_url": thumb,
                    }
        except Exception as e:
            print(f"[YouTube API 배치] 에러 (ids {i}~{i + 50}): {e}")

    result = []
    url_shorts_count = 0
    tag_shorts_count = 0
    duration_shorts_count = 0
    for url in urls:
        vid_id = _extract_video_id(url)
        url_shorts = url_is_shorts[url]
        if vid_id and vid_id in api_results:
            info = api_results[vid_id]
            is_shorts = (
                url_shorts or info["tag_is_shorts"] or info["duration_is_shorts"]
            )
            if url_shorts:
                url_shorts_count += 1
            if info["tag_is_shorts"]:
                tag_shorts_count += 1
            if info["duration_is_shorts"]:
                duration_shorts_count += 1
            result.append(
                {
                    "description": info["description"],
                    "duration": info["duration"],
                    "is_shorts": is_shorts,
                    "tags": info["tags"],
                    "thumbnail_url": info.get("thumbnail_url")
                    or thumbnail_url_for(url),
                }
            )
        else:
            if url_shorts:
                url_shorts_count += 1
            result.append(
                {
                    "description": "",
                    "duration": 0,
                    "is_shorts": url_shorts,
                    "tags": [],
                    "thumbnail_url": thumbnail_url_for(url),
                }
            )
    print(
        f"[Shorts 감지] URL: {url_shorts_count}건 / 태그: {tag_shorts_count}건 / 60초이하: {duration_shorts_count}건 / API응답: {len(api_results)}건/{len(urls)}건"
    )
    return result


_KW_NOISE = {
    "shorts",
    "youtube",
    "youtuber",
    "viral",
    "video",
    "재생목록",
    "구독",
    "영상",
    "동영상",
    "공식",
    "official",
    "무료",
    "전체",
    "모음",
    "최신",
    "ver",
    "버전",
    "편집",
    "다시보기",
    "highlight",
    "full",
}
_KW_PARTICLES = {
    "는",
    "은",
    "이",
    "가",
    "을",
    "를",
    "의",
    "에",
    "에서",
    "로",
    "으로",
    "와",
    "과",
    "도",
    "만",
    "고",
    "한",
    "하는",
    "에게",
    "처럼",
    "보다",
}


def _extract_words(text: str) -> list[str]:
    """텍스트에서 의미있는 단어 추출 (2글자 이상, 불용어 제외)"""
    words = re.split(r"[\s\[\]\(\)\|/\-_,.!?~·×X×]+", text or "")
    result = []
    for w in words:
        w = w.strip()
        if len(w) < 2:
            continue
        if w.lower() in _KW_NOISE or w in _KW_PARTICLES:
            continue
        if w.isdigit():
            continue
        result.append(w)
    return result


def extract_hashtags(
    description: str, tags: list[str] | None = None, title: str = ""
) -> list[str]:
    """여러 소스를 합쳐 최소 3~5개 키워드 추출"""
    seen: set[str] = set()
    result: list[str] = []

    def _add(items: list[str]) -> None:
        for w in items:
            if w.lower() not in seen and len(result) < 5:
                seen.add(w.lower())
                result.append(w)

    # 1. YouTube API tags
    if tags:
        _add([t for t in tags if t.lower() not in _KW_NOISE])
    # 2. 디스크립션 해시태그
    _add(
        [
            h
            for h in re.findall(r"#([\w가-힣]+)", description or "")
            if h.lower() not in _KW_NOISE
        ]
    )
    # 3. 제목 해시태그
    _add(
        [
            h
            for h in re.findall(r"#([\w가-힣]+)", title or "")
            if h.lower() not in _KW_NOISE
        ]
    )
    # 4. 부족하면 디스크립션 100자 단어로 채움 (제목 단어 제외)
    if len(result) < 3:
        _add(_extract_words((description or "")[:100]))

    return result


def get_video_info(video_url: str) -> dict:
    """단일 영상 정보 조회 (extension graph용)"""
    infos = get_videos_info_batch([video_url])
    return infos[0]


def add_keywords(items: list[dict]) -> list[dict]:
    """YouTube API 배치 보강 + LLM 키워드 추출"""
    from app.agents.indexer.prompt import extract_keywords_batch

    urls = [item.get("url", "") for item in items]
    video_infos = get_videos_info_batch(urls)

    batch_size = 20
    result = []
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        infos = video_infos[i : i + batch_size]

        texts = [
            item["title"] + (" " + info["description"] if info["description"] else "")
            for item, info in zip(batch, infos)
        ]
        keywords_list = extract_keywords_batch(texts)

        for item, keywords, info in zip(batch, keywords_list, infos, strict=False):
            result.append(
                {
                    **item,
                    "description": info["description"],
                    "keywords": keywords,
                    "title_keywords": keywords,
                    "desc_keywords": [],
                    "duration": info["duration"],
                    "is_shorts": info["is_shorts"],
                }
            )

    return result
