"""Store adapter output: sailings, per-source listings, and price snapshots."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import normalize
from .adapters.base import RawSailing
from .models import CruiseLine, Port, PriceSnapshot, Region, Sailing, Ship, SourceListing


class Ingestor:
    def __init__(self, session: Session):
        self.s = session
        self.lines = {c.name: c for c in session.scalars(select(CruiseLine))}
        self.ports = {p.code: p for p in session.scalars(select(Port))}
        self.regions = {r.code: r for r in session.scalars(select(Region))}
        self.ships: dict[tuple[int, str], Ship] = {(sh.cruise_line_id, sh.key): sh for sh in session.scalars(select(Ship))}

    def _line(self, text: str) -> CruiseLine:
        name = normalize.cruise_line_name(text)
        if name not in self.lines:
            self.lines[name] = CruiseLine(name=name)
            self.s.add(self.lines[name])
            self.s.flush()
        return self.lines[name]

    def _ship(self, line: CruiseLine, name: str) -> Ship:
        key = (line.id, normalize.ship_key(name))
        if key not in self.ships:
            self.ships[key] = Ship(cruise_line_id=line.id, name=name.strip(), key=key[1])
            self.s.add(self.ships[key])
            self.s.flush()
        return self.ships[key]

    def add(self, raw: RawSailing) -> Sailing:
        now = raw.captured_at or datetime.now()
        line = self._line(raw.cruise_line)
        ship = self._ship(line, raw.ship)
        embark = normalize.port_code(raw.embark)
        disembark = normalize.port_code(raw.disembark) if raw.disembark else embark
        region = normalize.infer_region(embark, disembark, raw.ports_of_call)

        key = normalize.match_key(line.name, raw.ship, raw.depart_date, raw.nights)
        sailing = self.s.scalar(select(Sailing).where(Sailing.match_key == key))
        if sailing is None:
            sailing = Sailing(
                match_key=key,
                ship_id=ship.id,
                depart_date=raw.depart_date,
                nights=raw.nights,
                embark_port_id=self.ports[embark].id if embark else None,
                disembark_port_id=self.ports[disembark].id if disembark else None,
                region_id=self.regions[region].id,
                embark_raw=raw.embark,
                disembark_raw=raw.disembark or raw.embark,
                itinerary=raw.ports_of_call,
            )
            self.s.add(sailing)
            self.s.flush()
        elif embark and sailing.embark_port_id and self.ports[embark].id != sailing.embark_port_id:
            # same ship/date/length but a different port: don't merge silently
            sailing.needs_review = True

        listing = self.s.scalar(
            select(SourceListing).where(
                SourceListing.source == raw.source, SourceListing.source_sailing_id == raw.source_sailing_id
            )
        )
        if listing is None:
            listing = SourceListing(
                sailing_id=sailing.id,
                source=raw.source,
                source_sailing_id=raw.source_sailing_id,
                url=raw.url,
                first_seen_at=now,
                last_seen_at=now,
            )
            self.s.add(listing)
            self.s.flush()
        listing.last_seen_at = max(listing.last_seen_at, now)
        listing.is_active = True
        listing.url = raw.url or listing.url

        for p in raw.prices:
            self.s.add(
                PriceSnapshot(
                    listing_id=listing.id,
                    captured_at=now,
                    cabin_type=p.cabin_type,
                    price_pp=p.price_pp,
                    taxes_fees_pp=p.taxes_fees_pp,
                    taxes_included=p.taxes_included,
                    brochure_price_pp=p.brochure_price_pp,
                    restricted=p.restricted,
                    raw_ref=raw.raw_ref,
                )
            )
        return sailing


def health_check(items: list[RawSailing]) -> tuple[str, str]:
    """Flag a run that looks like the site changed instead of storing garbage quietly."""
    if not items:
        return "warning", "0 sailings found: the site may have changed or blocked us"
    no_price = sum(1 for i in items if not i.prices)
    if no_price / len(items) > 0.5:
        return "warning", f"{no_price}/{len(items)} sailings had no price: parser may be out of date"
    return "ok", ""
