import os

from analysis.analysis import run_analysis
from analysis.clustering import run_clustering
from processing.merge_data import RawSource, merge_and_clean
from scraping.onat_scraper import save_onat_csv, scrape_onat
from scraping.ouedkniss_immobilier_location_vacances_scraper import (
    save_csv as save_ok_immo_csv,
    scrape_immobilier_location_vacances,
)
from scraping.ouedkniss_scraper import save_ouedkniss_csv, scrape_ouedkniss
from scraping.ouedkniss_voyages_tourisme_scraper import (
    save_csv as save_ok_vt_csv,
    scrape_ouedkniss_voyages_tourisme,
)
from scraping.petitfute_algerie_scraper import save_csv as save_pf_csv, scrape_petitfute_algerie
from scraping.ss_travel_scraper import save_csv as save_ss_csv, scrape_ss_travel
from scraping.tourismalgeria_scraper import save_csv as save_ta_csv, scrape_tourismalgeria
from scraping.traveldzair_scraper import save_csv as save_td_csv, scrape_traveldzair
from utils.helpers import ensure_directory


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

RAW_ONAT_PATH = os.path.join(DATA_DIR, "raw_onat.csv")
RAW_OUEDKNISS_PATH = os.path.join(DATA_DIR, "raw_ouedkniss.csv")
RAW_OUEDKNISS_VT_PATH = os.path.join(DATA_DIR, "raw_ouedkniss_voyages_tourisme.csv")
RAW_OUEDKNISS_IMMO_PATH = os.path.join(DATA_DIR, "raw_ouedkniss_immobilier_location_vacances.csv")
RAW_SS_TRAVEL_PATH = os.path.join(DATA_DIR, "raw_ss_travel.csv")
RAW_TRAVELDZAIR_PATH = os.path.join(DATA_DIR, "raw_traveldzair.csv")
RAW_TOURISMALGERIA_PATH = os.path.join(DATA_DIR, "raw_tourismalgeria.csv")
RAW_PETITFUTE_PATH = os.path.join(DATA_DIR, "raw_petitfute_algerie.csv")

CLEAN_DATA_PATH = os.path.join(OUTPUT_DIR, "clean_data.csv")
RESULTS_PATH = os.path.join(OUTPUT_DIR, "results.csv")

# (csv_path, source_id) — used for merge, cleaning, and per-source analytics.
RAW_SOURCES: list[RawSource] = [
    (RAW_ONAT_PATH, "onat"),
    (RAW_OUEDKNISS_PATH, "ouedkniss"),
    (RAW_OUEDKNISS_VT_PATH, "ouedkniss_voyages_tourisme"),
    (RAW_OUEDKNISS_IMMO_PATH, "ouedkniss_location_vacances"),
    (RAW_SS_TRAVEL_PATH, "ss_travel"),
    (RAW_TRAVELDZAIR_PATH, "traveldzair"),
    (RAW_TOURISMALGERIA_PATH, "tourismalgeria"),
    (RAW_PETITFUTE_PATH, "petitfute"),
]


def run_pipeline() -> None:
    ensure_directory(DATA_DIR)
    ensure_directory(OUTPUT_DIR)

    delay = 2.0
    pages = 5

    print("\n=== Scraping ONAT ===")
    save_onat_csv(scrape_onat(delay_seconds=delay), RAW_ONAT_PATH)

    print("\n=== Scraping Ouedkniss (general GraphQL strategies) ===")
    save_ouedkniss_csv(scrape_ouedkniss(max_pages=pages, delay_seconds=delay), RAW_OUEDKNISS_PATH)

    print("\n=== Scraping Ouedkniss /voyages-tourisme (GraphQL) ===")
    save_ok_vt_csv(scrape_ouedkniss_voyages_tourisme(max_pages=pages, delay_seconds=delay), RAW_OUEDKNISS_VT_PATH)

    print("\n=== Scraping Ouedkniss /immobilier-location-vacances (GraphQL) ===")
    save_ok_immo_csv(
        scrape_immobilier_location_vacances(max_pages=8, delay_seconds=delay),
        RAW_OUEDKNISS_IMMO_PATH,
    )

    print("\n=== Scraping SS-Travel (ss-travel.dz HTML) ===")
    save_ss_csv(scrape_ss_travel(delay_seconds=delay), RAW_SS_TRAVEL_PATH)

    print("\n=== Scraping Traveldzair ===")
    save_td_csv(scrape_traveldzair(max_pages=3, delay_seconds=delay), RAW_TRAVELDZAIR_PATH)

    print("\n=== Scraping TourismAlgeria.com ===")
    save_ta_csv(scrape_tourismalgeria(delay_seconds=delay), RAW_TOURISMALGERIA_PATH)

    print("\n=== Scraping Petit Futé Algérie ===")
    save_pf_csv(scrape_petitfute_algerie(max_pages=4, delay_seconds=delay), RAW_PETITFUTE_PATH)

    print("\n=== Merge + clean (all raw sources) ===")
    merged_df = merge_and_clean(RAW_SOURCES, CLEAN_DATA_PATH)

    print("\n=== Analysis ===")
    analyzed_df, comparison = run_analysis(merged_df, OUTPUT_DIR)
    print("[Analysis] offer vs hotel price comparison:", comparison)

    print("\n=== Clustering ===")
    clustered_df = run_clustering(analyzed_df, RESULTS_PATH, OUTPUT_DIR)
    print(f"[Pipeline] Completed. Clustered rows: {len(clustered_df)}")


if __name__ == "__main__":
    run_pipeline()
