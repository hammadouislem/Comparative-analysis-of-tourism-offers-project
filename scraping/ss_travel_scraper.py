"""
Source: https://ss-travel.dz

HTML inspection: marketing landing page with static package cards (not WordPress/WooCommerce).
Structure: ``div.pkg-card`` with ``.pkg-name``, ``.pkg-duration``, ``.pkg-price`` (DZD/pers.).
No server-side pagination on the homepage; one HTTP page = one logical "page" of results.
"""

import csv
import os
import time
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

from utils.helpers import clean_text, ensure_directory, parse_duration_to_days, parse_price

BASE = "https://ss-travel.dz/"
LOG = "[SS-Travel]"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


def scrape_ss_travel(delay_seconds: float = 2.0) -> List[Dict]:
    session = requests.Session()
    session.headers.update(HEADERS)
    records: List[Dict] = []

    print(f"{LOG} GET {BASE} (single page)")
    try:
        r = session.get(BASE, timeout=35)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("div.pkg-card")
        print(f"{LOG} extracted {len(cards)} rows on page 1 (selector: div.pkg-card)")
        for card in cards:
            name_el = card.select_one("div.pkg-name")
            price_el = card.select_one("div.pkg-price")
            dur_el = card.select_one("div.pkg-duration")
            name = clean_text(name_el.get_text(" ", strip=True) if name_el else "")
            if len(name) < 3:
                continue
            blob = clean_text(price_el.get_text(" ", strip=True) if price_el else "")
            price = parse_price(blob.replace("/pers.", "").replace("pers.", ""))
            duration = parse_duration_to_days(dur_el.get_text(" ", strip=True) if dur_el else None)
            records.append(
                {
                    "name": name,
                    "location": "Algeria",
                    "price": price,
                    "duration": duration,
                    "type": "offer",
                    "url": BASE + "#packages",
                }
            )
    except requests.RequestException as exc:
        print(f"{LOG} request failed: {exc}")
    except Exception as exc:
        print(f"{LOG} parse error: {exc}")

    time.sleep(delay_seconds)
    return [r for r in records if r.get("price") is not None]


def save_csv(records: List[Dict], output_path: str) -> None:
    ensure_directory(os.path.dirname(output_path))
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["name", "location", "price", "duration", "type", "url"],
            extrasaction="ignore",
        )
        w.writeheader()
        w.writerows(records)
    print(f"{LOG} saved {len(records)} rows -> {output_path}")
