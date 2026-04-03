"""
Source: https://www.ouedkniss.com/immobilier-location-vacances (SPA shell).

HTML inspection: same Vue bootstrap as other Ouedkniss routes; listings come from GraphQL.
We use categorySlug ``immobilier-location-vacances`` (validated via API). All rows are typed
``hotel`` (vacation rental / lodging). Pagination via SearchFilterInput.page.
"""

import csv
import os
import time
from typing import Dict, List

import requests

from scraping.ouedkniss_graphql_client import graphql_search, hit_to_row, new_session
from utils.helpers import ensure_directory


LOG = "[Ouedkniss immobilier-location-vacances]"


def _type_always_hotel(title: str) -> str:
    return "hotel"


def scrape_immobilier_location_vacances(max_pages: int = 8, delay_seconds: float = 2.0) -> List[Dict]:
    session = new_session()
    deduped: Dict[str, Dict] = {}

    for page in range(1, max_pages + 1):
        filt = {"categorySlug": "immobilier-location-vacances", "page": page}
        try:
            print(f"{LOG} GraphQL filter categorySlug + page={page}")
            hits = graphql_search(
                session,
                "",
                filt,
                log_prefix=LOG,
                retry_backoff_seconds=delay_seconds,
            )
            print(f"{LOG} extracted {len(hits)} rows on page {page}")
            if not hits:
                print(f"{LOG} empty page {page}, stopping pagination.")
                break
            for hit in hits:
                row = hit_to_row(hit, _type_always_hotel)
                if not row:
                    continue
                key = row["url"] or f"{row['name']}|{row['price']}"
                deduped[key] = row
            time.sleep(delay_seconds)
        except requests.RequestException as exc:
            print(f"{LOG} HTTP error page {page}: {exc}")
            break
        except Exception as exc:
            print(f"{LOG} error page {page}: {exc}")
            break

    return list(deduped.values())


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
