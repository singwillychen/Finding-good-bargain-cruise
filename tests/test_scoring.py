from datetime import date, datetime, timedelta

from cruise_tracker.adapters.base import RawPrice, RawSailing
from cruise_tracker.ingest import Ingestor, health_check
from cruise_tracker.models import Watch
from cruise_tracker.scoring import compute_deals, percentile_cheaper
from cruise_tracker.watches import deal_matches

TODAY = date(2026, 10, 7)


def raw(source, sid, ship, days_out, nights, prices, days_ago=0, embark="Keelung, Taiwan", line="MSC Cruises"):
    return RawSailing(
        source=source, source_sailing_id=sid, cruise_line=line, ship=ship,
        depart_date=TODAY + timedelta(days=days_out), nights=nights, embark=embark,
        ports_of_call=["Naha, Okinawa"], url=f"https://x/{source}/{sid}",
        prices=[RawPrice(c, p) for c, p in prices.items()],
        captured_at=datetime.combine(TODAY - timedelta(days=days_ago), datetime.min.time()),
    )


def test_percentile_cheaper():
    assert percentile_cheaper(100, [120, 150, 90, 200]) == 0.75
    assert percentile_cheaper(100, []) == 0.0


def test_health_check():
    assert health_check([])[0] == "warning"
    r = raw("vtg", "1", "A", 30, 5, {})
    assert health_check([r, r])[0] == "warning"
    assert health_check([raw("vtg", "1", "A", 30, 5, {"interior": 1})])[0] == "ok"


def test_same_sailing_from_two_sites_is_merged(session):
    ing = Ingestor(session)
    a = ing.add(raw("vtg", "v1", "MSC Bellissima", 40, 5, {"interior": 500}))
    b = ing.add(raw("cruisedirect", "c9", "Bellissima", 40, 5, {"interior": 480}))
    assert a.id == b.id
    session.flush()
    assert {l.source for l in a.listings} == {"vtg", "cruisedirect"}


def test_price_drop_scores_high_and_explains(session):
    ing = Ingestor(session)
    # a falling sailing with history
    for ago, price in [(28, 800), (14, 700), (0, 450)]:
        ing.add(raw("vtg", "drop", "MSC Bellissima", 45, 5, {"interior": price, "balcony": price * 1.6}, days_ago=ago))
    ing.add(raw("cruisedirect", "drop-cd", "MSC Bellissima", 45, 5, {"interior": 520}))
    # flat peers
    for i in range(6):
        ing.add(raw("vtg", f"peer{i}", f"Ship {i}", 50 + i, 5, {"interior": 700 + i * 20}, line="Costa"))
    session.flush()
    deals = {d.sailing.ship.name: d for d in compute_deals(session, TODAY)}
    top = deals["MSC Bellissima"]
    assert top.best_price_pp == 450 and top.best_source == "vtg"
    assert top.score >= 80
    joined = " ".join(top.reasons)
    assert "追蹤以來新低" in joined and "降" in joined and "便宜" in joined
    assert all(deals[f"Ship {i}"].score < top.score for i in range(6))


def test_restricted_prices_ignored(session):
    ing = Ingestor(session)
    r = raw("vtg", "r1", "MSC Bellissima", 40, 5, {"interior": 600})
    r.prices.append(RawPrice("oceanview", 100, restricted=True))
    ing.add(r)
    session.flush()
    (deal,) = compute_deals(session, TODAY)
    assert deal.best_price_pp == 600


def test_watch_filters(session):
    ing = Ingestor(session)
    ing.add(raw("vtg", "k", "MSC Bellissima", 40, 5, {"interior": 600, "balcony": 900}))
    ing.add(raw("vtg", "s", "Spectrum of the Seas", 40, 4, {"interior": 500}, embark="Singapore", line="Royal Caribbean"))
    session.flush()
    deals = {d.sailing.ship.name: d for d in compute_deals(session, TODAY)}
    keelung = session.query(Watch).first()  # seeded: Asia default ports
    assert deal_matches(keelung, deals["MSC Bellissima"]) and deal_matches(keelung, deals["Spectrum of the Seas"])

    from cruise_tracker.models import Port

    kee = session.query(Port).filter_by(code="keelung").one()
    w = Watch(name="t", embark_port_ids=[kee.id], cabin_types=["balcony"], max_price_pp=800)
    assert not deal_matches(w, deals["MSC Bellissima"])  # balcony is 900
    w.max_price_pp = 1000
    assert deal_matches(w, deals["MSC Bellissima"])
    assert not deal_matches(w, deals["Spectrum of the Seas"])  # wrong port
