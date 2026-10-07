import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import get_settings
from .db import session_scope
from .notify.digest import send_digest
from .pipeline import daily_job

log = logging.getLogger(__name__)


def weekly_digest() -> None:
    with session_scope() as s:
        send_digest(s)


def start_scheduler() -> BackgroundScheduler:
    s = get_settings()
    sched = BackgroundScheduler(timezone=s.timezone)
    sched.add_job(daily_job, CronTrigger.from_crontab(s.scrape_cron, timezone=s.timezone), id="scrape", max_instances=1)
    sched.add_job(weekly_digest, CronTrigger.from_crontab(s.digest_cron, timezone=s.timezone), id="digest", max_instances=1)
    sched.start()
    log.info("scheduler started: scrape=%r digest=%r (%s)", s.scrape_cron, s.digest_cron, s.timezone)
    return sched
