import os
from typing import List, Tuple

import numpy as np
import pandas as pd

from processing.clean_data import clean_dataframe
from utils.helpers import ensure_directory

RawSource = Tuple[str, str]  # (csv_path, source_id)


def _normalize_for_concat(df: pd.DataFrame) -> pd.DataFrame:
    """Align dtypes before concat to avoid pandas FutureWarnings on all-NA/object columns."""
    out = df.copy()
    out["price"] = pd.to_numeric(out["price"], errors="coerce")
    out["duration"] = pd.to_numeric(out["duration"], errors="coerce")
    out["rating"] = pd.Series(np.nan, index=out.index, dtype="float64")
    return out


def merge_and_clean(raw_sources: List[RawSource], output_path: str) -> pd.DataFrame:
    """
    Concatenate multiple raw CSV exports (same logical columns) then clean.

    raw_sources: list of (path, source_id) e.g. ("data/raw_onat.csv", "onat").

    Each CSV should have at least: name, location, price.
    Optional: type, duration, url. Column ``source`` is injected from source_id.
    """
    base_cols = ["name", "type", "location", "price", "duration", "source"]
    unified_cols = base_cols + ["rating"]
    chunks = []

    for path, source_id in raw_sources:
        if not os.path.isfile(path):
            print(f"[Merge] Skip missing file: {path}")
            continue
        try:
            df = pd.read_csv(path)
        except (pd.errors.EmptyDataError, FileNotFoundError) as exc:
            print(f"[Merge] Skip unreadable {path}: {exc}")
            continue
        if df.empty:
            print(f"[Merge] Skip empty: {path}")
            continue
        if "type" not in df.columns:
            df["type"] = "offer"
        if "duration" not in df.columns:
            df["duration"] = np.nan
        df["source"] = source_id
        need = ["name", "type", "location", "price", "duration", "source"]
        missing = [c for c in need if c not in df.columns]
        if missing:
            print(f"[Merge] Skip {path} (missing columns {missing})")
            continue
        chunks.append(_normalize_for_concat(df[need]))
        print(f"[Merge] Loaded {len(df)} rows from {os.path.basename(path)} [{source_id}]")

    if not chunks:
        merged = pd.DataFrame(columns=unified_cols)
    else:
        merged = pd.concat(chunks, ignore_index=True)

    merged_clean = clean_dataframe(merged)

    ensure_directory(os.path.dirname(output_path))
    merged_clean.to_csv(output_path, index=False)
    print(f"[Merge] Saved clean merged data: {output_path} ({len(merged_clean)} rows)")
    return merged_clean
