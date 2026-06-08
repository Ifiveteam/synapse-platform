import json
import re
import zipfile
from datetime import datetime, timezone

from sentence_transformers import SentenceTransformer


def parse_takeout_zip(zip_path: str) -> list[dict]:
    """구글 테이크아웃 ZIP 파일에서 시청 기록 파싱"""
    target_names = ["watch-history.json", "시청_기록.json", "시청 기록.json"]

    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            if any(target in name for target in target_names):
                with z.open(name) as f:
                    data = json.load(f)
                    return data
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


_model = None


def get_model():
    """BGE-m3 모델 로드 (최초 1회만 다운로드)"""
    global _model
    if _model is None:
        print("BGE-m3 모델 로딩 중... (첫 실행 시 다운로드 약 2GB)")
        _model = SentenceTransformer("BAAI/bge-m3")
    return _model


def vectorize(items: list[dict]) -> list[dict]:
    """제목 + 채널명 벡터화"""
    model = get_model()
    texts = [f"{item['title']} {item['channel']}" for item in items]
    embeddings = model.encode(texts, show_progress_bar=True)

    result = []
    for item, embedding in zip(items, embeddings, strict=False):
        result.append({**item, "embedding": embedding.tolist()})

    return result
