"""
Source: https://traveldzair.com

DNS / connectivity is probed for several host variants. HTML structure (when available) is
parsed with selectors **not** used on ss-travel or tourismalgeria: prefer ``article.post``,
then ``div.post-item``, then ``h2.entry-title a`` as a link-only fallback.
"""

import csv
import os
import time
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from utils.helpers import clean_text, ensure_directory, parse_price

LOG = "[Traveldzair]"

CANDIDATE_URLS = [
    "https://traveldzair.com/",
    "https://www.traveldzair.com/",
    "http://traveldzair.com/",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


def _pick_base(session: requests.Session) -> str:
    for u in CANDIDATE_URLS:
        try:
            print(f"{LOG} probing {u}")
            r = session.get(u, timeout=20, allow_redirects=True)
            if 200 <= r.status_code < 400:
                base = r.url.split("#")[0]
                if not base.endswith("/"):
                    base = base + "/"
                print(f"{LOG} resolved base: {base}")
                return base
            print(f"{LOG} HTTP {r.status_code} for {u}")
        except requests.RequestException as exc:
            print(f"{LOG} unreachable {u}: {exc}")
            time.sleep(1.5)
    return ""


def scrape_traveldzair(max_pages: int = 3, delay_seconds: float = 2.0) -> List[Dict]:
    session = requests.Session()
    session.headers.update(HEADERS)
    base = _pick_base(session)
    if not base:
        print(f"{LOG} no reachable host; 0 rows.")
        return []

    records: List[Dict] = []
    for page in range(1, max_pages + 1):
        url = base if page == 1 else urljoin(base, f"?paged={page}")
        try:
            print(f"{LOG} GET page {page}: {url}")
            r = session.get(url, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            items = []
            chosen = ""
            for sel in ("article.post", "div.post-item", "div.post"):
                found = soup.select(sel)
                if found:
                    items = found
                    chosen = sel
                    break
            if items:
                print(f"{LOG} page {page}: using item selector '{chosen}' ({len(items)} nodes)")
                n = 0
                for art in items:
                    title_el = art.select_one("h2.entry-title a, h2 a, h3.post-title a")
                    blob = clean_text(art.get_text(" ", strip=True))
                    name = clean_text(title_el.get_text(" ", strip=True) if title_el else "") or blob[:100]
                    if len(name) < 3:
                        continue
                    link = urljoin(base, title_el["href"]) if title_el and title_el.get("href") else ""
                    price = parse_price(blob)
                    if price is None:
                        continue
                    records.append(
                        {
                            "name": name,
                            "location": "Algeria",
                            "price": price,
                            "type": "offer",
                            "url": link,
                        }
                    )
                    n += 1
                print(f"{LOG} extracted {n} priced rows on page {page}")
                if n == 0:
                    print(f"{LOG} no priced rows on page {page}; stopping.")
                    break
            else:
                links = soup.select("h2.entry-title a")
                print(f"{LOG} page {page}: fallback selector 'h2.entry-title a' -> {len(links)} links (no prices)")
                if not links:
                    print(f"{LOG} nothing to parse; stopping pagination.")
                    break
        except requests.RequestException as exc:
            print(f"{LOG} page {page} failed: {exc}")
            break
        time.sleep(delay_seconds)

    return records


def save_csv(records: List[Dict], output_path: str) -> None:
    ensure_directory(os.path.dirname(output_path))
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["name", "location", "price", "type", "url"],
            extrasaction="ignore",
        )
        w.writeheader()
        w.writerows(records)
    print(f"{LOG} saved {len(records)} rows -> {output_path}")
