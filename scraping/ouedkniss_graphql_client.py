"""
Shared Ouedkniss GraphQL transport only (no site-specific pagination rules).

Listing pages are a JS SPA; data is loaded via https://api.ouedkniss.com/graphql .
"""

import time
from typing import Any, Callable, Dict, List, Optional

import requests

from utils.helpers import clean_text

BASE_WEB = "https://www.ouedkniss.com"
GRAPHQL_URL = "https://api.ouedkniss.com/graphql"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Content-Type": "application/json",
}

SEARCH_QUERY = """
query SearchAnnouncements($q: String!, $filter: SearchFilterInput) {
  search(q: $q, filter: $filter) {
    announcements {
      data {
        id
        title
        price
        slug
        description
        category {
          name
          slug
        }
        store {
          id
          name
          slug
        }
      }
    }
  }
}
"""


def new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    return s


def announcement_url(announcement_id: str) -> str:
    return f"{BASE_WEB}/annonces/{announcement_id.strip()}"


def hit_to_row(hit: Dict[str, Any], listing_type_fn: Callable[[str], str]) -> Optional[Dict[str, Any]]:
    title = clean_text(hit.get("title") or "")
    store = hit.get("store") or {}
    store_name = clean_text(store.get("name") or "")
    category = hit.get("category") or {}
    category_name = clean_text(category.get("name") or "")

    location_parts = [p for p in (store_name, category_name) if p]
    location = location_parts[0] if location_parts else "Unknown"

    price = hit.get("price")
    try:
        price_val = float(price) if price is not None else None
    except (TypeError, ValueError):
        price_val = None

    aid = str(hit.get("id") or "").strip()
    if not title or price_val is None:
        return None

    return {
        "name": title,
        "location": location,
        "price": price_val,
        "type": listing_type_fn(title),
        "url": announcement_url(aid) if aid else "",
        "slug": clean_text(hit.get("slug") or ""),
    }


def graphql_search(
    session: requests.Session,
    query_text: str,
    filter_payload: Optional[Dict[str, Any]],
    *,
    log_prefix: str,
    retries: int = 3,
    retry_backoff_seconds: float = 2.0,
) -> List[Dict[str, Any]]:
    body = {
        "query": SEARCH_QUERY,
        "variables": {"q": query_text, "filter": filter_payload},
    }
    payload: Optional[Dict[str, Any]] = None
    for attempt in range(1, retries + 1):
        try:
            response = session.post(GRAPHQL_URL, json=body, timeout=30)
            response.raise_for_status()
            payload = response.json()
            break
        except (requests.RequestException, ValueError) as exc:
            if attempt == retries:
                raise
            wait = retry_backoff_seconds * attempt
            print(f"{log_prefix} retry {attempt}/{retries}: {exc}")
            time.sleep(wait)
    if not payload:
        raise RuntimeError("GraphQL request failed with no response payload")
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0].get("message", "GraphQL error"))
    data = payload.get("data", {}).get("search", {}).get("announcements", {}).get("data", [])
    return data or []
