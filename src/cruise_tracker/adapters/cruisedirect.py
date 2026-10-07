"""CruiseDirect adapter.

Status: skeleton. The site is a JS front end; the plan is to let Playwright
load the search page and capture the JSON responses behind it. Which API
endpoint and payload fields to read has to be confirmed by
`scripts/recon.py`, which records every JSON response the page makes.
"""

import json

from .base import BrowserMixin, RawSailing, SourceAdapter

BASE = "https://www.cruisedirect.com"


class CruiseDirectAdapter(BrowserMixin, SourceAdapter):
    name = "cruisedirect"

    async def fetch_asia(self) -> list[RawSailing]:
        context = await self.open_browser()
        captured: list[dict] = []

        async def on_response(resp):
            if self.is_results_api(resp.url) and "json" in resp.headers.get("content-type", ""):
                try:
                    captured.append(await resp.json())
                except Exception:
                    pass

        try:
            page = await context.new_page()
            page.on("response", on_response)
            for url in self.asia_search_urls():
                await page.goto(url, wait_until="networkidle")
                await self.polite_pause()
            sailings: list[RawSailing] = []
            for payload in captured:
                ref = self.save_raw("api", json.dumps(payload), ext="json")
                sailings.extend(self.parse_payload(payload, ref))
            return sailings
        finally:
            await self.close_browser()

    def asia_search_urls(self) -> list[str]:
        # TODO(recon): destination=Asia search URL(s)
        raise NotImplementedError("CruiseDirect search URLs pending site recon (scripts/recon.py)")

    def is_results_api(self, url: str) -> bool:
        # TODO(recon): match the search-results API endpoint
        return False

    def parse_payload(self, payload: dict, raw_ref: str) -> list[RawSailing]:
        # TODO(recon): map API fields into RawSailing / RawPrice
        raise NotImplementedError("CruiseDirect parser pending site recon (scripts/recon.py)")
