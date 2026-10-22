"""Pembacaan dan validasi data korpus, query, dan qrels."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Mapping

import pandas as pd

from .config import DEFAULT_CORPUS, DEFAULT_QRELS, DEFAULT_QUERIES


def read_csv(path: str | Path) -> pd.DataFrame:
    """Membaca CSV sebagai string, mempertahankan sel kosong sebagai string kosong."""
    return pd.read_csv(Path(path), dtype=str, keep_default_na=False, encoding="utf-8-sig")


def load_corpus(path: str | Path = DEFAULT_CORPUS) -> pd.DataFrame:
    """Mengembalikan DataFrame korpus."""
    df = read_csv(path)
    required = {"doc_id", "judul", "isi"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Kolom korpus tidak lengkap: {sorted(missing)}")
    for col in ("doc_id", "judul", "isi"):
        df[col] = df[col].astype(str).str.strip()
    return df.reset_index(drop=True)


def corpus_texts(df: pd.DataFrame | None = None, path: str | Path = DEFAULT_CORPUS) -> dict[str, str]:
    """Mengembalikan {doc_id: judul + '. ' + isi}, sama seperti pipeline asli."""
    df = load_corpus(path) if df is None else df
    return {
        str(row.doc_id): f"{row.judul}. {row.isi}"
        for row in df.itertuples(index=False)
    }


def load_queries_df(path: str | Path = DEFAULT_QUERIES) -> pd.DataFrame:
    df = read_csv(path)
    required = {"query_id", "query"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Kolom queries tidak lengkap: {sorted(missing)}")
    for col in ("query_id", "query"):
        df[col] = df[col].astype(str).str.strip()
    return df.reset_index(drop=True)


def load_queries(path: str | Path = DEFAULT_QUERIES) -> dict[str, str]:
    """Mengembalikan {query_id: teks_query}."""
    df = load_queries_df(path)
    return dict(zip(df["query_id"], df["query"]))


def load_qrels_df(path: str | Path = DEFAULT_QRELS) -> pd.DataFrame:
    df = read_csv(path)
    required = ["query_id", "doc_id", "relevance"]
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Kolom qrels tidak lengkap: {sorted(missing)}")
    df = df[required + [c for c in df.columns if c not in required]].copy()
    df["query_id"] = df["query_id"].astype(str).str.strip()
    df["doc_id"] = df["doc_id"].astype(str).str.strip()
    df["relevance"] = pd.to_numeric(df["relevance"], errors="raise").astype(int)
    return df.reset_index(drop=True)


def load_qrels(path: str | Path = DEFAULT_QRELS) -> dict[str, dict[str, int]]:
    """Mengembalikan {query_id: {doc_id: nilai_relevansi}}."""
    df = load_qrels_df(path)
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    for row in df.itertuples(index=False):
        qrels[str(row.query_id)][str(row.doc_id)] = int(row.relevance)
    return dict(qrels)


def qrels_to_pairs(qrels: Mapping[str, Mapping[str, int]]) -> dict[tuple[str, str], int]:
    return {(q, d): int(r) for q, docs in qrels.items() for d, r in docs.items()}
