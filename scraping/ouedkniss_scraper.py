import csv
import os
import time
from typing import Any, Dict, List

import requests

from scraping.ouedkniss_graphql_client import graphql_search, hit_to_row, new_session
from utils.helpers import ensure_directory


HOTEL_KEYWORDS = {
    "hotel",
    "hôtel",
    "auberge",
    "residence",
    "résidence",
    "appartement",
    "villa",
    "studio",
    "hebergement",
    "hébergement",
}

OFFER_KEYWORDS = {
    "voyage",
    "package",
    "omra",
    "hajj",
    "excursion",
    "sejour",
    "séjour",
    "circuit",
    "tour",
    "sahara",
    "djanet",
    "hoggar",
}


def classify_listing(title: str) -> str:
    t = title.lower()
    if any(k in t for k in HOTEL_KEYWORDS):
        return "hotel"
    if any(k in t for k in OFFER_KEYWORDS):
        return "offer"
    return "offer"


def scrape_ouedkniss(max_pages: int = 5, delay_seconds: float = 2.0) -> List[Dict]:
    """
    Fetch Ouedkniss listings via the public GraphQL search API.

    The site shell is a JavaScript SPA; category pages do not ship listing HTML to BeautifulSoup.
    Pagination uses SearchFilterInput.page (10 results per page on the live API).
    """
    session = new_session()

    strategies: List[Dict[str, Any]] = [
        {"label": "category:voyages-voyage-organise", "q": "", "filter_base": {"categorySlug": "voyages-voyage-organise"}},
        {"label": "keyword:hotel", "q": "hotel", "filter_base": {}},
        {"label": "keyword:voyage", "q": "voyage", "filter_base": {}},
    ]

    deduped: Dict[str, Dict] = {}
    log_p = "[Ouedkniss]"

    for strat in strategies:
        for page in range(1, max_pages + 1):
            filt = dict(strat["filter_base"])
            filt["page"] = page
            try:
                print(f"{log_p} {strat['label']} page {page} ...")
                hits = graphql_search(
                    session,
                    strat["q"],
                    filt,
                    log_prefix=log_p,
                    retry_backoff_seconds=delay_seconds,
                )
                print(f"{log_p} extracted {len(hits)} rows on page {page} ({strat['label']})")
                if not hits:
                    print(f"{log_p} empty page {page} for {strat['label']}, stopping this strategy.")
                    break
                for hit in hits:
                    row = hit_to_row(hit, classify_listing)
                    if not row:
                        continue
                    key = row["url"] or f"{row['name']}|{row['price']}"
                    deduped[key] = row
                print(f"{log_p} unique total after page {page}: {len(deduped)}")
                time.sleep(delay_seconds)
            except requests.RequestException as exc:
                print(f"{log_p} HTTP error ({strat['label']} p{page}): {exc}")
                break
            except Exception as exc:
                print(f"{log_p} error ({strat['label']} p{page}): {exc}")
                break

    return list(deduped.values())


def save_ouedkniss_csv(records: List[Dict], output_path: str) -> None:
    ensure_directory(os.path.dirname(output_path))
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["name", "location", "price", "type", "url"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(records)
    print(f"[Ouedkniss] Saved {len(records)} rows to {output_path}")
