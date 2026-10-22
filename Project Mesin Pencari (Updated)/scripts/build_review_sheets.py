"""Membuat lembar review independen untuk dua penilai.

Output (di Data/review/):
  penilai_1_qrels.csv
  penilai_2_qrels.csv
  penilai_1_dokumen.csv
  penilai_2_dokumen.csv
  petunjuk_review.md

Lembar qrels hanya memuat dokumen yang sudah dinilai relevan; tidak ada
label awal. Skala 1/2/3 diisi mandiri oleh masing-masing penilai.
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
QRELS = DATA / "qrels_final.csv"
CORPUS = DATA / "korpus_final.csv"
QUERIES = DATA / "queries_25.csv"
OUT_DIR = DATA / "review"

QRELS_FIELDS = [
    "penilai", "query_id", "query", "intent", "doc_id", "judul", "isi",
    "topik", "skala", "label_1_2_3", "alasan", "catatan",
]
DOC_FIELDS = [
    "penilai", "doc_id", "judul", "isi", "topik", "sumber", "jenis_sumber",
    "url", "tanggal_publikasi", "tanggal_akses", "status_sumber", "catatan",
]

PETUNJUK = """# Petunjuk Review Independen

## Tugas

1. Baca query dan dokumen pada setiap baris.
2. Isi `label_1_2_3` dengan:
   - `3` = sangat relevan: dokumen langsung menjawab/membahas query;
   - `2` = relevan: dokumen membahas query, tetapi bukan fokus utama;
   - `1` = sedikit relevan: dokumen hanya menyinggung topik query.
3. Isi `alasan` secara singkat: bagian dokumen yang mendukung label.
4. Isi `catatan` jika ada keraguan.

## Aturan

- Penilai 1 dan Penilai 2 bekerja **terpisah**.
- Jangan berdiskusi atau melihat lembar penilai lain sampai kedua lembar selesai.
- Jangan mengubah teks query, judul, atau isi dokumen.
- Setelah selesai, kirim file masing-masing ke koordinator.
- Perbedaan label akan dicatat dan diadjudikasi terpisah.

## Review dokumen

Untuk `penilai_*_dokumen.csv`, isi `status_sumber`:
- `cocok` = isi dokumen didukung sumber;
- `cukup` = sebagian besar didukung, ada bagian yang perlu diperbaiki;
- `tidak_cocok` = isi tidak didukung sumber.

Tulis catatan pada `catatan` jika status bukan `cocok`.
"""


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_rows(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    qrels = read_rows(QRELS)
    corpus = read_rows(CORPUS)
    query_rows = read_rows(QUERIES)
    query_text = {row["query_id"]: row["query"] for row in query_rows}
    query_intent = {row["query_id"]: row.get("intent", "") for row in query_rows}
    docs_by_id = {row["doc_id"]: row for row in corpus}

    base_qrels: list[dict[str, object]] = []
    for row in qrels:
        doc = docs_by_id[row["doc_id"]]
        base_qrels.append({
            "query_id": row["query_id"],
            "query": query_text[row["query_id"]],
            "intent": query_intent.get(row["query_id"], ""),
            "doc_id": row["doc_id"],
            "judul": doc["judul"],
            "isi": doc["isi"],
            "topik": doc["topik"],
        })

    base_docs: list[dict[str, object]] = []
    for row in corpus:
        base_docs.append({
            "doc_id": row["doc_id"],
            "judul": row["judul"],
            "isi": row["isi"],
            "topik": row["topik"],
            "sumber": row["sumber"],
            "jenis_sumber": row["jenis_sumber"],
            "url": row["url"],
            "tanggal_publikasi": row["tanggal_publikasi"],
            "tanggal_akses": row["tanggal_akses"],
        })

    rng = random.Random(args.seed)
    for number, name in ((1, "Penilai 1"), (2, "Penilai 2")):
        qrels_rows = [dict(row) for row in base_qrels]
        docs_rows = [dict(row) for row in base_docs]
        rng.shuffle(qrels_rows)
        rng.shuffle(docs_rows)

        for row in qrels_rows:
            row.update({
                "penilai": name,
                "skala": "1-3",
                "label_1_2_3": "",
                "alasan": "",
                "catatan": "",
            })
        for row in docs_rows:
            row.update({
                "penilai": name,
                "status_sumber": "",
                "catatan": "",
            })

        write_rows(OUT_DIR / f"penilai_{number}_qrels.csv", QRELS_FIELDS, qrels_rows)
        write_rows(OUT_DIR / f"penilai_{number}_dokumen.csv", DOC_FIELDS, docs_rows)

    (OUT_DIR / "petunjuk_review.md").write_text(PETUNJUK, encoding="utf-8")

    print(f"Lembar qrels  : {len(base_qrels)} baris x 2 penilai")
    print(f"Lembar dokumen: {len(base_docs)} baris x 2 penilai")
    print(f"Output        : {OUT_DIR}")


if __name__ == "__main__":
    main()
