import asyncio
import gzip
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from ..config import get_settings


@dataclass
class RawPrice:
    cabin_type: str  # interior | oceanview | balcony | suite
    price_pp: float  # USD per person, double occupancy
    taxes_fees_pp: float | None = None
    taxes_included: str = "unknown"
    brochure_price_pp: float | None = None
    restricted: bool = False


@dataclass
class RawSailing:
    source: str
    source_sailing_id: str
    cruise_line: str
    ship: str
    depart_date: date
    nights: int
    embark: str
    disembark: str = ""  # empty = round trip
    ports_of_call: list[str] = field(default_factory=list)
    url: str = ""
    prices: list[RawPrice] = field(default_factory=list)
    raw_ref: str = ""
    captured_at: datetime | None = None  # only set by the demo adapter


class SourceAdapter(ABC):
    name: str

    @abstractmethod
    async def fetch_asia(self) -> list[RawSailing]:
        """Return every Asia sailing the source lists right now."""

    async def polite_pause(self) -> None:
        s = get_settings()
        await asyncio.sleep(random.uniform(s.request_delay_min, s.request_delay_max))

    def save_raw(self, kind: str, content: str | bytes, ext: str = "html") -> str:
        """Keep the original page so a broken parser can be re-run later."""
        s = get_settings()
        folder: Path = s.raw_dir / self.name / datetime.now().strftime("%Y-%m-%d")
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{datetime.now():%H%M%S}-{kind}.{ext}.gz"
        data = content.encode() if isinstance(content, str) else content
        path.write_bytes(gzip.compress(data))
        return str(path.relative_to(s.data_dir))


class BrowserMixin:
    """Shared headless Chromium session (Playwright)."""

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    )

    async def open_browser(self):
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)
        self._context = await self._browser.new_context(user_agent=self.USER_AGENT, locale="en-US")
        return self._context

    async def close_browser(self):
        await self._context.close()
        await self._browser.close()
        await self._pw.stop()
