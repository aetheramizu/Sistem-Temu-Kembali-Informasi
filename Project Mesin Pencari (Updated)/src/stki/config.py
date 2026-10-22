"""Konfigurasi path dan default proyek STKI."""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "Data"
DOCS_DIR = ROOT_DIR / "docs"
EXPERIMENTS_DIR = ROOT_DIR / "experiments"
RESULTS_DIR = EXPERIMENTS_DIR / "results"

DEFAULT_CORPUS = DATA_DIR / "korpus_final.csv"
DEFAULT_QUERIES = DATA_DIR / "queries_25.csv"
DEFAULT_QRELS = DATA_DIR / "qrels_final.csv"
DEFAULT_SYNONYMS = DATA_DIR / "kamus_sinonim.csv"
LEGACY_CORPUS = DATA_DIR / "korpus.csv"
LEGACY_QUERIES = DATA_DIR / "queries.csv"
LEGACY_QRELS = DATA_DIR / "qrels.csv"

DEFAULT_K1 = 1.5
DEFAULT_B = 0.75
DEFAULT_TOP_K = 10
DEFAULT_METRIC_K = 5
DEFAULT_EXPANSION_WEIGHT = 0.5
