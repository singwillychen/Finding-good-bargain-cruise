from collections import defaultdict
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..db import init_db, session_scope
from ..fx import current_rate
from ..models import CABIN_LABELS, CABIN_TYPES, AlertLog, CruiseLine, Port, Region, Sailing, ScrapeRun, SourceListing, Watch
from ..scoring import latest_deals, source_label
from ..seed import seed_reference
from ..watches import deal_matches

HERE = Path(__file__).parent
templates = Jinja2Templates(directory=HERE / "templates")
templates.env.globals.update(cabin_labels=CABIN_LABELS, source_label=source_label)


def render(request: Request, name: str, rate: float, **ctx) -> HTMLResponse:
    return templates.TemplateResponse(request, name, {"rate": rate, **ctx})


def _ints(values: list[str]) -> list[int]:
    return [int(v) for v in values if v]


def create_app(scheduler: bool = False) -> FastAPI:
    app = FastAPI(title="Cruise Bargain Tracker")
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    init_db()
    with session_scope() as s:
        seed_reference(s)

    if scheduler:
        from ..scheduler import start_scheduler

        @app.on_event("startup")
        def _start():
            app.state.scheduler = start_scheduler()

    @app.get("/", response_class=HTMLResponse)
    def deals(request: Request, watch: int | None = None, priority: bool = False):
        with session_scope() as s:
            rate = current_rate(s)
            watches = s.scalars(select(Watch).order_by(Watch.id)).all()
            items = latest_deals(s)
            if watch:
                w = s.get(Watch, watch)
                items = [d for d in items if deal_matches(w, d)]
            if priority:
                items = [d for d in items if d.sailing.ship.cruise_line.priority]
            return render(request, "deals.html", rate, deals=items, watches=watches, watch_id=watch, priority=priority)

    @app.get("/sailing/{sailing_id}", response_class=HTMLResponse)
    def sailing_detail(request: Request, sailing_id: int):
        with session_scope() as s:
            rate = current_rate(s)
            sailing = s.scalar(
                select(Sailing)
                .where(Sailing.id == sailing_id)
                .options(selectinload(Sailing.listings).selectinload(SourceListing.snapshots))
            )
            series: dict[str, dict[str, float]] = defaultdict(dict)  # "source · cabin" -> day -> price
            latest: dict[tuple[str, str], float] = {}
            for listing in sailing.listings:
                for snap in sorted(listing.snapshots, key=lambda x: x.captured_at):
                    if snap.restricted:
                        continue
                    label = f"{source_label(listing.source)} · {CABIN_LABELS.get(snap.cabin_type, snap.cabin_type)}"
                    day = snap.captured_at.date().isoformat()
                    series[label][day] = min(series[label].get(day, snap.price_pp), snap.price_pp)
                    latest[(listing.source, snap.cabin_type)] = snap.price_pp
            days = sorted({d for v in series.values() for d in v})
            chart = {
                "labels": days,
                "datasets": [
                    {"label": k, "data": [v.get(d) for d in days], "hidden": not k.endswith(CABIN_LABELS["interior"])}
                    for k, v in sorted(series.items())
                ],
            }
            deal = next((d for d in latest_deals(s) if d.sailing_id == sailing_id), None)
            sources = sorted({src for src, _ in latest})
            return render(
                request, "sailing.html", rate, sailing=sailing, chart=chart, latest=latest,
                sources=sources, cabins=CABIN_TYPES, deal=deal,
            )

    @app.get("/explore", response_class=HTMLResponse)
    def explore(request: Request, sort: str = "per_night"):
        with session_scope() as s:
            rate = current_rate(s)
            items = latest_deals(s)
            key = {"per_night": lambda d: d.price_per_night, "price": lambda d: d.best_price_pp,
                   "date": lambda d: d.sailing.depart_date, "score": lambda d: -d.score}.get(sort)
            items.sort(key=key)
            return render(request, "explore.html", rate, deals=items, sort=sort)

    @app.get("/watches", response_class=HTMLResponse)
    def watches(request: Request):
        with session_scope() as s:
            rate = current_rate(s)
            return render(
                request, "watches.html", rate,
                watches=s.scalars(select(Watch).order_by(Watch.id)).all(),
                ports={p.id: p for p in s.scalars(select(Port).order_by(Port.is_default_asia.desc(), Port.country, Port.name))},
                regions={r.id: r for r in s.scalars(select(Region))},
                lines={c.id: c for c in s.scalars(select(CruiseLine).order_by(CruiseLine.priority.desc(), CruiseLine.name))},
                cabins=CABIN_TYPES, today=date.today(),
            )

    @app.post("/watches")
    def save_watch(
        name: str = Form(...),
        embark_port_ids: list[str] = Form(default=[]),
        region_ids: list[str] = Form(default=[]),
        disembark_port_ids: list[str] = Form(default=[]),
        cruise_line_ids: list[str] = Form(default=[]),
        cabin_types: list[str] = Form(default=[]),
        date_from: str = Form(""),
        date_to: str = Form(""),
        nights_min: str = Form(""),
        nights_max: str = Form(""),
        max_price_pp: str = Form(""),
        max_price_per_night: str = Form(""),
    ):
        with session_scope() as s:
            s.add(
                Watch(
                    name=name,
                    embark_port_ids=_ints(embark_port_ids),
                    region_ids=_ints(region_ids),
                    disembark_port_ids=_ints(disembark_port_ids),
                    cruise_line_ids=_ints(cruise_line_ids),
                    cabin_types=[c for c in cabin_types if c in CABIN_TYPES],
                    date_from=date.fromisoformat(date_from) if date_from else None,
                    date_to=date.fromisoformat(date_to) if date_to else None,
                    nights_min=int(nights_min) if nights_min else None,
                    nights_max=int(nights_max) if nights_max else None,
                    max_price_pp=float(max_price_pp) if max_price_pp else None,
                    max_price_per_night=float(max_price_per_night) if max_price_per_night else None,
                )
            )
        return RedirectResponse("/watches", status_code=303)

    @app.post("/watches/{watch_id}/toggle")
    def toggle_watch(watch_id: int):
        with session_scope() as s:
            w = s.get(Watch, watch_id)
            w.is_active = not w.is_active
        return RedirectResponse("/watches", status_code=303)

    @app.post("/watches/{watch_id}/delete")
    def delete_watch(watch_id: int):
        with session_scope() as s:
            s.delete(s.get(Watch, watch_id))
        return RedirectResponse("/watches", status_code=303)

    @app.get("/status", response_class=HTMLResponse)
    def status(request: Request):
        with session_scope() as s:
            rate = current_rate(s)
            runs = s.scalars(select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(30)).all()
            alerts = s.scalars(select(AlertLog).order_by(AlertLog.sent_at.desc()).limit(10)).all()
            return render(request, "status.html", rate, runs=runs, alerts=alerts)

    return app
