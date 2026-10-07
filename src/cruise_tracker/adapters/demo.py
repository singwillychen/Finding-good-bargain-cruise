"""Sample Asia sailings (made-up prices) so the UI, scoring and digest can be
tried before the real adapters are finished. Never mixed into real data:
everything it produces is tagged source="demo"."""

import json
from datetime import date, datetime, timedelta
from importlib import resources

from .base import RawPrice, RawSailing, SourceAdapter


class DemoAdapter(SourceAdapter):
    name = "demo"

    async def fetch_asia(self) -> list[RawSailing]:
        data = json.loads(resources.files("cruise_tracker").joinpath("demo_data.json").read_text())
        today = date.today()
        out: list[RawSailing] = []
        for i, s in enumerate(data):
            depart = today + timedelta(days=s["days_out"])
            # one snapshot per historical price point, oldest first
            for back, price in zip(range(len(s["history"]) - 1, -1, -1), s["history"]):
                for src, factor in s.get("sources", {"demo": 1.0}).items():
                    out.append(
                        RawSailing(
                            source=f"demo_{src}",
                            source_sailing_id=f"{src}-{i}",
                            cruise_line=s["line"],
                            ship=s["ship"],
                            depart_date=depart,
                            nights=s["nights"],
                            embark=s["embark"],
                            disembark=s.get("disembark", ""),
                            ports_of_call=s.get("ports", []),
                            url=f"https://example.com/demo/{src}/{i}",
                            prices=[
                                RawPrice(cabin, round(price * mult * factor), brochure_price_pp=round(price * mult * 2.2))
                                for cabin, mult in (("interior", 1.0), ("oceanview", 1.25), ("balcony", 1.6), ("suite", 3.0))
                            ],
                            captured_at=datetime.combine(today - timedelta(days=back * 7), datetime.min.time()),
                        )
                    )
        return out
