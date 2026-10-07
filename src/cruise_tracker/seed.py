from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CruiseLine, Port, Region, Watch
from .reference import CRUISE_LINES, PORTS, REGIONS


def seed_reference(session: Session) -> None:
    regions = {r.code: r for r in session.scalars(select(Region))}
    for code, name, is_asia in REGIONS:
        if code not in regions:
            session.add(Region(code=code, name=name, is_asia=is_asia))

    ports = {p.code: p for p in session.scalars(select(Port))}
    for code, name, zh, country, _region, default_asia, aliases in PORTS:
        p = ports.get(code) or Port(code=code)
        p.name, p.name_zh, p.country, p.aliases, p.is_default_asia = name, zh, country, aliases, default_asia
        session.add(p)

    lines = {c.name: c for c in session.scalars(select(CruiseLine))}
    for name, priority, _aliases in CRUISE_LINES:
        if name not in lines:
            session.add(CruiseLine(name=name, priority=priority))
    session.flush()

    if session.scalar(select(Watch).limit(1)) is None:
        default_ports = session.scalars(select(Port.id).where(Port.is_default_asia)).all()
        session.add(
            Watch(
                name="亞洲出發（台／日／韓／星）",
                embark_port_ids=list(default_ports),
                date_from=date.today(),
                date_to=date.today() + timedelta(days=365),
            )
        )
