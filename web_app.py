"""
Local web dashboard for pipeline outputs (summary, clustered results, plots).

Run from project root:
    pip install flask
    python web_app.py

Then open http://127.0.0.1:5000/
"""

import os
from typing import Any, Dict, List, Optional

import pandas as pd
from flask import Flask, abort, render_template, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

ALLOWED_PLOTS = frozenset({"price_distribution.png", "clusters.png"})

app = Flask(__name__)


def _safe_read_csv(path: str) -> Optional[pd.DataFrame]:
    if not os.path.isfile(path):
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _format_summary(df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows = []
    for _, r in df.iterrows():
        rows.append(
            {
                "type": str(r.get("type", "")),
                "average_price": float(r["average_price"]) if pd.notna(r.get("average_price")) else None,
                "listing_count": int(r["listing_count"]) if pd.notna(r.get("listing_count")) else 0,
                "listings_known_duration": int(r["listings_known_duration"])
                if pd.notna(r.get("listings_known_duration"))
                else 0,
                "average_cost_per_day": float(r["average_cost_per_day"])
                if pd.notna(r.get("average_cost_per_day"))
                else None,
            }
        )
    return rows


def _format_by_source(df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows = []
    for _, r in df.iterrows():
        rows.append(
            {
                "source": str(r.get("source", "")),
                "average_price": float(r["average_price"]) if pd.notna(r.get("average_price")) else None,
                "listing_count": int(r["listing_count"]) if pd.notna(r.get("listing_count")) else 0,
                "listings_known_duration": int(r["listings_known_duration"])
                if pd.notna(r.get("listings_known_duration"))
                else 0,
                "average_cost_per_day": float(r["average_cost_per_day"])
                if pd.notna(r.get("average_cost_per_day"))
                else None,
            }
        )
    return rows


@app.route("/")
def index():
    summary_path = os.path.join(OUTPUT_DIR, "analysis_summary.csv")
    by_source_path = os.path.join(OUTPUT_DIR, "analysis_summary_by_source.csv")
    results_path = os.path.join(OUTPUT_DIR, "results.csv")

    summary_df = _safe_read_csv(summary_path)
    by_source_df = _safe_read_csv(by_source_path)
    results_df = _safe_read_csv(results_path)

    if summary_df is not None and not summary_df.empty and "listings_known_duration" not in summary_df.columns:
        summary_df = summary_df.assign(listings_known_duration=0)
    if by_source_df is not None and not by_source_df.empty and "listings_known_duration" not in by_source_df.columns:
        by_source_df = by_source_df.assign(listings_known_duration=0)

    summary_rows: List[Dict[str, Any]] = []
    if summary_df is not None and not summary_df.empty:
        summary_rows = _format_summary(summary_df)

    by_source_rows: List[Dict[str, Any]] = []
    if by_source_df is not None and not by_source_df.empty:
        by_source_rows = _format_by_source(by_source_df)

    results_columns: List[str] = []
    results_records: List[Dict[str, Any]] = []
    results_total = 0
    if results_df is not None and not results_df.empty:
        results_total = len(results_df)
        want = [
            "source",
            "name",
            "type",
            "location",
            "price",
            "duration",
            "cost_per_day",
            "cluster",
            "cluster_label",
        ]
        cols = [c for c in want if c in results_df.columns]
        sub = results_df[cols].head(40) if cols else results_df.head(40)
        results_columns = list(sub.columns)
        for _, row in sub.iterrows():
            rec: Dict[str, Any] = {}
            for c in results_columns:
                v = row[c]
                if pd.isna(v):
                    rec[c] = None
                elif isinstance(v, (float, int)) and c in ("price", "duration", "cost_per_day", "cluster"):
                    rec[c] = float(v)
                else:
                    rec[c] = str(v) if v is not None else None
            results_records.append(rec)

    plots_ok = all(os.path.isfile(os.path.join(OUTPUT_DIR, p)) for p in ALLOWED_PLOTS)

    return render_template(
        "dashboard.html",
        summary_rows=summary_rows,
        by_source_rows=by_source_rows,
        results_columns=results_columns,
        results_records=results_records,
        results_total=results_total,
        plots_ok=plots_ok,
        output_missing=summary_df is None or summary_df.empty,
    )


@app.route("/plots/<path:name>")
def plot_file(name: str):
    if name not in ALLOWED_PLOTS:
        abort(404)
    return send_from_directory(OUTPUT_DIR, name, mimetype="image/png")


def main() -> None:
    # Dev server; for production use a proper WSGI server.
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
