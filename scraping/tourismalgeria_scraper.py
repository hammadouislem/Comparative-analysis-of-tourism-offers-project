"""
Source: https://www.tourismalgeria.com

HTML inspection (hotel.html, index.html):
- Bootstrap / static pages with a custom element ``<dz-hotel-comparator>`` in Shadow DOM.
- Live hotel rows are meant to load from ``data-src`` pointing at JSON; when empty, the site
  falls back to embedded demo data inside JavaScript (not executed by requests).
- We only ingest **remote JSON** linked from ``data-src`` if it is an http(s) URL and rows
  contain a **DZD** price field. We skip EUR-only demo snippets to avoid wrong currency in the
  unified schema.
"""

import csv
import json
import os
import re
import time
from typing import Any, Dict, List, Optional
import requests

from utils.helpers import clean_text, ensure_directory

LOG = "[TourismAlgeria]"
BASE = "https://www.tourismalgeria.com/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
}

SEED_PAGES = [
    f"{BASE}hotel.html",
    f"{BASE}index.html",
    f"{BASE}algeria-resorts.html",
]


def _extract_json_hrefs(html: str) -> List[str]:
    hrefs: List[str] = []
    for m in re.finditer(
        r"<dz-hotel-comparator[^>]*\sdata-src\s*=\s*[\"']([^\"']+)[\"']",
        html,
        flags=re.IGNORECASE,
    ):
        u = m.group(1).strip()
        if u.startswith("http://") or u.startswith("https://"):
            hrefs.append(u)
    return list(dict.fromkeys(hrefs))


def _row_from_hotel_obj(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    name = clean_text(str(obj.get("name") or ""))
    city = clean_text(str(obj.get("city") or ""))
    if len(name) < 2:
        return None

    price = None
    for key in ("minPriceDzd", "minPriceDZD", "priceDzd", "price_dzd", "dzd", "price"):
        v = obj.get(key)
        if v is not None:
            try:
                price = float(v)
                break
            except (TypeError, ValueError):
                continue
    if price is None or price <= 0:
        return None

    return {
        "name": name,
        "location": city or "Algeria",
        "price": price,
        "type": "hotel",
        "url": SEED_PAGES[0],
    }


def scrape_tourismalgeria(delay_seconds: float = 2.0) -> List[Dict]:
    session = requests.Session()
    session.headers.update(HEADERS)
    records: List[Dict] = []
    seen_json: set = set()

    for page_idx, page_url in enumerate(SEED_PAGES, start=1):
        try:
            print(f"{LOG} GET seed page {page_idx}: {page_url}")
            r = session.get(page_url, timeout=35)
            r.raise_for_status()
            json_urls = _extract_json_hrefs(r.text)
            print(f"{LOG} found {len(json_urls)} data-src JSON URL(s) on page {page_idx}")
            for ju in json_urls:
                if ju in seen_json:
                    continue
                seen_json.add(ju)
                try:
                    print(f"{LOG} GET JSON: {ju}")
                    jr = session.get(ju, timeout=35)
                    jr.raise_for_status()
                    data = jr.json()
                    rows = data if isinstance(data, list) else data.get("hotels") or data.get("data") or []
                    if not isinstance(rows, list):
                        continue
                    n_ok = 0
                    for item in rows:
                        if not isinstance(item, dict):
                            continue
                        row = _row_from_hotel_obj(item)
                        if row:
                            records.append(row)
                            n_ok += 1
                    print(f"{LOG} extracted {n_ok} priced rows (DZD) from JSON page {page_idx}")
                except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
                    print(f"{LOG} JSON fetch/parse failed ({ju}): {exc}")
                time.sleep(delay_seconds)
        except requests.RequestException as exc:
            print(f"{LOG} seed page failed {page_url}: {exc}")
        time.sleep(delay_seconds)

    if not records:
        print(
            f"{LOG} no DZD hotel JSON discovered (empty data-src or EUR-only demo). "
            "See module docstring."
        )
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
