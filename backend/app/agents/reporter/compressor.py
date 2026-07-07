"""GlobalTrendsSnapshot JSONB → Gemini 피딩용 경량 Compact Delimiter Format 변환."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from app.agents.navigator.constants import BEHAVIOR_AXES
from app.models.global_trends_snapshot import GlobalTrendsSnapshot
from app.models.trend_domain import TrendDomain

# 필드 구분자: 레코드(;), 필드(|), 키-값(:), 목록(,)
_RECORD_SEP = ";"
_FIELD_SEP = "|"
_KV_SEP = ":"
_LIST_SEP = ","

# 도메인·8축 약어 — 토큰 절감용 (첫 줄 LEGEND에 역매핑 제공)
_DOMAIN_ABBR: dict[str, str] = {
    TrendDomain.TECH_BUSINESS.value: "TB",
    TrendDomain.CONTENT_MEDIA.value: "CM",
    TrendDomain.LIFESTYLE_WELLNESS.value: "LW",
    TrendDomain.SOCIAL_CURRENT_AFFAIRS.value: "SCA",
    TrendDomain.KNOWLEDGE_EDUCATION.value: "KE",
    TrendDomain.ECONOMY_TECHFIN.value: "ET",
}

_AXIS_ABBR: dict[str, str] = {
    "exploration": "exp",
    "analytical": "ana",
    "creativity": "cre",
    "execution": "exe",
    "achievement_drive": "ach",
    "autonomy": "aut",
    "sociality": "soc",
    "sensitivity": "sen",
}


@dataclass(frozen=True, slots=True)
class CompressedSnapshot:
    """압축된 스냅샷 컨텍스트와 압축 지표."""

    target_date: str
    compact_text: str
    raw_json_chars: int
    compressed_chars: int

    @property
    def compression_ratio(self) -> float:
        if self.raw_json_chars <= 0:
            return 0.0
        return round(1.0 - (self.compressed_chars / self.raw_json_chars), 4)


class DataCompressor:
    """스냅샷 JSONB를 Compact Delimiter-separated Format으로 변환한다."""

    @classmethod
    def compress_snapshot(cls, snapshot: GlobalTrendsSnapshot) -> CompressedSnapshot:
        payload = cls._snapshot_to_payload(snapshot)
        target_date = cls._resolve_target_date(snapshot, payload)
        compact_text = cls._build_compact_text(target_date, payload)
        raw_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return CompressedSnapshot(
            target_date=target_date,
            compact_text=compact_text,
            raw_json_chars=len(raw_json),
            compressed_chars=len(compact_text),
        )

    @classmethod
    def compress_payload(
        cls,
        payload: Mapping[str, Any],
        *,
        target_date: str | None = None,
    ) -> CompressedSnapshot:
        resolved_date = target_date or cls._payload_target_date(payload)
        compact_text = cls._build_compact_text(resolved_date, payload)
        raw_json = json.dumps(dict(payload), ensure_ascii=False, separators=(",", ":"))
        return CompressedSnapshot(
            target_date=resolved_date,
            compact_text=compact_text,
            raw_json_chars=len(raw_json),
            compressed_chars=len(compact_text),
        )

    @staticmethod
    def _snapshot_to_payload(snapshot: GlobalTrendsSnapshot) -> dict[str, Any]:
        return {
            "top_domains": snapshot.top_domains or {},
            "top_scrap_categories": snapshot.top_scrap_categories or {},
            "external_market_keywords": snapshot.external_market_keywords or {},
            "global_8_axis_avg": snapshot.global_8_axis_avg or {},
            "trending_keywords": snapshot.trending_keywords or {},
            "cross_domain_insights": snapshot.cross_domain_insights,
        }

    @classmethod
    def _resolve_target_date(
        cls,
        snapshot: GlobalTrendsSnapshot,
        payload: Mapping[str, Any],
    ) -> str:
        trending = payload.get("trending_keywords")
        if isinstance(trending, dict) and trending.get("target_date"):
            return str(trending["target_date"])
        if snapshot.snapshot_date:
            return snapshot.snapshot_date.date().isoformat()
        return cls._payload_target_date(payload)

    @staticmethod
    def _payload_target_date(payload: Mapping[str, Any]) -> str:
        trending = payload.get("trending_keywords")
        if isinstance(trending, dict) and trending.get("target_date"):
            return str(trending["target_date"])
        return date.today().isoformat()

    @classmethod
    def _build_compact_text(cls, target_date: str, payload: Mapping[str, Any]) -> str:
        sections = [
            (
                "LEGEND "
                "DM=도메인(TB=Tech/Business,CM=Content/Media,LW=Lifestyle/Wellness,"
                "SCA=Social/Current Affairs,KE=Knowledge/Education,ET=Economy/TechFin) "
                "KW=키워드|오늘빈도|7일평균|급상승스코어 "
                "AX=8축약어:점수 "
                "SC=스크랩카테고리|건수|순위 "
                "EXT=도메인약어:g구글키워드,n네이버키워드"
            ),
            f"DATE {target_date}",
            f"DM {cls._compress_domains(payload.get('top_domains'))}",
            f"KW {cls._compress_trending_keywords(payload.get('trending_keywords'))}",
            f"AX {cls._compress_axes(payload.get('global_8_axis_avg'))}",
            f"SC {cls._compress_scrap_categories(payload.get('top_scrap_categories'))}",
            f"EXT {cls._compress_external_market(payload.get('external_market_keywords'))}",
        ]
        meta = cls._compress_meta(payload.get("trending_keywords"))
        if meta:
            sections.append(f"META {meta}")
        return "\n".join(section for section in sections if section.split(" ", 1)[-1])

    @classmethod
    def _compress_domains(cls, top_domains: Any) -> str:
        if not isinstance(top_domains, dict) or not top_domains:
            return ""

        records: list[str] = []
        for domain in TrendDomain:
            bucket = top_domains.get(domain.value)
            if not isinstance(bucket, dict):
                continue
            abbr = _DOMAIN_ABBR.get(domain.value, domain.value)
            user_count = int(bucket.get("user_count", 0) or 0)
            total_duration = int(bucket.get("total_duration", 0) or 0)
            avg_weight = round(float(bucket.get("avg_weight", 0.0) or 0.0), 4)
            records.append(
                _FIELD_SEP.join(
                    [
                        abbr,
                        str(user_count),
                        str(total_duration),
                        f"{avg_weight:.4f}",
                    ]
                )
            )
        return _RECORD_SEP.join(records)

    @classmethod
    def _compress_trending_keywords(cls, trending_keywords: Any) -> str:
        if not isinstance(trending_keywords, dict):
            return ""

        ranking = trending_keywords.get("ranking")
        if not isinstance(ranking, list):
            return ""

        records: list[str] = []
        for row in ranking:
            if not isinstance(row, dict):
                continue
            keyword = str(row.get("keyword", "")).strip()
            if not keyword:
                continue
            count_today = int(row.get("count_today", 0) or 0)
            avg_7day = round(float(row.get("avg_7day", 0.0) or 0.0), 4)
            score = round(float(row.get("score", 0.0) or 0.0), 4)
            records.append(
                _FIELD_SEP.join(
                    [
                        keyword,
                        str(count_today),
                        f"{avg_7day:.4f}",
                        f"{score:.4f}",
                    ]
                )
            )
        return _RECORD_SEP.join(records)

    @classmethod
    def _compress_axes(cls, global_8_axis_avg: Any) -> str:
        if not isinstance(global_8_axis_avg, dict) or not global_8_axis_avg:
            return ""

        parts: list[str] = []
        for axis in BEHAVIOR_AXES:
            raw = global_8_axis_avg.get(axis)
            if raw is None:
                continue
            abbr = _AXIS_ABBR.get(axis, axis)
            score = round(float(raw), 2)
            parts.append(f"{abbr}{_KV_SEP}{score:.2f}")
        return _LIST_SEP.join(parts)

    @classmethod
    def _compress_scrap_categories(cls, top_scrap_categories: Any) -> str:
        if not isinstance(top_scrap_categories, dict) or not top_scrap_categories:
            return ""

        ranked = sorted(
            top_scrap_categories.items(),
            key=lambda item: (
                int((item[1] or {}).get("rank", 999))
                if isinstance(item[1], dict)
                else 999
            ),
        )
        records: list[str] = []
        for category, stats in ranked[:15]:
            if not isinstance(stats, dict):
                continue
            count = int(stats.get("count", 0) or 0)
            rank = int(stats.get("rank", 0) or 0)
            safe_category = (
                str(category).replace(_FIELD_SEP, "/").replace(_RECORD_SEP, "/")
            )
            records.append(_FIELD_SEP.join([safe_category, str(count), str(rank)]))
        return _RECORD_SEP.join(records)

    @classmethod
    def _compress_external_market(cls, external_market_keywords: Any) -> str:
        if not isinstance(external_market_keywords, dict):
            return ""

        by_domain = external_market_keywords.get("by_domain")
        if not isinstance(by_domain, dict) or not by_domain:
            return ""

        records: list[str] = []
        for domain in TrendDomain:
            bucket = by_domain.get(domain.value)
            if not isinstance(bucket, dict):
                continue
            abbr = _DOMAIN_ABBR.get(domain.value, domain.value)
            google_kw = cls._extract_external_keywords(
                bucket.get("google"), key="keyword", limit=4
            )
            naver_kw = cls._extract_external_naver_keywords(
                bucket.get("naver"), limit=4
            )
            if not google_kw and not naver_kw:
                continue
            g_part = _LIST_SEP.join(google_kw) if google_kw else "-"
            n_part = _LIST_SEP.join(naver_kw) if naver_kw else "-"
            records.append(_FIELD_SEP.join([abbr, f"g:{g_part}", f"n:{n_part}"]))
        return _RECORD_SEP.join(records)

    @staticmethod
    def _extract_external_keywords(
        entries: Any,
        *,
        key: str,
        limit: int,
    ) -> list[str]:
        if not isinstance(entries, list):
            return []
        keywords: list[str] = []
        for entry in entries[:limit]:
            if not isinstance(entry, dict):
                continue
            value = str(entry.get(key, "")).strip()
            if value:
                keywords.append(value.replace(_LIST_SEP, "/"))
        return keywords

    @classmethod
    def _extract_external_naver_keywords(cls, entries: Any, *, limit: int) -> list[str]:
        if not isinstance(entries, list):
            return []
        keywords: list[str] = []
        for entry in entries[:limit]:
            if not isinstance(entry, dict):
                continue
            group = str(entry.get("group_name", "")).strip()
            if group:
                keywords.append(group.replace(_LIST_SEP, "/"))
                continue
            raw = str(entry.get("keywords", "")).strip()
            if raw:
                first = raw.replace("/", _LIST_SEP).split(_LIST_SEP)[0].strip()
                if first:
                    keywords.append(first.replace(_LIST_SEP, "/"))
        return keywords[:limit]

    @staticmethod
    def _compress_meta(trending_keywords: Any) -> str:
        if not isinstance(trending_keywords, dict):
            return ""
        meta = trending_keywords.get("meta")
        if not isinstance(meta, dict):
            return ""
        unique_today = meta.get("unique_keywords_today")
        lookback = trending_keywords.get("lookback_days")
        if unique_today is None and lookback is None:
            return ""
        parts: list[str] = []
        if unique_today is not None:
            parts.append(f"kw_today={unique_today}")
        if lookback is not None:
            parts.append(f"lookback={lookback}")
        return _LIST_SEP.join(parts)
