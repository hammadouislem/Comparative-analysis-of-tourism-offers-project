"""
Source: https://www.petitfute.com/p136-algerie/

HTML inspection: responses from this environment return Cloudflare ``Attention Required`` (403)
with no destination content. When HTTP 200 is received elsewhere, this module uses **Petit Futé
specific** selectors (not shared with ss-travel / tourismalgeria):

- ``ul.pfu-grid li article`` cards
- title: ``h2 a`` or ``h3 a``
- location line: ``span.pfu-card__location`` (if present)
- price-like tokens: regex on card text (EUR / DZD)

If blocked, the scraper logs the status and writes only a header row via ``save_csv`` callers.
"""

import csv
import os
import time
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from utils.helpers import clean_text, ensure_directory, parse_price

LOG = "[Petit Futé Algérie]"
START_URL = "https://www.petitfute.com/p136-algerie/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/",
}


def scrape_petitfute_algerie(max_pages: int = 4, delay_seconds: float = 2.5) -> List[Dict]:
    session = requests.Session()
    session.headers.update(HEADERS)
    records: List[Dict] = []

    for page in range(1, max_pages + 1):
        url = START_URL if page == 1 else urljoin(START_URL, f"?page={page}")
        try:
            print(f"{LOG} GET page {page}: {url}")
            r = session.get(url, timeout=35)
            print(f"{LOG} HTTP {r.status_code}, bytes={len(r.text)}")
            if r.status_code == 403:
                print(f"{LOG} blocked (likely Cloudflare); stopping pagination.")
                break
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            cards = soup.select("ul.pfu-grid li article")
            if not cards:
                cards = soup.select("article.pfu-card")
            print(f"{LOG} extracted {len(cards)} card nodes on page {page} (Petit Futé grid selectors)")
            if not cards:
                print(f"{LOG} no cards; stopping pagination.")
                break

            for art in cards:
                title_el = art.select_one("h2 a, h3 a, a.pfu-card__title")
                loc_el = art.select_one("span.pfu-card__location, .pfu-card__subtitle")
                name = clean_text(title_el.get_text(" ", strip=True) if title_el else "")
                if len(name) < 3:
                    continue
                loc = clean_text(loc_el.get_text(" ", strip=True) if loc_el else "Algeria")
                blob = clean_text(art.get_text(" ", strip=True))
                price = parse_price(blob)
                href = ""
                if title_el and title_el.get("href"):
                    href = urljoin(START_URL, title_el["href"])
                row = {
                    "name": name,
                    "location": loc,
                    "price": price,
                    "type": "offer",
                    "url": href,
                }
                if price is not None:
                    records.append(row)
        except requests.RequestException as exc:
            print(f"{LOG} page {page} error: {exc}")
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
