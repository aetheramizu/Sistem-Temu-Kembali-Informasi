"""Metrik evaluasi temu kembali dan paired bootstrap."""
from __future__ import annotations

import math
from typing import Mapping

import numpy as np
import pandas as pd


def precision_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    return sum(1 for doc_id in ranked[:k] if doc_id in relevant) / k


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    return (
        sum(1 for doc_id in ranked[:k] if doc_id in relevant) / len(relevant)
        if relevant
        else 0.0
    )


def f1_score(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0


def average_precision(ranked: list[str], relevant: set[str]) -> float:
    hits = 0
    total = 0.0
    for rank, doc_id in enumerate(ranked, start=1):
        if doc_id in relevant:
            hits += 1
            total += hits / rank
    return total / len(relevant) if relevant else 0.0


def dcg_at_k(gains: list[int | float], k: int) -> float:
    return sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains[:k], start=1))


def ndcg_at_k(ranked: list[str], graded: Mapping[str, int], k: int) -> float:
    gains = [graded.get(doc_id, 0) for doc_id in ranked[:k]]
    ideal = sorted((value for value in graded.values() if value > 0), reverse=True)
    idcg = dcg_at_k(ideal, k)
    return dcg_at_k(gains, k) / idcg if idcg > 0 else 0.0


def evaluate(
    run: Mapping[str, list[str]],
    qrels: Mapping[str, Mapping[str, int]],
    k: int = 5,
) -> pd.DataFrame:
    """Metrik per query + baris rata-rata.

    Hanya qrels dengan relevance > 0 yang dianggap relevan. Ini membuat
    baris eksplisit relevance=0 tetap aman jika suatu saat ditambahkan.
    """
    rows = []
    for query_id, ranked in run.items():
        graded = qrels.get(query_id, {})
        relevant = {doc_id for doc_id, grade in graded.items() if grade > 0}
        precision = precision_at_k(ranked, relevant, k)
        recall = recall_at_k(ranked, relevant, k)
        rows.append(
            {
                "query_id": query_id,
                f"P@{k}": precision,
                f"R@{k}": recall,
                f"F1@{k}": f1_score(precision, recall),
                "AP": average_precision(ranked, relevant),
                f"nDCG@{k}": ndcg_at_k(ranked, graded, k),
                "num_relevant": len(relevant),
                "num_retrieved": len(ranked),
            }
        )
    df = pd.DataFrame(rows).set_index("query_id")
    if df.empty:
        raise ValueError("Run kosong")
    df.loc["Rata-rata"] = df.mean(numeric_only=True)
    return df.round(6)


def per_query_metric(
    run: Mapping[str, list[str]],
    qrels: Mapping[str, Mapping[str, int]],
    metric: str = "AP",
    k: int = 5,
) -> dict[str, float]:
    values: dict[str, float] = {}
    for query_id, ranked in run.items():
        graded = qrels.get(query_id, {})
        relevant = {doc_id for doc_id, grade in graded.items() if grade > 0}
        if metric == "AP":
            values[query_id] = average_precision(ranked, relevant)
        elif metric == f"nDCG@{k}":
            values[query_id] = ndcg_at_k(ranked, graded, k)
        elif metric == f"P@{k}":
            values[query_id] = precision_at_k(ranked, relevant, k)
        elif metric == f"R@{k}":
            values[query_id] = recall_at_k(ranked, relevant, k)
        elif metric == f"F1@{k}":
            precision = precision_at_k(ranked, relevant, k)
            recall = recall_at_k(ranked, relevant, k)
            values[query_id] = f1_score(precision, recall)
        else:
            raise ValueError(f"Metrik tidak dikenal: {metric}")
    return values


def paired_bootstrap(
    run_a: Mapping[str, list[str]],
    run_b: Mapping[str, list[str]],
    qrels: Mapping[str, Mapping[str, int]],
    metric: str = "AP",
    k: int = 5,
    n_samples: int = 10_000,
    seed: int = 42,
) -> dict[str, float | int | str]:
    """Paired bootstrap untuk selisih rata-rata A - B pada level query."""
    query_ids = sorted(set(run_a) & set(run_b))
    if not query_ids:
        raise ValueError("Tidak ada query yang sama pada kedua run")
    a = np.array([per_query_metric(run_a, qrels, metric, k)[q] for q in query_ids])
    b = np.array([per_query_metric(run_b, qrels, metric, k)[q] for q in query_ids])
    diff = a - b
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(query_ids), size=(n_samples, len(query_ids)))
    boot = diff[idx].mean(axis=1)
    ci_low, ci_high = np.percentile(boot, [2.5, 97.5])
    return {
        "metric": metric,
        "k": k,
        "n_queries": len(query_ids),
        "mean_a": float(a.mean()),
        "mean_b": float(b.mean()),
        "mean_diff": float(diff.mean()),
        "ci95_low": float(ci_low),
        "ci95_high": float(ci_high),
        "prob_a_better": float((boot > 0).mean()),
        "n_a_better": int((diff > 0).sum()),
        "n_b_better": int((diff < 0).sum()),
        "n_tie": int((diff == 0).sum()),
        "n_bootstrap": n_samples,
        "seed": seed,
    }


def compare_per_query(
    run_a: Mapping[str, list[str]],
    run_b: Mapping[str, list[str]],
    qrels: Mapping[str, Mapping[str, int]],
    k: int = 5,
) -> pd.DataFrame:
    """Tabel per query: AP dan nDCG@k untuk A, B, dan selisihnya."""
    query_ids = sorted(set(run_a) & set(run_b))
    ap_a = per_query_metric(run_a, qrels, "AP", k)
    ap_b = per_query_metric(run_b, qrels, "AP", k)
    ndcg_a = per_query_metric(run_a, qrels, f"nDCG@{k}", k)
    ndcg_b = per_query_metric(run_b, qrels, f"nDCG@{k}", k)
    rows = []
    for query_id in query_ids:
        rows.append(
            {
                "query_id": query_id,
                "AP_A": ap_a[query_id],
                "AP_B": ap_b[query_id],
                "delta_AP": ap_a[query_id] - ap_b[query_id],
                f"nDCG@{k}_A": ndcg_a[query_id],
                f"nDCG@{k}_B": ndcg_b[query_id],
                f"delta_nDCG@{k}": ndcg_a[query_id] - ndcg_b[query_id],
                "winner_AP": "A" if ap_a[query_id] > ap_b[query_id] else ("B" if ap_a[query_id] < ap_b[query_id] else "Tie"),
            }
        )
    return pd.DataFrame(rows)
