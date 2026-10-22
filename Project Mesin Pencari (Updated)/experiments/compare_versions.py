"""Membandingkan hasil Versi A dan Versi B.

Contoh:
  python experiments/compare_versions.py --results-dir experiments/results/final_review \
      --qrels Data/qrels_final.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stki.data import load_qrels  # noqa: E402
from stki.evaluation import compare_per_query, evaluate, paired_bootstrap  # noqa: E402


def resolve(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def load_run(path: Path) -> dict[str, list[str]]:
    df = pd.read_csv(path, dtype={"query_id": str, "doc_id": str}, encoding="utf-8-sig")
    required = {"query_id", "rank", "doc_id"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path}: kolom hilang {sorted(missing)}")
    df = df.sort_values(["query_id", "rank"])
    return {
        query_id: group["doc_id"].tolist()
        for query_id, group in df.groupby("query_id", sort=True)
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="experiments/results")
    parser.add_argument("--qrels", default="Data/qrels_final.csv")
    parser.add_argument("--metric-k", type=int, default=5)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    results_dir = resolve(args.results_dir)
    qrels_path = resolve(args.qrels)
    if not qrels_path.exists():
        raise FileNotFoundError(
            f"Qrels tidak ditemukan: {qrels_path}. "
            "Gunakan --qrels Data/qrels_final.csv."
        )

    run_a = load_run(results_dir / "versi_a_run.csv")
    run_b = load_run(results_dir / "versi_b_run.csv")
    qrels = load_qrels(qrels_path)
    k = args.metric_k

    eval_a = evaluate(run_a, qrels, k=k)
    eval_b = evaluate(run_b, qrels, k=k)
    metrics = [f"P@{k}", f"R@{k}", f"F1@{k}", "AP", f"nDCG@{k}"]
    a_avg = eval_a.loc["Rata-rata"]
    b_avg = eval_b.loc["Rata-rata"]

    summary = pd.DataFrame(
        [
            {
                "metrik": metric,
                "versi_a": float(a_avg[metric]),
                "versi_b": float(b_avg[metric]),
                "selisih_a_minus_b": float(a_avg[metric] - b_avg[metric]),
            }
            for metric in metrics
        ]
    )
    per_query = compare_per_query(run_a, run_b, qrels, k=k)
    boot_ap = paired_bootstrap(
        run_a,
        run_b,
        qrels,
        metric="AP",
        k=k,
        n_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    boot_ndcg = paired_bootstrap(
        run_a,
        run_b,
        qrels,
        metric=f"nDCG@{k}",
        k=k,
        n_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    bootstrap = pd.DataFrame([boot_ap, boot_ndcg])

    summary.to_csv(results_dir / "ringkasan_a_b.csv", index=False, encoding="utf-8-sig")
    per_query.to_csv(results_dir / "perbandingan_a_b.csv", index=False, encoding="utf-8-sig")
    bootstrap.to_csv(results_dir / "bootstrap_a_b.csv", index=False, encoding="utf-8-sig")
    payload = {
        "qrels": str(qrels_path),
        "metric_k": k,
        "summary": summary.to_dict(orient="records"),
        "bootstrap": bootstrap.to_dict(orient="records"),
    }
    (results_dir / "perbandingan_a_b.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("Ringkasan A vs B")
    print(summary.to_string(index=False))
    print("\nBootstrap selisih A - B")
    print(
        bootstrap[
            ["metric", "mean_a", "mean_b", "mean_diff", "ci95_low", "ci95_high", "prob_a_better"]
        ].to_string(index=False)
    )
    print(f"\nOutput: {results_dir}")


if __name__ == "__main__":
    main()
