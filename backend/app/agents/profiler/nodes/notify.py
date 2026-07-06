from __future__ import annotations

import os
import uuid
from html import escape
from typing import Any

from app.agents.profiler.state import ProfilerState
from app.services.email import send_email
from app.services.notification import build_notification, mask_email

# 이메일 팔레트
_INK = "#1f2937"
_MUTED = "#6b7280"
_ACCENT = "#6366f1"
_TRACK = "#ece9fe"
_BORDER = "#eceaf3"


def _frontend_url() -> str:
    return os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")


def _category_label(cat_id: str | None) -> str:
    from app.agents.indexer.utils import youtube_category_label

    return youtube_category_label(cat_id) or (str(cat_id) if cat_id else "기타")


async def _load_detail(state: ProfilerState) -> dict[str, Any] | None:
    """결과 페이지와 동일한 스냅샷 상세(상위 카테고리·롱폼/숏폼 채널) 로드."""
    snapshot_id = state.get("snapshot_id")
    user_id = state.get("user_id")
    if not snapshot_id or not user_id:
        return None
    try:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.profiler_repository import fetch_profile_snapshot
        from app.services.profiler.service import profile_dict_with_catalog

        async with AsyncSessionLocal() as session:
            row = await fetch_profile_snapshot(
                session, uuid.UUID(str(user_id)), uuid.UUID(str(snapshot_id))
            )
            if row is None:
                return None
            return await profile_dict_with_catalog(session, row)
    except Exception:
        return None


def _extract(state: ProfilerState, detail: dict[str, Any] | None) -> dict[str, Any]:
    """이메일 렌더에 필요한 값들을 state + detail에서 폴백과 함께 수집."""
    detail = detail or {}
    portrait = detail.get("portrait") or state.get("portrait") or {}
    insight = state.get("profile_insight")

    persona = portrait.get("persona_label") or (
        insight.persona_label if insight else ""
    )
    summary = portrait.get("reasoning") or (insight.summary_text if insight else "")
    keywords = portrait.get("keywords") or []

    strengths = (insight.strengths if insight else None) or ""
    weaknesses = (insight.weaknesses if insight else None) or ""
    if not strengths or not weaknesses:
        se = detail.get("supporting_evidence") or {}
        se_insight = (se.get("insight") if isinstance(se, dict) else {}) or {}
        strengths = strengths or (se_insight.get("strengths") or "")
        weaknesses = weaknesses or (se_insight.get("weaknesses") or "")

    interest = sorted(
        portrait.get("interest") or [],
        key=lambda x: x.get("value") or 0,
        reverse=True,
    )[:6]

    stats = state.get("catalog_stats") or {}
    return {
        "persona": persona,
        "summary": summary,
        "keywords": keywords,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "interest": interest,
        "top_categories": (detail.get("top_categories") or [])[:5],
        "long_channels": (detail.get("top_channels_long") or [])[:5],
        "short_channels": (detail.get("top_channels_short") or [])[:5],
        "total": stats.get("total") or 0,
        "shorts_ratio": stats.get("shorts_ratio") or 0.0,
        "link": (
            f"{_frontend_url()}/me/analyses/{state.get('snapshot_id')}"
            if state.get("snapshot_id")
            else f"{_frontend_url()}/me/analyses"
        ),
    }


# ─────────────────────────── 텍스트(폴백) ───────────────────────────
def _build_email(
    state: ProfilerState, detail: dict[str, Any] | None
) -> tuple[str, str]:
    d = _extract(state, detail)
    persona = d["persona"]

    lines = [
        "Synapse 개인성향 분석이 완료되었습니다.",
        "",
        persona or "(페르소나 미정)",
        "  ".join(f"#{k}" for k in d["keywords"]),
        "",
        d["summary"],
    ]
    if d["strengths"]:
        lines += ["", "■ 강점", d["strengths"]]
    if d["weaknesses"]:
        lines += ["", "■ 맹점", d["weaknesses"]]
    if d["interest"]:
        lines += ["", "■ 관심사"]
        lines += [f"  {i['axis']}  {i.get('value', 0):.0f}%" for i in d["interest"]]
    if d["top_categories"]:
        lines += ["", "■ 상위 카테고리"]
        lines += [
            f"  {n}. {_category_label(c['category_id'])} ({c['count']})"
            for n, c in enumerate(d["top_categories"], 1)
        ]
    if d["long_channels"]:
        lines += ["", "■ 롱폼 상위 채널"]
        lines += [
            f"  {n}. {c['channel']} ({c['count']})"
            for n, c in enumerate(d["long_channels"], 1)
        ]
    if d["short_channels"]:
        lines += ["", "■ 숏폼 상위 채널"]
        lines += [
            f"  {n}. {c['channel']} ({c['count']})"
            for n, c in enumerate(d["short_channels"], 1)
        ]
    lines += [
        "",
        "■ 시청 요약",
        f"  기록: {d['total']}건",
        f"  숏폼 비중: {d['shorts_ratio']:.0%}",
        "",
        f"분석 결과 보기: {d['link']}",
    ]

    subject = f"[Synapse] ‘{persona or '프로필'}’ 분석이 완료되었습니다"
    return subject, "\n".join(lines)


# ─────────────────────────── HTML ───────────────────────────
def _section_title(text: str) -> str:
    return (
        f'<p style="margin:0 0 12px;font-size:13px;font-weight:700;color:{_INK};'
        f'letter-spacing:.02em;">{escape(text)}</p>'
    )


def _rank_list(items: list[dict], key: str, labeler=None) -> str:
    rows = ""
    for n, it in enumerate(items, 1):
        raw = it.get(key)
        label = labeler(raw) if labeler else str(raw)
        rows += (
            f"<tr>"
            f'<td style="padding:5px 0;font-size:13px;color:{_MUTED};width:22px;">{n}</td>'
            f'<td style="padding:5px 0;font-size:13px;color:{_INK};">{escape(label)}</td>'
            f'<td style="padding:5px 0;font-size:13px;color:{_MUTED};text-align:right;">'
            f"{it.get('count', '')}</td>"
            f"</tr>"
        )
    return f'<table width="100%" cellpadding="0" cellspacing="0">{rows}</table>'


def _card(title: str, inner: str, width: str = "") -> str:
    w = f' width="{width}"' if width else ""
    return (
        f'<td valign="top"{w} style="padding:14px;background:#fbfbfd;'
        f'border:1px solid {_BORDER};border-radius:12px;">'
        f"{_section_title(title)}{inner}</td>"
    )


def _interest_bars(interest: list[dict]) -> str:
    rows = ""
    for it in interest:
        axis = escape(str(it.get("axis", "")))
        val = float(it.get("value") or 0)
        rows += (
            f"<tr>"
            f'<td style="padding:4px 0;font-size:12px;color:{_INK};width:88px;">{axis}</td>'
            f'<td style="padding:4px 0;">'
            f'<div style="background:{_TRACK};border-radius:6px;height:8px;width:100%;">'
            f'<div style="background:{_ACCENT};border-radius:6px;height:8px;'
            f'width:{val:.0f}%;"></div></div></td>'
            f'<td style="padding:4px 0 4px 10px;font-size:12px;color:{_MUTED};'
            f'text-align:right;width:38px;">{val:.0f}%</td>'
            f"</tr>"
        )
    return f'<table width="100%" cellpadding="0" cellspacing="0">{rows}</table>'


def _build_email_html(state: ProfilerState, detail: dict[str, Any] | None) -> str:
    d = _extract(state, detail)
    persona = escape(d["persona"] or "개인성향 분석")
    keywords = "  ".join(f"#{escape(str(k))}" for k in d["keywords"])
    summary = escape(d["summary"]).replace("\n", "<br>")

    # 강점 / 맹점 박스
    sw = ""
    if d["strengths"] or d["weaknesses"]:
        cells = ""
        if d["strengths"]:
            cells += (
                f'<td valign="top" width="50%" style="padding:14px 16px;background:#f0fdf4;'
                f'border-left:3px solid #10b981;border-radius:8px;">'
                f'<p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#059669;">강점</p>'
                f'<p style="margin:0;font-size:13px;line-height:1.6;color:{_INK};">'
                f"{escape(d['strengths'])}</p></td>"
                f'<td width="12"></td>'
            )
        if d["weaknesses"]:
            cells += (
                f'<td valign="top" width="50%" style="padding:14px 16px;background:#fffbeb;'
                f'border-left:3px solid #f59e0b;border-radius:8px;">'
                f'<p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#d97706;">맹점</p>'
                f'<p style="margin:0;font-size:13px;line-height:1.6;color:{_INK};">'
                f"{escape(d['weaknesses'])}</p></td>"
            )
        sw = (
            f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin:0 0 24px;"><tr>{cells}</tr></table>'
        )

    # 관심사
    interest_block = ""
    if d["interest"]:
        interest_block = (
            f'<div style="margin:0 0 24px;">{_section_title("관심사")}'
            f"{_interest_bars(d['interest'])}</div>"
        )

    # 상위 카테고리 / 롱폼 / 숏폼 채널 — 한 행 3열
    cards: list[str] = []
    if d["top_categories"]:
        cards.append(
            _card(
                "상위 카테고리",
                _rank_list(d["top_categories"], "category_id", _category_label),
                width="32%",
            )
        )
    if d["long_channels"]:
        cards.append(
            _card(
                "롱폼 상위 채널", _rank_list(d["long_channels"], "channel"), width="32%"
            )
        )
    if d["short_channels"]:
        cards.append(
            _card(
                "숏폼 상위 채널",
                _rank_list(d["short_channels"], "channel"),
                width="32%",
            )
        )
    ranks_row = ""
    if cards:
        cells = '<td width="10"></td>'.join(cards)
        ranks_row = (
            f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin:0 0 24px;"><tr>{cells}</tr></table>'
        )

    tags_html = (
        f'<p style="margin:10px 0 0;font-size:13px;color:#e0e0ff;">{keywords}</p>'
        if keywords
        else ""
    )
    summary_html = (
        f'<p style="margin:0 0 24px;font-size:14px;line-height:1.7;color:{_INK};">'
        f"{summary}</p>"
        if summary
        else ""
    )

    return f"""\
<div style="margin:0;padding:24px 0;background:#f4f4f7;">
  <table align="center" width="680" cellpadding="0" cellspacing="0"
    style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:16px;
    overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',
    Roboto,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;">
    <tr>
      <td style="padding:28px 32px;background:#4f46e5;">
        <p style="margin:0;font-size:12px;color:#c7d2fe;letter-spacing:.04em;">
          SYNAPSE · 개인성향 분석 완료</p>
        <h1 style="margin:6px 0 0;font-size:22px;font-weight:800;color:#ffffff;
          line-height:1.3;">{persona}</h1>
        {tags_html}
      </td>
    </tr>
    <tr>
      <td style="padding:28px 32px 8px;">
        {summary_html}
        {sw}
        {interest_block}
        {ranks_row}
        <table width="100%" cellpadding="0" cellspacing="0"
          style="margin:0 0 24px;padding:14px 16px;background:#fbfbfd;
          border:1px solid {_BORDER};border-radius:12px;">
          <tr>
            <td style="font-size:13px;color:{_MUTED};">시청 기록</td>
            <td style="font-size:13px;color:{_INK};font-weight:700;text-align:right;">
              {d["total"]}건</td>
          </tr>
          <tr>
            <td style="font-size:13px;color:{_MUTED};padding-top:6px;">숏폼 비중</td>
            <td style="font-size:13px;color:{_INK};font-weight:700;text-align:right;
              padding-top:6px;">{d["shorts_ratio"]:.0%}</td>
          </tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr><td align="center" style="padding:0 0 8px;">
            <a href="{escape(d["link"])}" style="display:inline-block;padding:12px 28px;
              background:{_ACCENT};color:#ffffff;font-size:14px;font-weight:700;
              text-decoration:none;border-radius:10px;">분석 결과 자세히 보기 →</a>
          </td></tr>
        </table>
      </td>
    </tr>
    <tr>
      <td style="padding:18px 32px 28px;border-top:1px solid {_BORDER};">
        <p style="margin:0;font-size:11px;color:#9ca3af;text-align:center;">
          이 메일은 Synapse 프로필 분석 완료 시 자동 발송됩니다.</p>
      </td>
    </tr>
  </table>
</div>"""


async def notify_node(state: ProfilerState) -> dict:
    recipient = (state.get("notify_email") or "").strip()
    log = list(state.get("investigation_log") or [])

    if not recipient:
        log.append("notify: skipped (no email)")
        return {"current_step": "notify", "investigation_log": log}

    detail = await _load_detail(state)
    subject, text = _build_email(state, detail)
    html = _build_email_html(state, detail)
    mail_result = send_email(recipient, subject, text, html=html)

    d = _extract(state, detail)
    persona = d["persona"]
    notification = build_notification(
        notification_type="analysis_complete",
        message=(
            f"‘{persona}’ 분석이 완료되었습니다."
            if persona
            else "개인성향 분석이 완료되었습니다."
        ),
        mail_result=mail_result,
        recipient=recipient,
    )

    if mail_result.sent:
        log.append(f"notify: mail sent to {mask_email(recipient)}")
    elif mail_result.attempted:
        log.append(f"notify: mail failed ({mail_result.error})")
    else:
        log.append(f"notify: mail skipped ({mail_result.error})")

    return {
        "notification": notification,
        "current_step": "notify",
        "investigation_log": log,
    }
