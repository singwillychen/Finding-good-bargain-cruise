"""Deal engine: score every upcoming sailing 0-100 and explain why.

Signals (each normalised to 0..1), see docs/DESIGN.md §2.5:
  A peer      cheaper per night than similar sailings (region, length, month)
  B drop      fell vs. its own highest price in the last 30 days
  C low       at or below its lowest price since tracking began
  D gap       cheaper on one site than the other
  E brochure  site-reported discount vs. brochure fare (low weight)
  F last_min  departs within 90 days and still falling
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import normalize
from .models import Deal, PriceSnapshot, Sailing, SourceListing

WEIGHTS = {"peer": 40, "drop": 25, "low": 15, "gap": 10, "brochure": 5, "last_min": 5}
MIN_PEERS = 5


@dataclass
class PricePoint:
    source: str
    url: str
    price: float
    brochure: float | None


@dataclass
class SailingPrices:
    sailing: Sailing
    cabin: str
    current: dict[str, PricePoint]  # cheapest latest price per source
    daily_min: dict[date, float] = field(default_factory=dict)  # history across sources

    @property
    def best(self) -> PricePoint:
        return min(self.current.values(), key=lambda p: p.price)

    @property
    def per_night(self) -> float:
        return self.best.price / max(self.sailing.nights, 1)


def collect_prices(sailing: Sailing, cabins: list[str] | None = None) -> SailingPrices | None:
    """Latest price per source (cheapest of the wanted cabins) plus daily history."""
    current: dict[str, PricePoint] = {}
    daily: dict[date, float] = {}
    for listing in sailing.listings:
        latest: dict[str, PriceSnapshot] = {}
        for snap in listing.snapshots:
            if snap.restricted or (cabins and snap.cabin_type not in cabins):
                continue
            d = snap.captured_at.date()
            daily[d] = min(daily.get(d, snap.price_pp), snap.price_pp)
            if snap.cabin_type not in latest or snap.captured_at > latest[snap.cabin_type].captured_at:
                latest[snap.cabin_type] = snap
        if not latest or not listing.is_active:
            continue
        newest = max(s.captured_at for s in latest.values())
        fresh = [s for s in latest.values() if s.captured_at == newest]
        cheapest = min(fresh, key=lambda s: s.price_pp)
        current[listing.source] = PricePoint(listing.source, listing.url, cheapest.price_pp, cheapest.brochure_price_pp)
    if not current:
        return None
    cabin = "lowest" if not cabins else ",".join(cabins)
    return SailingPrices(sailing, cabin, current, daily)


def percentile_cheaper(value: float, peers: list[float]) -> float:
    """Share of peers that cost more per night than this sailing."""
    others = [p for p in peers if p is not None]
    if not others:
        return 0.0
    return sum(1 for p in others if p > value) / len(others)


def score_signals(sp: SailingPrices, peers: list[float], today: date) -> tuple[float, dict, list[str]]:
    best = sp.best
    signals: dict[str, float] = {}
    reasons: list[str] = []
    weights = dict(WEIGHTS)

    # A: peer comparison; trust it less when the peer group is small
    if len(peers) >= 1:
        pct = percentile_cheaper(sp.per_night, peers)
        signals["peer"] = pct
        if len(peers) < MIN_PEERS:
            weights["peer"] = WEIGHTS["peer"] * len(peers) / MIN_PEERS
        if pct >= 0.5:
            reasons.append(f"比 {pct:.0%} 的同類航次便宜（每晚）")
    else:
        weights["peer"] = 0
        signals["peer"] = 0

    # B: drop vs. own 30-day high
    window = [p for d, p in sp.daily_min.items() if d >= today - timedelta(days=30)]
    high = max(window) if window else best.price
    drop = (high - best.price) / high if high else 0
    signals["drop"] = min(max(drop, 0) / 0.30, 1.0)
    if drop >= 0.05:
        reasons.append(f"30 天內降 US${high - best.price:,.0f}（-{drop:.0%}）")

    # C: all-time low since tracking (needs at least 2 days of history to mean anything)
    if len(sp.daily_min) >= 2 and best.price <= min(sp.daily_min.values()) and drop > 0:
        signals["low"] = 1.0
        reasons.append("追蹤以來新低")
    else:
        signals["low"] = 0.0

    # D: cross-site gap
    if len(sp.current) >= 2:
        other = min(p.price for s, p in sp.current.items() if s != best.source)
        gap = (other - best.price) / other if other else 0
        signals["gap"] = min(max(gap, 0) / 0.15, 1.0)
        if gap >= 0.02:
            reasons.append(f"{source_label(best.source)} 比另一站便宜 US${other - best.price:,.0f}")
    else:
        weights["gap"] = 0
        signals["gap"] = 0

    # E: brochure discount
    if best.brochure and best.brochure > best.price:
        disc = 1 - best.price / best.brochure
        signals["brochure"] = min(disc / 0.70, 1.0)
    else:
        weights["brochure"] = 0
        signals["brochure"] = 0

    # F: last minute and still falling
    days_out = (sp.sailing.depart_date - today).days
    signals["last_min"] = 1.0 if days_out <= 90 and drop > 0 else 0.0
    if signals["last_min"]:
        reasons.append(f"{days_out} 天後出發，尾艙降價中")

    total_w = sum(weights.values())
    score = 100 * sum(signals[k] * weights[k] for k in weights) / total_w if total_w else 0
    return round(score, 1), signals, reasons


def peer_key_levels(s: Sailing) -> list[tuple]:
    """Peer groups from narrow to wide; we use the narrowest with enough members."""
    region = s.region.code if s.region else "other"
    band = normalize.nights_band(s.nights)
    month = s.depart_date.strftime("%Y-%m")
    asia = "asia" if (s.region and s.region.is_asia) else region
    return [("r-b-m", region, band, month), ("r-b", region, band), ("r", region), ("asia-b", asia, band)]


def compute_deals(session: Session, today: date | None = None) -> list[Deal]:
    today = today or date.today()
    sailings = session.scalars(
        select(Sailing)
        .where(Sailing.depart_date > today)
        .options(selectinload(Sailing.listings).selectinload(SourceListing.snapshots), selectinload(Sailing.region))
    ).all()

    prices = [sp for s in sailings if (sp := collect_prices(s))]
    groups: dict[tuple, list[SailingPrices]] = defaultdict(list)
    for sp in prices:
        for key in peer_key_levels(sp.sailing):
            groups[key].append(sp)

    session.query(Deal).filter(Deal.computed_on == today).delete()
    deals = []
    for sp in prices:
        peers: list[float] = []
        for key in peer_key_levels(sp.sailing):
            peers = [o.per_night for o in groups[key] if o is not sp]
            if len(peers) >= MIN_PEERS:
                break
        score, signals, reasons = score_signals(sp, peers, today)
        best = sp.best
        deal = Deal(
            sailing_id=sp.sailing.id,
            computed_on=today,
            cabin_type=sp.cabin,
            score=score,
            best_source=best.source,
            best_url=best.url,
            best_price_pp=best.price,
            price_per_night=round(sp.per_night, 2),
            reasons=reasons,
            signals={**signals, "peers": len(peers)},
        )
        session.add(deal)
        deals.append(deal)
    session.flush()
    return deals


SOURCE_LABELS = {"vtg": "Vacations To Go", "cruisedirect": "CruiseDirect"}


def source_label(source: str) -> str:
    base = source.removeprefix("demo_")
    label = SOURCE_LABELS.get(base, base)
    return f"{label}（示範）" if source.startswith("demo_") else label


def latest_deals(session: Session) -> list[Deal]:
    day = session.scalar(select(Deal.computed_on).order_by(Deal.computed_on.desc()).limit(1))
    if day is None:
        return []
    return list(
        session.scalars(
            select(Deal)
            .where(Deal.computed_on == day)
            .order_by(Deal.score.desc())
            .options(selectinload(Deal.sailing))
        )
    )

