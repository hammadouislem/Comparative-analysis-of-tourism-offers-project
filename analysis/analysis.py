import os
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from utils.helpers import ensure_directory

# Plot prices in thousands of DZD so axes show readable numbers (avoid 1e7 notation).
_PRICE_SCALE = 1000.0


def run_analysis(df: pd.DataFrame, output_dir: str) -> Tuple[pd.DataFrame, Dict]:
    ensure_directory(output_dir)

    work = df.copy()
    summary_path = os.path.join(output_dir, "analysis_summary.csv")
    fig_path = os.path.join(output_dir, "price_distribution.png")

    if work.empty:
        print("[Analysis] No rows after merge/clean; skipping aggregates and charts.")
        pd.DataFrame(
            columns=["type", "average_price", "average_cost_per_day", "listing_count"]
        ).to_csv(summary_path, index=False)
        comparison = {
            "avg_offer_price": None,
            "avg_hotel_price": None,
            "summary_path": summary_path,
            "price_plot_path": None,
        }
        return work, comparison

    work["duration"] = work["duration"].fillna(1.0)
    work["duration"] = work["duration"].replace(0, 1.0)
    work["cost_per_day"] = work["price"] / work["duration"]

    summary = (
        work.groupby("type", as_index=False)
        .agg(
            average_price=("price", "mean"),
            average_cost_per_day=("cost_per_day", "mean"),
            listing_count=("name", "count"),
        )
        .sort_values(by="average_price")
    )

    summary.to_csv(summary_path, index=False)

    price_series = pd.to_numeric(work["price"], errors="coerce").dropna()
    if len(price_series) == 0:
        print("[Analysis] No numeric prices to plot; skipping histogram.")
        comparison = {
            "avg_offer_price": None,
            "avg_hotel_price": None,
            "summary_path": summary_path,
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
        "price_plot_path": fig_path,
    }

    print(f"[Analysis] Saved summary -> {summary_path}")
    print(f"[Analysis] Saved price distribution plot -> {fig_path}")
    return work, comparison

