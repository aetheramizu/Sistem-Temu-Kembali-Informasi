"""Mengecek ulang status HTTP sumber dokumen baru.

Script ini hanya membantu verifikasi. HTTP 403 belum tentu berarti URL mati;
beberapa situs memblokir akses otomatis. Halaman tetap harus dibuka manual.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]


def resolve(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default="Data/korpus_final.csv")
    parser.add_argument("--output", default="experiments/results/source_check.csv")
    parser.add_argument("--timeout", type=int, default=25)
    args = parser.parse_args()

    corpus_path = resolve(args.corpus)
    output_path = resolve(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    corpus = pd.read_csv(corpus_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    rows = []
    checked_at = datetime.now(timezone.utc).isoformat()
    for row in corpus.itertuples(index=False):
        url = str(getattr(row, "url", "")).strip()
        if not url:
            continue
        status = ""
        final_url = ""
        size = ""
        error = ""
        try:
            response = requests.get(
                url,
                timeout=args.timeout,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            status = str(response.status_code)
            final_url = response.url
            size = str(len(response.content))
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
        rows.append(
            {
                "doc_id": getattr(row, "doc_id", ""),
                "url": url,
                "status_http": status,
                "final_url": final_url,
                "content_bytes": size,
                "checked_at_utc": checked_at,
                "error": error,
            }
        )
        print(f"{getattr(row, 'doc_id', ''):>4}  {status or 'ERR':>4}  {url[:100]}")

    output = pd.DataFrame(rows)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\nOutput: {output_path}")
    if not output.empty:
        print("Ringkasan status:", output["status_http"].value_counts().to_dict())


if __name__ == "__main__":
    main()
