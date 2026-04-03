import os
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from utils.helpers import ensure_directory

# Plot prices in thousands of DZD so axes show readable numbers (avoid 1e7 notation).
_PRICE_SCALE = 1000.0

def run_analysis(df: pd.DataFrame, output_dir: str) -> Tuple[pd.DataFrame, Dict]:
    ensure_directory(output_dir)

    work = df.copy()
    summary_path = os.path.join(output_dir, "analysis_summary.csv")
    summary_by_source_path = os.path.join(output_dir, "analysis_summary_by_source.csv")
    fig_path = os.path.join(output_dir, "price_distribution.png")

    if work.empty:
        print("[Analysis] No rows after merge/clean; skipping aggregates and charts.")
        empty_cols = [
            "type",
            "average_price",
            "listing_count",
            "listings_known_duration",
            "average_cost_per_day",
        ]
        pd.DataFrame(columns=empty_cols).to_csv(summary_path, index=False)
        pd.DataFrame(
            columns=["source", "listing_count", "average_price", "listings_known_duration", "average_cost_per_day"]
        ).to_csv(summary_by_source_path, index=False)
        comparison = {
            "avg_offer_price": None,
            "avg_hotel_price": None,
            "summary_path": summary_path,
            "summary_by_source_path": summary_by_source_path,
            "price_plot_path": None,
        }
        return work, comparison

    # cost_per_day only when duration is present and > 0 (no default 1-day assumption).
    work["cost_per_day"] = np.nan
    dur_ok = work["duration"].notna() & (work["duration"] > 0)
    work.loc[dur_ok, "cost_per_day"] = work.loc[dur_ok, "price"] / work.loc[dur_ok, "duration"]

    summary = (
        work.groupby("type", as_index=False)
        .agg(
            average_price=("price", "mean"),
            listing_count=("name", "count"),
            listings_known_duration=("cost_per_day", lambda s: int(s.notna().sum())),
            average_cost_per_day=("cost_per_day", "mean"),
        )
        .sort_values(by="average_price")
    )

    summary.to_csv(summary_path, index=False)

    if "source" in work.columns:
        by_src = (
            work.groupby("source", as_index=False)
            .agg(
                average_price=("price", "mean"),
                listing_count=("name", "count"),
                listings_known_duration=("cost_per_day", lambda s: int(s.notna().sum())),
                average_cost_per_day=("cost_per_day", "mean"),
            )
            .sort_values(by=["source", "average_price"])
        )
        by_src.to_csv(summary_by_source_path, index=False)
        print(f"[Analysis] Saved per-source summary -> {summary_by_source_path}")
    else:
        pd.DataFrame(
            columns=["source", "listing_count", "average_price", "listings_known_duration", "average_cost_per_day"]
        ).to_csv(summary_by_source_path, index=False)

    known_n = int(dur_ok.sum())
    print(
        f"[Analysis] Listings with known duration: {known_n}/{len(work)} "
        "(cost_per_day is NaN for the rest - not treated as 1-day trips)."
    )

    price_series = pd.to_numeric(work["price"], errors="coerce").dropna()
    if len(price_series) == 0:
        print("[Analysis] No numeric prices to plot; skipping histogram.")
        comparison = {
            "avg_offer_price": None,
            "avg_hotel_price": None,
            "summary_path": summary_path,
            "summary_by_source_path": summary_by_source_path,
            "price_plot_path": None,
        }
        print(f"[Analysis] Saved summary -> {summary_path}")
        return work, comparison

    plt.figure(figsize=(9, 5))
    (price_series / _PRICE_SCALE).plot(
        kind="hist", bins=min(30, max(5, len(price_series))), alpha=0.75, color="steelblue"
    )
    ax = plt.gca()
    ax.set_title("Price Distribution of Tourism Listings")
    ax.set_xlabel("Price (1000 DZD)")
    ax.set_ylabel("Frequency")
    ax.ticklabel_format(axis="x", style="plain", useOffset=False)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _p: f"{x:,.0f}".replace(",", " ")))
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=10))
    plt.tight_layout()
    plt.savefig(fig_path, dpi=140)
    plt.close()

    offer_avg = summary.loc[summary["type"] == "offer", "average_price"]
    hotel_avg = summary.loc[summary["type"] == "hotel", "average_price"]
    comparison = {
        "avg_offer_price": float(offer_avg.iloc[0]) if not offer_avg.empty else None,
        "avg_hotel_price": float(hotel_avg.iloc[0]) if not hotel_avg.empty else None,
        "summary_path": summary_path,
        "summary_by_source_path": summary_by_source_path,
        "price_plot_path": fig_path,
        "listings_known_duration": known_n,
    }

    print(f"[Analysis] Saved summary -> {summary_path}")
    print(f"[Analysis] Saved price distribution plot -> {fig_path}")
    return work, comparison
