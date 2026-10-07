from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

CABIN_TYPES = ("interior", "oceanview", "balcony", "suite")
CABIN_LABELS = {"interior": "內艙", "oceanview": "海景", "balcony": "陽台", "suite": "套房"}


class CruiseLine(Base):
    __tablename__ = "cruise_line"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    priority: Mapped[bool] = mapped_column(Boolean, default=False)  # ⭐ 關注品牌


class Ship(Base):
    __tablename__ = "ship"
    __table_args__ = (UniqueConstraint("cruise_line_id", "key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cruise_line_id: Mapped[int] = mapped_column(ForeignKey("cruise_line.id"))
    name: Mapped[str] = mapped_column(String(100))
    key: Mapped[str] = mapped_column(String(100))  # normalized name
    cruise_line: Mapped[CruiseLine] = relationship()


class Region(Base):
    __tablename__ = "region"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    is_asia: Mapped[bool] = mapped_column(Boolean, default=False)


class Port(Base):
    __tablename__ = "port"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    name_zh: Mapped[str] = mapped_column(String(100), default="")
    country: Mapped[str] = mapped_column(String(60), default="")
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    is_default_asia: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def label(self) -> str:
        return self.name_zh or self.name


class Sailing(Base):
    __tablename__ = "sailing"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_key: Mapped[str] = mapped_column(String(200), unique=True)
    ship_id: Mapped[int] = mapped_column(ForeignKey("ship.id"))
    depart_date: Mapped[date] = mapped_column(Date, index=True)
    nights: Mapped[int] = mapped_column(Integer)
    embark_port_id: Mapped[int | None] = mapped_column(ForeignKey("port.id"))
    disembark_port_id: Mapped[int | None] = mapped_column(ForeignKey("port.id"))
    region_id: Mapped[int | None] = mapped_column(ForeignKey("region.id"))
    embark_raw: Mapped[str] = mapped_column(String(200), default="")
    disembark_raw: Mapped[str] = mapped_column(String(200), default="")
    itinerary: Mapped[list] = mapped_column(JSON, default=list)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)

    ship: Mapped[Ship] = relationship()
    embark_port: Mapped[Port | None] = relationship(foreign_keys=[embark_port_id])
    disembark_port: Mapped[Port | None] = relationship(foreign_keys=[disembark_port_id])
    region: Mapped[Region | None] = relationship()
    listings: Mapped[list["SourceListing"]] = relationship(back_populates="sailing")

    @property
    def embark_label(self) -> str:
        return self.embark_port.label if self.embark_port else self.embark_raw

    @property
    def disembark_label(self) -> str:
        return self.disembark_port.label if self.disembark_port else self.disembark_raw

    @property
    def itinerary_labels(self) -> list[str]:
        from .normalize import port_label

        return [port_label(p) for p in self.itinerary]


class SourceListing(Base):
    __tablename__ = "source_listing"
    __table_args__ = (UniqueConstraint("source", "source_sailing_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    sailing_id: Mapped[int] = mapped_column(ForeignKey("sailing.id"))
    source: Mapped[str] = mapped_column(String(20))  # vtg | cruisedirect | demo
    source_sailing_id: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500), default="")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    sailing: Mapped[Sailing] = relationship(back_populates="listings")
    snapshots: Mapped[list["PriceSnapshot"]] = relationship(back_populates="listing")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshot"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("source_listing.id"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    cabin_type: Mapped[str] = mapped_column(String(20))
    price_pp: Mapped[float] = mapped_column(Float)  # USD per person, double occupancy
    taxes_fees_pp: Mapped[float | None] = mapped_column(Float, nullable=True)
    taxes_included: Mapped[str] = mapped_column(String(10), default="unknown")  # yes|no|unknown
    brochure_price_pp: Mapped[float | None] = mapped_column(Float, nullable=True)
    restricted: Mapped[bool] = mapped_column(Boolean, default=False)  # e.g. residents-only rate
    raw_ref: Mapped[str] = mapped_column(String(300), default="")

    listing: Mapped[SourceListing] = relationship(back_populates="snapshots")


class Watch(Base):
    __tablename__ = "watch"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    embark_port_ids: Mapped[list] = mapped_column(JSON, default=list)  # empty = any
    region_ids: Mapped[list] = mapped_column(JSON, default=list)
    disembark_port_ids: Mapped[list] = mapped_column(JSON, default=list)
    cruise_line_ids: Mapped[list] = mapped_column(JSON, default=list)
    cabin_types: Mapped[list] = mapped_column(JSON, default=list)  # empty = lowest available
    date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    nights_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nights_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_price_pp: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price_per_night: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Deal(Base):
    __tablename__ = "deal"
    __table_args__ = (UniqueConstraint("sailing_id", "computed_on"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    sailing_id: Mapped[int] = mapped_column(ForeignKey("sailing.id"))
    computed_on: Mapped[date] = mapped_column(Date, index=True)
    cabin_type: Mapped[str] = mapped_column(String(20))
    score: Mapped[float] = mapped_column(Float)
    best_source: Mapped[str] = mapped_column(String(20))
    best_url: Mapped[str] = mapped_column(String(500), default="")
    best_price_pp: Mapped[float] = mapped_column(Float)
    price_per_night: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    signals: Mapped[dict] = mapped_column(JSON, default=dict)

    sailing: Mapped[Sailing] = relationship()


class FxRate(Base):
    __tablename__ = "fx_rate"
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    usd_twd: Mapped[float] = mapped_column(Float)


class AlertLog(Base):
    __tablename__ = "alert_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime)
    channel: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(20))  # weekly | instant
    status: Mapped[str] = mapped_column(String(20))
    body: Mapped[str] = mapped_column(String)


class ScrapeRun(Base):
    __tablename__ = "scrape_run"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String(20), default="running")  # ok | warning | failed
