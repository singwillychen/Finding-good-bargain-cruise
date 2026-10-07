"""Vacations To Go adapter.

Status: skeleton. The page structure (search URL parameters, result table
layout, login form) still has to be confirmed by running
`scripts/recon.py` against the live site; the TODOs below mark the parts
that depend on it. Everything around it (login, polite pacing, raw page
archive, output format) is in place.
"""

from ..config import get_settings
from .base import BrowserMixin, RawSailing, SourceAdapter

BASE = "https://www.vacationstogo.com"


class VacationsToGoAdapter(BrowserMixin, SourceAdapter):
    name = "vtg"

    async def fetch_asia(self) -> list[RawSailing]:
        context = await self.open_browser()
        try:
            page = await context.new_page()
            await self.login(page)
            sailings: list[RawSailing] = []
            for url in self.asia_search_urls():
                await page.goto(url, wait_until="domcontentloaded")
                html = await page.content()
                ref = self.save_raw("search", html)
                sailings.extend(self.parse_results(html, ref))
                await self.polite_pause()
            return sailings
        finally:
            await self.close_browser()

    async def login(self, page) -> None:
        s = get_settings()
        if not (s.vtg_email and s.vtg_password):
            return  # public pages still work; the 90-Day Ticker needs a login
        # TODO(recon): confirm login URL and form field selectors
        raise NotImplementedError("VTG login selectors pending site recon (scripts/recon.py)")

    def asia_search_urls(self) -> list[str]:
        # TODO(recon): build the destination=Asia search URLs (and 90-Day Ticker URL)
        raise NotImplementedError("VTG search URLs pending site recon (scripts/recon.py)")

    def parse_results(self, html: str, raw_ref: str) -> list[RawSailing]:
        # TODO(recon): parse result rows into RawSailing / RawPrice
        raise NotImplementedError("VTG result parser pending site recon (scripts/recon.py)")
