import csv
import os
import re
import time
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

from utils.helpers import clean_text, ensure_directory, parse_duration_to_days, parse_price


# Public OpenCart storefront (paths like /fr/ return 404 on current deployment).
OFFERS_URLS = [
    "https://onat.dz/",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


def _location_from_title(title: str) -> str:
    """Infer a coarse location from offer title (many ONAT titles are place names)."""
    t = clean_text(title)
    if not t:
        return "Unknown"
    # Strip common product words; keep last meaningful token if it looks like a place.
    lower = t.lower()
    for suffix in (" excursion", " circuit", " thermal", " village", " program", " mini"):
        if lower.endswith(suffix.strip()):
            t = clean_text(t[: -len(suffix.strip())])
            break
    parts = re.split(r"[/,]| - ", t)
    candidate = clean_text(parts[-1]) if parts else t
    return candidate if candidate else "Unknown"


def _extract_product_thumbs(soup: BeautifulSoup) -> List[Dict]:
    """Parse ONAT OpenCart listing cards (.product-thumb)."""
    records: List[Dict] = []
    for card in soup.select(".product-thumb"):
        title_el = card.select_one(".caption h4 a, h4.protitle a, .caption h4, h4 a")
        price_el = card.select_one(".price")
        if not title_el:
            continue

        name = clean_text(title_el.get_text(" ", strip=True))
        if len(name) < 3:
            continue

        blob = clean_text(card.get_text(" ", strip=True))
        price = parse_price(price_el.get_text(" ", strip=True) if price_el else blob)
        duration = parse_duration_to_days(blob)

        records.append(
            {
                "name": name,
                "location": _location_from_title(name),
                "price": price,
                "duration": duration,
            }
        )
    return records


def scrape_onat(delay_seconds: float = 2.0) -> List[Dict]:
    """Scrape ONAT offers and return raw records."""
    all_records: List[Dict] = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for url in OFFERS_URLS:
        try:
            print(f"[ONAT] Fetching: {url}")
            response = session.get(url, timeout=25)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            records = _extract_product_thumbs(soup)
            if records:
                all_records.extend(records)
                print(f"[ONAT] Parsed {len(records)} records from {url}")
            else:
                print(f"[ONAT] No product-thumb entries parsed from {url}")
            time.sleep(delay_seconds)
        except requests.RequestException as exc:
            print(f"[ONAT] Request failed for {url}: {exc}")
        except Exception as exc:
            print(f"[ONAT] Unexpected error for {url}: {exc}")

    deduped = {}
    for row in all_records:
        key = (row.get("name"), row.get("location"), row.get("price"))
        deduped[key] = row
    return list(deduped.values())


def save_onat_csv(records: List[Dict], output_path: str) -> None:
    ensure_directory(os.path.dirname(output_path))
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "location", "price", "duration"])
        writer.writeheader()
        writer.writerows(records)
    print(f"[ONAT] Saved {len(records)} rows to {output_path}")
