# Comparative Analysis of Tourism Offers in Algeria

## Structured Platforms vs Independent Planning

This project is a full data engineering and analytics pipeline in Python that compares two tourism planning approaches in Algeria:

- **Structured platforms** (official tourism offers from ONAT)
- **Independent planning** (hotels and travel listings from Ouedkniss)

It performs end-to-end web scraping, cleaning, schema unification, statistical comparison, and machine learning clustering.

## Authors

This project was developed by:

- **Hammadou Islem**
- **Mokkedem Akram**
- **Boukhelkhel Chamseddine**

---

## Project Architecture

```text
project/
│
├── scraping/
│   ├── onat_scraper.py
│   ├── ouedkniss_graphql_client.py
│   ├── ouedkniss_scraper.py
│   ├── ouedkniss_voyages_tourisme_scraper.py
│   ├── ouedkniss_immobilier_location_vacances_scraper.py
│   ├── ss_travel_scraper.py
│   ├── traveldzair_scraper.py
│   ├── tourismalgeria_scraper.py
│   ├── petitfute_algerie_scraper.py
│
├── data/
│   ├── raw_onat.csv
│   ├── raw_ouedkniss.csv
│   ├── raw_ouedkniss_voyages_tourisme.csv
│   ├── raw_ouedkniss_immobilier_location_vacances.csv
│   ├── raw_ss_travel.csv
│   ├── raw_traveldzair.csv
│   ├── raw_tourismalgeria.csv
│   ├── raw_petitfute_algerie.csv
│
├── processing/
│   ├── clean_data.py
│   ├── merge_data.py
│   ├── filters.py
│
├── analysis/
│   ├── analysis.py
│   ├── clustering.py
│
├── output/
│   ├── clean_data.csv
│   ├── results.csv
│
├── utils/
│   ├── helpers.py
│
├── main.py
├── web_app.py
├── templates/
│   └── dashboard.html
├── requirements.txt
└── README.md
```

---

## Data Sources

The project uses **100% web-sourced data** (no manual dataset, no invented prices):

1. [ONAT](https://onat.dz) — official offers (OpenCart HTML)
2. [Ouedkniss](https://www.ouedkniss.com) — mixed listings via public GraphQL (`ouedkniss_scraper.py`)
3. [Ouedkniss voyages-tourisme](https://www.ouedkniss.com/voyages-tourisme) — GraphQL strategies tuned to that hub (`ouedkniss_voyages_tourisme_scraper.py`)
4. [Ouedkniss immobilier location vacances](https://www.ouedkniss.com/immobilier-location-vacances) — vacation rentals (`ouedkniss_immobilier_location_vacances_scraper.py`)
5. [SS-Travel](https://ss-travel.dz) — static `div.pkg-card` packages (`ss_travel_scraper.py`)
6. [Traveldzair](https://traveldzair.com) — probed with WordPress-like selectors; **often unreachable** (DNS) from some networks (`traveldzair_scraper.py`)
7. [TourismAlgeria.com](https://www.tourismalgeria.com) — only ingests **remote JSON** from `dz-hotel-comparator` `data-src` when it exposes **DZD** prices (often none in static HTML) (`tourismalgeria_scraper.py`)
8. [Petit Futé Algérie](https://www.petitfute.com/p136-algerie/) — **often blocked by Cloudflare (403)**; selectors target Petit Futé grid cards when HTML is available (`petitfute_algerie_scraper.py`)

---

## Unified Data Schema

Each record is normalized into:

```json
{
  "name": "string",
  "type": "offer | hotel",
  "location": "string",
  "price": "float",
  "duration": "float (days, optional; NaN if unknown)",
  "source": "string (provenance id after merge)",
  "rating": "float (optional)"
}
```

---

## Pipeline Overview

### 1) Scraping

- `scraping/onat_scraper.py`
  - Uses `requests` + `BeautifulSoup`
  - Extracts: offer name, location, price, duration
  - Writes `data/raw_onat.csv`

- `scraping/ouedkniss_scraper.py`
  - Ouedkniss serves listings through a **JavaScript SPA**; listing HTML is not present in the first response, so this module uses the public **`https://api.ouedkniss.com/graphql`** search API with `requests` (same live data as the website), including `SearchFilterInput.page` pagination.
  - Extracts: title, store/category as a coarse location, price, listing URL (`/annonces/{id}`)
  - Classifies listings into `hotel` or `offer` via keywords
  - Uses headers, delays, and retries on transient disconnects
  - Writes `data/raw_ouedkniss.csv`

- Additional scrapers (each with **its own** selectors / API filters, User-Agent, delays, and per-page row logging) write the other `data/raw_*.csv` files listed in the tree above.

### 2) Processing

- `processing/filters.py`
  - Drops obvious **non-product** rows (visa / consular / paperwork keywords) so averages are less polluted.

- `processing/clean_data.py`
  - Removes duplicates
  - Normalizes `price` to float; `duration` to days when parseable, otherwise **left as missing** (no default “1 day”)
  - Applies noise filter from `filters.py`

- `processing/merge_data.py`
  - Merges **all** non-empty raw CSVs; each file is tagged with a **`source`** id (see `main.py` `RAW_SOURCES`)
  - Writes `output/clean_data.csv` (includes `source`)

### 3) Analysis

- `analysis/analysis.py`
  - **`cost_per_day` only when `duration` is known** (`price / duration`); otherwise NaN (never assumed 1-day)
  - Summary by **`type`**: average price, listing count, count with known duration, **average cost/day over rows with duration only**
  - Summary by **`source`**: same metrics per scraper
  - Saves:
    - `output/analysis_summary.csv`
    - `output/analysis_summary_by_source.csv`
    - `output/price_distribution.png`

### 4) Clustering

- `analysis/clustering.py`
  - If **enough listings have known duration** (default ≥ 20): KMeans on **`price` + `cost_per_day`** for those rows; others get cluster label **`no_trip_length`**
  - Otherwise: KMeans on **`log(1 + price)`** for all rows (price-tier clusters)
  - Labels: budget / mid-range / premium (by centroid ordering)
  - Saves:
    - `output/results.csv`
    - `output/clusters.png`

### 5) Orchestration

- `main.py` runs all steps in order:
  1. scraping
  2. cleaning
  3. merging
  4. analysis
  5. clustering

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows PowerShell
pip install -r requirements.txt
```

---

## Run

```bash
python main.py
```

### Web dashboard (view results in the browser)

After the pipeline has produced files under `output/`, install Flask if needed and start the local server:

```bash
pip install flask
python web_app.py
```

Open **http://127.0.0.1:5000/** to see:

- Summary table (from `analysis_summary.csv`)
- Charts (`price_distribution.png`, `clusters.png`)
- A sample of clustered rows (`results.csv`)

The app is intended for **local use** only; do not expose it to the public internet without proper security hardening.

Generated artifacts:

- `data/raw_onat.csv`
- `data/raw_ouedkniss.csv`
- `data/raw_ouedkniss_voyages_tourisme.csv`
- `data/raw_ouedkniss_immobilier_location_vacances.csv`
- `data/raw_ss_travel.csv`
- `data/raw_traveldzair.csv`
- `data/raw_tourismalgeria.csv`
- `data/raw_petitfute_algerie.csv`
- `output/clean_data.csv`
- `output/analysis_summary.csv`
- `output/analysis_summary_by_source.csv`
- `output/results.csv`
- `output/price_distribution.png`
- `output/clusters.png`

---

## Analytical Interpretation

This project enables a practical comparison between:

- **Structured offers** (packages from official channels)
- **Independent options** (hotels/listings from classified platforms)

Using `average price`, `cost_per_day`, and `cluster segmentation`, the pipeline helps identify where listings fall economically (budget to premium) and whether organized packages provide better day-level value than independent accommodation planning.

---

## Conclusions

The pipeline is designed as a realistic backend + analytics workflow:

- modular source separation (scraping, processing, analysis)
- robust parsing and normalization helpers
- reproducible outputs for reporting
- ML clustering for market segmentation

Because scraped content evolves over time, running the pipeline periodically gives updated market comparisons and more reliable trends.

