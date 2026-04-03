import os

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from utils.helpers import ensure_directory


CLUSTER_LABELS = {0: "budget", 1: "mid-range", 2: "premium"}


def run_clustering(df: pd.DataFrame, output_csv_path: str, output_dir: str) -> pd.DataFrame:
    ensure_directory(output_dir)
    ensure_directory(os.path.dirname(output_csv_path))

    work = df.copy()
    work["cost_per_day"] = work["cost_per_day"].fillna(work["price"])

    model_df = work.dropna(subset=["price", "cost_per_day"]).copy()
    if len(model_df) < 3:
        print("[Clustering] Not enough rows for 3 clusters. Returning without clustering.")
        model_df["cluster"] = -1
        model_df["cluster_label"] = "unassigned"
        model_df.to_csv(output_csv_path, index=False)
        return model_df

    features = model_df[["price", "cost_per_day"]].values
    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    model_df["cluster"] = kmeans.fit_predict(scaled)

    # Map cluster IDs based on price centroid ordering: low -> budget, mid -> mid-range, high -> premium.
    centers_original = scaler.inverse_transform(kmeans.cluster_centers_)
    order = centers_original[:, 0].argsort()
    ordered_labels = ["budget", "mid-range", "premium"]
    mapping = {cluster_id: ordered_labels[idx] for idx, cluster_id in enumerate(order)}
    model_df["cluster_label"] = model_df["cluster"].map(mapping).fillna(model_df["cluster"].map(CLUSTER_LABELS))

    model_df.to_csv(output_csv_path, index=False)
    print(f"[Clustering] Saved clustered results -> {output_csv_path}")

    plt.figure(figsize=(9, 6))
    for label in ["budget", "mid-range", "premium"]:
        part = model_df[model_df["cluster_label"] == label]
        if not part.empty:
            plt.scatter(part["price"], part["cost_per_day"], label=label, alpha=0.7)
    plt.title("Tourism Listings Clusters")
    plt.xlabel("Price (DZD)")
    plt.ylabel("Cost per Day (DZD/day)")
    plt.legend()
    plt.tight_layout()
    cluster_plot_path = os.path.join(output_dir, "clusters.png")
    plt.savefig(cluster_plot_path, dpi=140)
    plt.close()
    print(f"[Clustering] Saved cluster visualization -> {cluster_plot_path}")

    return model_df

