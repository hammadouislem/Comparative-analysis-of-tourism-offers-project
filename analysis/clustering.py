import os

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from utils.helpers import ensure_directory

_PRICE_SCALE = 1000.0

# Use (price, cost_per_day) clustering only when enough listings have real trip length.
_MIN_ROWS_FOR_DURATION_CLUSTERING = 20

def _label_from_centroid_order(centroid_prices: np.ndarray) -> dict:
    order = np.argsort(centroid_prices)
    names = ["budget", "mid-range", "premium"]
    return {int(cluster_id): names[i] for i, cluster_id in enumerate(order)}


def run_clustering(df: pd.DataFrame, output_csv_path: str, output_dir: str) -> pd.DataFrame:
    ensure_directory(output_dir)
    ensure_directory(os.path.dirname(output_csv_path))

    work = df.copy()
    if "cost_per_day" not in work.columns:
        work["cost_per_day"] = np.nan
        dur_ok = work["duration"].notna() & (work["duration"] > 0)
        work.loc[dur_ok, "cost_per_day"] = work.loc[dur_ok, "price"] / work.loc[dur_ok, "duration"]

    if len(work) < 3:
        print("[Clustering] Not enough rows for 3 clusters. Returning without clustering.")
        work["cluster"] = -1
        work["cluster_label"] = "unassigned"
        work.to_csv(output_csv_path, index=False)
        return work

    dur_ok = work["duration"].notna() & (work["duration"] > 0)
    known_n = int(dur_ok.sum())

    if known_n >= _MIN_ROWS_FOR_DURATION_CLUSTERING:
        print(
            f"[Clustering] Mode: price + cost_per_day ({known_n} listings with known duration). "
            "Others labeled 'no_trip_length'."
        )
        known_idx = work.index[dur_ok]
        known_df = work.loc[known_idx].copy()

        features = known_df[["price", "cost_per_day"]].values.astype(float)
        scaler = StandardScaler()
        scaled = scaler.fit_transform(features)
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        known_df["cluster"] = kmeans.fit_predict(scaled)
        centers_original = scaler.inverse_transform(kmeans.cluster_centers_)
        mapping = _label_from_centroid_order(centers_original[:, 0])
        known_df["cluster_label"] = known_df["cluster"].map(mapping)

        work["cluster"] = -1
        work["cluster_label"] = "no_trip_length"
        work.loc[known_idx, "cluster"] = known_df["cluster"]
        work.loc[known_idx, "cluster_label"] = known_df["cluster_label"]

        plot_df = known_df
        y_label = "Cost per day (1000 DZD / day)"
        title = "Clusters (listings with known trip length)"
    else:
        print(
            f"[Clustering] Mode: log-price tiers only ({known_n} known durations < "
            f"{_MIN_ROWS_FOR_DURATION_CLUSTERING}). Using log(1+price) for all rows."
        )
        logp = np.log1p(work["price"].astype(float).values.reshape(-1, 1))
        scaler = StandardScaler()
        scaled = scaler.fit_transform(logp)
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        work["cluster"] = kmeans.fit_predict(scaled)
        centers = scaler.inverse_transform(kmeans.cluster_centers_).flatten()
        mapping = _label_from_centroid_order(centers)
        work["cluster_label"] = work["cluster"].map(mapping)

        plot_df = work
        y_label = "log(1 + price) [DZD]"
        title = "Clusters (price tiers; duration missing for many rows)"

    work.to_csv(output_csv_path, index=False)
    print(f"[Clustering] Saved clustered results -> {output_csv_path}")

    plt.figure(figsize=(9, 6))
    for label in ["budget", "mid-range", "premium"]:
        part = plot_df[plot_df["cluster_label"] == label]
        if not part.empty:
            if known_n >= _MIN_ROWS_FOR_DURATION_CLUSTERING:
                px = part["price"] / _PRICE_SCALE
                py = part["cost_per_day"] / _PRICE_SCALE
            else:
                px = part["price"] / _PRICE_SCALE
                py = np.log1p(part["price"].astype(float))
            plt.scatter(px, py, label=label, alpha=0.7)
    ax = plt.gca()
    ax.set_title(title)
    ax.set_xlabel("Price (1000 DZD)")
    ax.set_ylabel(y_label)
    ax.ticklabel_format(axis="x", style="plain", useOffset=False)
    space_fmt = mticker.FuncFormatter(lambda x, _p: f"{x:,.0f}".replace(",", " "))
    ax.xaxis.set_major_formatter(space_fmt)
    if known_n >= _MIN_ROWS_FOR_DURATION_CLUSTERING:
        ax.yaxis.set_major_formatter(space_fmt)
    plt.legend()
    plt.tight_layout()
    cluster_plot_path = os.path.join(output_dir, "clusters.png")
    plt.savefig(cluster_plot_path, dpi=140)
    plt.close()
    print(f"[Clustering] Saved cluster visualization -> {cluster_plot_path}")

    return work
