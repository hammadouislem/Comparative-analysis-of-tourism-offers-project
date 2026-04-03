"""
Source: https://www.ouedkniss.com/voyages-tourisme (SPA shell).

HTML inspection: initial document is a Vue shell (~6KB) with no listing cards.
Data is loaded from the public GraphQL API. We target category slug ``voyages``
(API returns results for this slug; path ``voyages-tourisme`` has no separate slug in tests)
plus keyword searches for broader coverage. Selectors differ from other Ouedkniss scrapers.
"""

import csv
import os
import time
from typing import Any, Dict, List

import requests

from scraping.ouedkniss_graphql_client import graphql_search, hit_to_row, new_session
from utils.helpers import ensure_directory


LOG = "[Ouedkniss voyages-tourisme]"


def _type_always_offer(title: str) -> str:
    return "offer"


def scrape_ouedkniss_voyages_tourisme(max_pages: int = 5, delay_seconds: float = 2.0) -> List[Dict]:
    session = new_session()
    strategies: List[Dict[str, Any]] = [
        {
            "label": "graphql categorySlug=voyages (maps www /voyages-tourisme hub)",
            "q": "",
            "filter_base": {"categorySlug": "voyages"},
        },
        {"label": "keyword tourisme", "q": "tourisme", "filter_base": {}},
        {"label": "keyword voyage organisé", "q": "voyage organisé", "filter_base": {}},
    ]

    deduped: Dict[str, Dict] = {}

    for strat in strategies:
        for page in range(1, max_pages + 1):
            filt = dict(strat["filter_base"])
            filt["page"] = page
            try:
                print(f"{LOG} {strat['label']} - page {page}")
                hits = graphql_search(
                    session,
                    strat["q"],
                    filt,
                    log_prefix=LOG,
                    retry_backoff_seconds=delay_seconds,
                )
                print(f"{LOG} extracted {len(hits)} rows on page {page}")
                if not hits:
                    print(f"{LOG} empty page {page}, stopping this strategy.")
                    break
                for hit in hits:
                    row = hit_to_row(hit, _type_always_offer)
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
