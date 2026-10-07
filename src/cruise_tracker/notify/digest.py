"""Weekly Telegram digest (docs/DESIGN.md §6.1)."""

from datetime import date, datetime, timedelta
from html import escape

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..fx import current_rate
from ..models import AlertLog, Deal, ScrapeRun, Sailing, SourceListing, Watch
from ..scoring import latest_deals, source_label
from ..watches import deal_matches


def build_digest(session: Session, today: date | None = None) -> str:
    settings = get_settings()
    today = today or date.today()
    week_start = today - timedelta(days=7)
    rate = current_rate(session)
    watches = session.scalars(select(Watch).where(Watch.is_active)).all()

    deals = [
        d
        for d in latest_deals(session)
        if d.score >= settings.digest_min_score and (not watches or any(deal_matches(w, d) for w in watches))
    ][: settings.digest_max_items]

    new_sailings = session.scalar(
        select(func.count(func.distinct(SourceListing.sailing_id))).where(SourceListing.first_seen_at >= week_start)
    )
    failed_runs = session.scalars(
        select(ScrapeRun).where(ScrapeRun.started_at >= week_start, ScrapeRun.status != "ok")
    ).all()

    lines = [
        f"🚢 <b>本週郵輪特價</b>（{week_start:%m/%d}–{today:%m/%d}）",
        f"追蹤中：{len(watches)} 組條件｜本週新航次 {new_sailings} 筆",
        "",
    ]
    if not deals:
        lines.append(f"本週沒有 {settings.digest_min_score:.0f} 分以上的特價。")
    for i, d in enumerate(deals, 1):
        lines.extend(_deal_block(i, d, rate, settings.web_base_url))
        lines.append("")

    if failed_runs:
        by_source = {}
        for r in failed_runs:
            by_source[r.source] = by_source.get(r.source, 0) + 1
        for src, n in by_source.items():
            lines.append(f"⚠️ 系統：{escape(source_label(src))} 本週有 {n} 次抓取異常")
    return "\n".join(lines).strip()


def _deal_block(i: int, d: Deal, rate: float, base_url: str) -> list[str]:
    s: Sailing = d.sailing
    line = s.ship.cruise_line
    star = "⭐ " if line.priority else ""
    icon = "🔥" if d.score >= 80 else "👍"
    route = s.embark_label
    if s.itinerary:
        route += " → " + " → ".join(s.itinerary_labels[:4])
    route += f" → {s.disembark_label}"
    twd = d.price_per_night * rate
    return [
        f"{icon} {i}. {star}<b>{escape(line.name)} · {escape(s.ship.name)}</b>｜{d.score:.0f} 分",
        f"   {s.depart_date:%Y-%m-%d} {escape(route)}｜{s.nights} 晚",
        f"   最低價 US${d.best_price_pp:,.0f}/人（US${d.price_per_night:,.0f}/晚 ≈ NT${twd:,.0f}）{escape(source_label(d.best_source))}",
        "   " + "｜".join(escape(r) for r in d.reasons[:3]),
        f'   <a href="{escape(d.best_url)}">訂購</a>｜<a href="{escape(base_url)}/sailing/{s.id}">走勢圖</a>',
    ]


def send_digest(session: Session, dry_run: bool = False) -> str:
    from .telegram import send_message

    settings = get_settings()
    body = build_digest(session)
    if dry_run:
        return body
    status = "sent"
    try:
        if not (settings.telegram_bot_token and settings.telegram_chat_id):
            raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set")
        send_message(settings.telegram_bot_token, settings.telegram_chat_id, body)
    except Exception as e:  # logged, then re-raised so the scheduler shows it
        status = f"failed: {e}"[:20]
        raise
    finally:
        session.add(AlertLog(sent_at=datetime.now(), channel="telegram", kind="weekly", status=status, body=body))
    return body

