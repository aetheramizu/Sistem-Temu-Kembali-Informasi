"""Menjalankan satu versi eksperimen (A atau B).

Contoh:
  python experiments/run_experiment.py --config experiments/versi_a/config.json \
      --qrels Data/qrels_final.csv --output-dir experiments/results/final_review --label final_review
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stki.data import load_qrels, load_qrels_df, load_queries, load_queries_df  # noqa: E402
from stki.engine import SearchEngine  # noqa: E402
from stki.evaluation import evaluate  # noqa: E402
from stki.validation import sha256_file, validate_dataset  # noqa: E402


def resolve(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--qrels", default=None, help="Override qrels dari config")
    parser.add_argument("--output-dir", default="experiments/results")
    parser.add_argument("--label", default="final_review", help="Label run")
    args = parser.parse_args()

    config_path = resolve(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    corpus_path = resolve(config["corpus"])
    queries_path = resolve(config["queries"])
    qrels_path = resolve(args.qrels or config["qrels"])
    output_dir = resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not qrels_path.exists():
        raise FileNotFoundError(
            f"Qrels tidak ditemukan: {qrels_path}. "
            "Gunakan --qrels Data/qrels_final.csv."
        )

    corpus = pd.read_csv(corpus_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    queries_df = load_queries_df(queries_path)
    qrels_df = load_qrels_df(qrels_path)
    warnings = validate_dataset(
        corpus,
        queries_df,
        qrels_df,
        expected_docs=config.get("expected_docs", 50),
        expected_queries=config.get("expected_queries", 25),
        docs_per_topic=config.get("docs_per_topic"),
        queries_per_topic=config.get("queries_per_topic"),
        expected_topics=config.get("expected_topics", 5),
    )

    queries = load_queries(queries_path)
    qrels = load_qrels(qrels_path)
    top_k = int(config.get("top_k", 10))
    metric_k = int(config.get("metric_k", 5))

    start = time.perf_counter()
    engine = SearchEngine(
        corpus_path=corpus_path,
        model=config.get("model", "bm25"),
        use_stopword=bool(config.get("use_stopword", True)),
        use_stemming=bool(config.get("use_stemming", True)),
        use_query_expansion=bool(config.get("use_query_expansion", False)),
        expansion_weight=float(config.get("expansion_weight", 0.5)),
        synonyms_path=resolve(config["synonyms"]) if "synonyms" in config else ROOT / "Data" / "kamus_sinonim.csv",
        k1=float(config.get("k1", 1.5)),
        b=float(config.get("b", 0.75)),
    )

    run_rows = []
    run: dict[str, list[str]] = {}
    for query_id, query_text in queries.items():
        results = engine.search(query_text, k=top_k)
        run[query_id] = [doc_id for doc_id, _ in results]
        for rank, (doc_id, score) in enumerate(results, start=1):
            run_rows.append(
                {
                    "query_id": query_id,
                    "rank": rank,
                    "doc_id": doc_id,
                    "score": score,
                }
            )
    runtime = time.perf_counter() - start

    metrics = evaluate(run, qrels, k=metric_k)
    summary_row = metrics.loc["Rata-rata"]
    summary = pd.DataFrame(
        [
            {
                "version": config.get("version", "?"),
                "label": args.label,
                "model": config.get("model", "bm25"),
                "k1": config.get("k1", 1.5),
                "b": config.get("b", 0.75),
                "use_stopword": config.get("use_stopword", True),
                "use_stemming": config.get("use_stemming", True),
                "use_query_expansion": config.get("use_query_expansion", False),
                "expansion_weight": config.get("expansion_weight", None),
                f"P@{metric_k}": summary_row[f"P@{metric_k}"],
                f"R@{metric_k}": summary_row[f"R@{metric_k}"],
                f"F1@{metric_k}": summary_row[f"F1@{metric_k}"],
                "MAP": summary_row["AP"],
                f"nDCG@{metric_k}": summary_row[f"nDCG@{metric_k}"],
                "num_queries": len(queries),
                "num_docs": len(corpus),
                "qrels": str(qrels_path.relative_to(ROOT)) if qrels_path.is_relative_to(ROOT) else str(qrels_path),
            }
        ]
    )

    prefix = f"versi_{str(config.get('version', 'x')).lower()}"
    pd.DataFrame(run_rows).to_csv(output_dir / f"{prefix}_run.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(output_dir / f"{prefix}_metrics_per_query.csv", encoding="utf-8-sig")
    summary.to_csv(output_dir / f"{prefix}_summary.csv", index=False, encoding="utf-8-sig")

    metadata = {
        "version": config.get("version"),
        "label": args.label,
        "description": config.get("description"),
        "config": config,
        "config_path": str(config_path.relative_to(ROOT)),
        "resolved_paths": {
            "corpus": str(corpus_path),
            "queries": str(queries_path),
            "qrels": str(qrels_path),
        },
        "checksums_sha256": {
            "corpus": sha256_file(corpus_path),
            "queries": sha256_file(queries_path),
            "qrels": sha256_file(qrels_path),
        },
        "python": sys.version,
        "platform": platform.platform(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(runtime, 4),
        "warnings": warnings,
    }
    (output_dir / f"{prefix}_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Versi {config.get('version')} selesai.")
    print(summary.to_string(index=False))
    if warnings:
        print("Warning:")
        for warning in warnings:
            print(f"  - {warning}")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
