from typing import Optional

import pandas as pd

from utils.helpers import clean_text, parse_duration_to_days, parse_price


def _normalize_type(value: Optional[str]) -> str:
    if not value:
        return "offer"
    v = clean_text(value).lower()
    return "hotel" if v == "hotel" else "offer"


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply dedupe and normalize schema-compatible columns."""
    if df.empty:
        return df.copy()

    out = df.copy()

    if "name" in out.columns:
        out["name"] = out["name"].astype(str).map(clean_text)
    if "location" in out.columns:
        out["location"] = out["location"].astype(str).map(clean_text)
    else:
        out["location"] = "Unknown"

    out["price"] = out.get("price", pd.Series([None] * len(out))).map(parse_price)
    out["duration"] = out.get("duration", pd.Series([None] * len(out))).map(parse_duration_to_days)
    out["type"] = out.get("type", pd.Series(["offer"] * len(out))).map(_normalize_type)

    # Remove clearly unusable rows.
    out = out.dropna(subset=["name"])
    out = out[out["name"] != ""]
    out = out.dropna(subset=["price"])
    out = out[out["price"] > 0]

    out["location"] = out["location"].replace("", "Unknown")
    out["duration"] = out["duration"].fillna(1.0)

    out = out.drop_duplicates(subset=["name", "location", "price", "type"]).reset_index(drop=True)
    return out

