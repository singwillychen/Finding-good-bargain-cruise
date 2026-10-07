import asyncio

from fastapi.testclient import TestClient

from cruise_tracker.adapters.demo import DemoAdapter
from cruise_tracker.ingest import Ingestor
from cruise_tracker.notify.digest import build_digest
from cruise_tracker.scoring import compute_deals


def test_demo_end_to_end(session):
    ing = Ingestor(session)
    for r in asyncio.run(DemoAdapter().fetch_asia()):
        ing.add(r)
    session.flush()
    deals = compute_deals(session)
    assert len(deals) == 18
    session.commit()

    text = build_digest(session)
    assert "本週郵輪特價" in text and "⭐" in text
    assert text.count("分\n") <= 5

    from cruise_tracker.web.app import create_app

    client = TestClient(create_app())
    for path in ["/", "/explore", "/watches", "/status", f"/sailing/{deals[0].sailing_id}", "/?priority=true"]:
        resp = client.get(path)
        assert resp.status_code == 200, path
    assert "data-twd" in client.get("/").text

    resp = client.post("/watches", data={"name": "基隆 5 晚內", "nights_max": "5", "cabin_types": ["interior"]}, follow_redirects=False)
    assert resp.status_code == 303
    assert "基隆 5 晚內" in client.get("/watches").text
