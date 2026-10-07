"""USD -> TWD from Bank of Taiwan's daily posted rates (spot buy/sell midpoint)."""

import csv
import io
from datetime import date

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import FxRate

BOT_CSV = "https://rate.bot.com.tw/xrt/flcsv/0/day"
FALLBACK_USD_TWD = 32.0


def parse_bot_csv(text: str) -> float:
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    for row in rows:
        if row and row[0].strip() == "USD":
            cells = [c.strip() for c in row]
            buy_spot = float(cells[3])
            sell_idx = cells.index("本行賣出") if "本行賣出" in cells else 11
            sell_spot = float(cells[sell_idx + 2])
            return round((buy_spot + sell_spot) / 2, 3)
    raise ValueError("USD row not found in Bank of Taiwan CSV")


def refresh_rate(session: Session) -> float:
    resp = httpx.get(BOT_CSV, timeout=20)
    resp.raise_for_status()
    rate = parse_bot_csv(resp.content.decode("utf-8-sig"))
    session.merge(FxRate(day=date.today(), usd_twd=rate))
    return rate


def current_rate(session: Session) -> float:
    row = session.scalar(select(FxRate).order_by(FxRate.day.desc()).limit(1))
    return row.usd_twd if row else FALLBACK_USD_TWD
