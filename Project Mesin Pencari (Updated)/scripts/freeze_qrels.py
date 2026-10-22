"""Membuat Data/qrels_final.csv dari lembar penilaian yang sudah diverifikasi.

Script ini menolak membuat qrels final jika masih ada baris dengan status
`menunggu_verifikasi` atau label di luar 1/2/3. Ini sengaja dibuat ketat agar
label final tidak dibuat tanpa persetujuan kelompok.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stki.data import load_corpus, load_queries_df  # noqa: E402
from stki.validation import sha256_file, validate_dataset  # noqa: E402

ACCEPTED_STATUS = {"diverifikasi", "disetujui", "verified", "approved"}


def resolve(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="Data/lembar_penilaian_final.csv")
    parser.add_argument("--output", default="Data/qrels_final.csv")
    parser.add_argument("--corpus", default="Data/korpus_final.csv")
    parser.add_argument("--queries", default="Data/queries_25.csv")
    args = parser.parse_args()

    input_path = resolve(args.input)
    output_path = resolve(args.output)
    corpus_path = resolve(args.corpus)
    queries_path = resolve(args.queries)

    df = pd.read_csv(input_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    required = {
        "query_id",
        "doc_id",
        "label_penilai_1",
        "label_penilai_2",
        "label_final",
        "status_verifikasi",
        "catatan_anggota",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Kolom lembar penilaian tidak lengkap: {sorted(missing)}")

    label_columns = ["label_penilai_1", "label_penilai_2", "label_final"]
    for column in label_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    bad_label_rows = df[df[label_columns].isna().any(axis=1) | ~df[label_columns].isin([1, 2, 3]).all(axis=1)]
    if not bad_label_rows.empty:
        print("Qrels final belum bisa dibuat: label penilai belum lengkap atau di luar 1/2/3.")
        print(bad_label_rows[["query_id", "doc_id", *label_columns]].head(20).to_string(index=False))
        raise SystemExit(1)

    df[label_columns] = df[label_columns].astype(int)
    status_counts = df["status_verifikasi"].value_counts().to_dict()
    pending = df[~df["status_verifikasi"].isin(ACCEPTED_STATUS)]
    if not pending.empty:
        print("Qrels final belum bisa dibuat.")
        print(f"Status: {status_counts}")
        print(f"Baris belum diverifikasi: {len(pending)}")
        print(pending[["query_id", "doc_id", "label_final", "status_verifikasi"]].head(20).to_string(index=False))
        raise SystemExit(1)

    disagreements = df[df["label_penilai_1"] != df["label_penilai_2"]]
    missing_notes = disagreements[disagreements["catatan_anggota"].str.strip() == ""]
    if not missing_notes.empty:
        print("Qrels final belum bisa dibuat: pasangan yang tidak sepakat wajib punya catatan adjudikasi.")
        print(missing_notes[["query_id", "doc_id", "label_penilai_1", "label_penilai_2", "label_final"]].to_string(index=False))
        raise SystemExit(1)

    final = df[df["label_final"] > 0][["query_id", "doc_id", "label_final"]].copy()
    final = final.rename(columns={"label_final": "relevance"})
    final = final.drop_duplicates(["query_id", "doc_id"]).sort_values(["query_id", "doc_id"])

    if final.empty:
        raise ValueError("Tidak ada label 1/2/3; qrels final kosong")

    corpus = load_corpus(corpus_path)
    queries = load_queries_df(queries_path)
    warnings = validate_dataset(
        corpus,
        queries,
        final,
        docs_per_topic=5,
        queries_per_topic=None,
        expected_topics=10,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(output_path, index=False, encoding="utf-8-sig")
    checksum = sha256_file(output_path)
    (output_path.parent / "qrels_final_checksum.txt").write_text(
        f"{checksum}  {output_path.name}\n", encoding="utf-8"
    )

    print("Qrels final dibuat.")
    print(f"Pasangan: {len(final)}; query: {final['query_id'].nunique()}; dokumen: {final['doc_id'].nunique()}")
    if disagreements.empty:
        print("Kesepakatan penilai: 100% (tidak ada pasangan berbeda).")
    else:
        agreement = 1 - len(disagreements) / len(df)
        print(f"Kesepakatan penilai: {agreement:.2%}; pasangan diadjudikasi: {len(disagreements)}")
    print(f"Output: {output_path}")
    print(f"SHA256: {checksum}")
    if warnings:
        print("Warning:")
        for warning in warnings:
            print(f"  - {warning}")


if __name__ == "__main__":
    main()
