"""The daily job: scrape each source, store, refresh FX, score."""

import asyncio
import logging
import traceback
from datetime import datetime

from .adapters import get_adapter
from .config import get_settings
from .db import session_scope
from .fx import refresh_rate
from .ingest import Ingestor, health_check
from .models import ScrapeRun
from .scoring import compute_deals

log = logging.getLogger(__name__)


def scrape_source(name: str) -> int:
    with session_scope() as s:
        run = ScrapeRun(source=name, started_at=datetime.now())
        s.add(run)
        s.flush()
        run_id = run.id
    items, error = [], ""
    try:
        items = asyncio.run(get_adapter(name).fetch_asia())
    except Exception:
        error = traceback.format_exc(limit=3)
        log.exception("scrape %s failed", name)
    with session_scope() as s:
        if items:
            ing = Ingestor(s)
            for raw in items:
                ing.add(raw)
        run = s.get(ScrapeRun, run_id)
        run.finished_at = datetime.now()
        run.items_found = len(items)
        if error:
            run.status, run.errors = "failed", error
        else:
            run.status, run.errors = health_check(items)
    return len(items)


def daily_job(sources: list[str] | None = None) -> None:
    for name in sources or get_settings().source_list:
        n = scrape_source(name)
        log.info("%s: %d sailings", name, n)
    with session_scope() as s:
        try:
            refresh_rate(s)
        except Exception as e:
            log.warning("FX refresh failed (%s); keeping last known rate", e)
    with session_scope() as s:
        deals = compute_deals(s)
        log.info("scored %d sailings", len(deals))
