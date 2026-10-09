"""Site recon: record what the cruise sites actually send, so the adapters can be finished.

Run it on any computer that can reach the sites (your PC, or the NAS):

    pip install playwright && playwright install chromium
    python scripts/recon.py            # opens a browser window

A Chromium window opens on Vacations To Go. Use the site like a person:
  1. search for Asia cruises (e.g. destination Asia / departure Keelung)
  2. open one result's detail page
  3. (VTG) log in and open the 90-Day Ticker
  4. go to CruiseDirect and repeat steps 1-2
Then come back to this terminal and press Enter.

Everything lands in recon_output/: every page's HTML + screenshot, and every
JSON response the pages loaded (that's where CruiseDirect's prices live).
Passwords typed into forms are NOT recorded (only responses are saved,
request bodies are not). Zip the folder and send it back / commit it.
"""

import argparse
import json
import re
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

START = ["https://www.vacationstogo.com/", "https://www.cruisedirect.com/"]
OUT = Path("recon_output")
# never keep responses from login/account endpoints: they can carry session tokens
SKIP = re.compile(r"login|logon|signin|sign-in|auth|token|session|account|password", re.I)


def slug(url: str) -> str:
    u = urlparse(url)
    return re.sub(r"[^A-Za-z0-9]+", "_", f"{u.netloc}{u.path}?{u.query}")[:150]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true", help="no window: just capture the start pages + robots.txt")
    ap.add_argument("--start", action="append", help=argparse.SUPPRESS)  # testing only
    args = ap.parse_args()
    start = args.start or START
    OUT.mkdir(exist_ok=True)
    (OUT / "json").mkdir(exist_ok=True)
    (OUT / "pages").mkdir(exist_ok=True)
    index = []
    seen_pages = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        ctx = browser.new_context(locale="en-US", viewport={"width": 1366, "height": 900})

        def on_response(resp):
            ctype = resp.headers.get("content-type", "")
            if "json" not in ctype or SKIP.search(resp.url):
                return
            try:
                body = resp.json()
            except Exception:
                return
            name = f"{int(time.time() * 1000)}_{slug(resp.url)}.json"
            (OUT / "json" / name).write_text(json.dumps(body, indent=1, ensure_ascii=False), encoding="utf-8")
            index.append({"kind": "json", "url": resp.url, "method": resp.request.method, "file": name})

        def snapshot(page):
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            key = page.url
            if key in seen_pages:
                return
            seen_pages.add(key)
            name = f"{int(time.time() * 1000)}_{slug(page.url)}"
            (OUT / "pages" / f"{name}.html").write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(OUT / "pages" / f"{name}.png"), full_page=True)
            index.append({"kind": "page", "url": page.url, "file": name})
            print("captured", page.url)

        ctx.on("response", on_response)
        ctx.on("page", lambda p: p.on("load", lambda: snapshot(p)))

        for site in start:
            try:
                robots = ctx.request.get(site.rstrip("/") + "/robots.txt")
                (OUT / f"robots_{slug(site)}.txt").write_text(robots.text(), encoding="utf-8")
            except Exception as e:
                print("robots.txt failed:", site, e)

        page = ctx.new_page()
        page.on("load", lambda: snapshot(page))
        for url in start:
            page.goto(url, wait_until="domcontentloaded")
            snapshot(page)
        if not args.headless:
            page.goto(start[0])
            print(
                "\n請在跳出的瀏覽器中操作：\n"
                "  1. Vacations To Go：搜尋亞洲航線（例如目的地 Asia、出發港 Keelung）\n"
                "  2. 點開其中一筆航次的詳細頁\n"
                "  3. 登入 VTG，打開 90-Day Ticker\n"
                "  4. 到 cruisedirect.com 重複 1、2\n"
            )
            input("全部做完後，回到這個視窗按 Enter（瀏覽器會自動關閉）... ")
        browser.close()

    (OUT / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")
    archive = shutil.make_archive("recon_output", "zip", OUT)
    print(f"\n完成：共 {len(index)} 筆。請把這個檔案傳回來：{Path(archive).resolve()}")


if __name__ == "__main__":
    main()
