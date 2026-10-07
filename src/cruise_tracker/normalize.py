"""Turn the text the sites show into canonical keys we can compare across sources."""

import re
from datetime import date

from .reference import CRUISE_LINES, PORTS

_CABIN_PATTERNS = [
    ("suite", re.compile(r"suite|haven|yacht club|concierge|penthouse", re.I)),
    ("balcony", re.compile(r"balcon|veranda|verandah|terrace", re.I)),
    ("oceanview", re.compile(r"ocean ?view|outside|window|porthole|exterior", re.I)),
    ("interior", re.compile(r"inside|interior|inner", re.I)),
]

_SHIP_PREFIXES = re.compile(r"^(the|msc|ms|mv|m/s|ss|carnival|disney|norwegian|celebrity|star)\s+", re.I)


def cabin_type(text: str) -> str | None:
    for code, pattern in _CABIN_PATTERNS:
        if pattern.search(text or ""):
            return code
    return None


def ship_key(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"[’'`]", "", s)
    while True:
        stripped = _SHIP_PREFIXES.sub("", s)
        if stripped == s:
            break
        s = stripped
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def cruise_line_name(text: str) -> str:
    t = (text or "").lower()
    for name, _priority, aliases in CRUISE_LINES:
        if any(a in t for a in aliases):
            return name
    return (text or "").strip()


def port_code(text: str) -> str | None:
    t = (text or "").lower()
    for code, _n, _zh, _c, _r, _d, aliases in PORTS:
        if any(re.search(rf"\b{re.escape(a)}\b", t) for a in aliases):
            return code
    return None


def port_region(code: str | None) -> str | None:
    for c, _n, _zh, _country, region, _d, _a in PORTS:
        if c == code:
            return region
    return None


ASIA_REGIONS = {"japan", "korea", "taiwan", "china", "southeast_asia", "asia_other"}


def infer_region(embark: str | None, disembark: str | None, ports_of_call: list[str]) -> str:
    """Pick a region from the ports. Asia <-> elsewhere one-way sailings count as repositioning."""
    start, end = port_region(embark), port_region(disembark)
    if start and end and start != end and not {start, end} <= ASIA_REGIONS:
        return "transpacific"
    # the destination is where it stops, not where it starts; ties go to the earlier port
    counts: dict[str, int] = {}
    for p in [port_code(x) for x in ports_of_call]:
        r = port_region(p)
        if r:
            counts[r] = counts.get(r, 0) + 1
    if counts:
        return max(counts, key=counts.get)
    return end or start or "other"


def match_key(line: str, ship: str, depart: date, nights: int) -> str:
    return f"{cruise_line_name(line).lower()}|{ship_key(ship)}|{depart.isoformat()}|{nights}"


def nights_band(nights: int) -> str:
    if nights <= 4:
        return "2-4"
    if nights <= 7:
        return "5-7"
    if nights <= 10:
        return "8-10"
    if nights <= 14:
        return "11-14"
    return "15+"


def parse_money(text: str) -> float | None:
    m = re.search(r"\$?\s*([\d,]+(?:\.\d+)?)", text or "")
    return float(m.group(1).replace(",", "")) if m else None


def port_label(text: str) -> str:
    """Chinese label for a known port, otherwise the site's text up to the first comma."""
    code = port_code(text)
    for c, _n, zh, *_ in PORTS:
        if c == code:
            return zh
    return (text or "").split(",")[0].strip()
