"""Menggabungkan dua lembar review independen dan menandai perbedaan.

Output:
  Data/lembar_penilaian_final.csv
  Data/review/perbedaan_label.csv

Jika masih ada perbedaan, isi `label_final` dan `catatan_anggota` pada
`perbedaan_label.csv`, lalu jalankan ulang dengan --adjudikasi.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
REVIEW = DATA / "review"
DEFAULT_1 = REVIEW / "penilai_1_qrels_selesai.csv"
DEFAULT_2 = REVIEW / "penilai_2_qrels_selesai.csv"
OUT = DATA / "lembar_penilaian_final.csv"
DIFF = REVIEW / "perbedaan_label.csv"

FIELDS = [
    "query_id", "query", "intent", "doc_id", "judul", "isi", "topik",
    "label_penilai_1", "alasan_penilai_1", "catatan_penilai_1",
    "label_penilai_2", "alasan_penilai_2", "catatan_penilai_2",
    "label_final", "catatan_anggota", "status_verifikasi",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_rows(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def index(rows: list[dict[str, str]], name: str) -> dict[tuple[str, str], dict[str, str]]:
    result: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["query_id"], row["doc_id"])
        if key in result:
            raise ValueError(f"{name}: pasangan ganda {key}")
        result[key] = row
    return result


def parse_label(value: str, key: tuple[str, str], name: str) -> int:
    text = (value or "").strip()
    if text not in {"1", "2", "3"}:
        raise ValueError(f"{name}: label tidak valid untuk {key}: {value!r} (pakai 1/2/3)")
    return int(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--penilai-1", default=str(DEFAULT_1))
    parser.add_argument("--penilai-2", default=str(DEFAULT_2))
    parser.add_argument("--adjudikasi", default="")
    args = parser.parse_args()

    rows_1 = read_rows(Path(args.penilai_1))
    rows_2 = read_rows(Path(args.penilai_2))
    data_1 = index(rows_1, "penilai 1")
    data_2 = index(rows_2, "penilai 2")

    if set(data_1) != set(data_2):
        only_1 = sorted(set(data_1) - set(data_2))
        only_2 = sorted(set(data_2) - set(data_1))
        raise ValueError(f"Pasangan tidak sama. Hanya 1: {only_1}; hanya 2: {only_2}")

    adjudication: dict[tuple[str, str], dict[str, str]] = {}
    if args.adjudikasi:
        adjudication = index(read_rows(Path(args.adjudikasi)), "adjudikasi")

    merged: list[dict[str, object]] = []
    differences: list[dict[str, object]] = []
    missing = 0
    disagreements = 0

    for key in sorted(data_1):
        row_1 = data_1[key]
        row_2 = data_2[key]
        try:
            label_1 = parse_label(row_1.get("label_1_2_3", ""), key, "penilai 1")
            label_2 = parse_label(row_2.get("label_1_2_3", ""), key, "penilai 2")
        except ValueError:
            missing += 1
            continue

        if label_1 == label_2:
            label_final: object = label_1
            note = ""
            status = "disetujui"
        else:
            disagreements += 1
            label_final = ""
            note = ""
            status = "perlu_adjudikasi"
            if key in adjudication:
                label_final = parse_label(
                    adjudication[key].get("label_final", ""), key, "adjudikasi"
                )
                note = adjudication[key].get("catatan_anggota", "")
                status = "disetujui"

        merged.append({
            "query_id": key[0],
            "query": row_1["query"],
            "intent": row_1.get("intent", ""),
            "doc_id": key[1],
            "judul": row_1["judul"],
            "isi": row_1["isi"],
            "topik": row_1["topik"],
            "label_penilai_1": label_1,
            "alasan_penilai_1": row_1.get("alasan", ""),
            "catatan_penilai_1": row_1.get("catatan", ""),
            "label_penilai_2": label_2,
            "alasan_penilai_2": row_2.get("alasan", ""),
            "catatan_penilai_2": row_2.get("catatan", ""),
            "label_final": label_final,
            "catatan_anggota": note,
            "status_verifikasi": status,
        })

        if label_1 != label_2:
            differences.append({
                "query_id": key[0],
                "doc_id": key[1],
                "query": row_1["query"],
                "judul": row_1["judul"],
                "label_penilai_1": label_1,
                "alasan_penilai_1": row_1.get("alasan", ""),
                "label_penilai_2": label_2,
                "alasan_penilai_2": row_2.get("alasan", ""),
                "label_final": label_final,
                "catatan_anggota": note,
            })

    write_rows(OUT, FIELDS, merged)
    write_rows(
        DIFF,
        [
            "query_id", "doc_id", "query", "judul", "label_penilai_1",
            "alasan_penilai_1", "label_penilai_2", "alasan_penilai_2",
            "label_final", "catatan_anggota",
        ],
        differences,
    )

    total = len(data_1)
    print(f"Total pasangan : {total}")
    print(f"Terisi lengkap : {total - missing}")
    print(f"Belum lengkap  : {missing}")
    print(f"Sepakat        : {total - missing - disagreements}")
    print(f"Beda label     : {disagreements}")
    print(f"Output         : {OUT}")
    print(f"Daftar beda    : {DIFF}")

    if missing:
        raise SystemExit(f"Masih ada {missing} pasangan yang labelnya belum lengkap.")
    if disagreements and not args.adjudikasi:
        raise SystemExit(
            f"Masih ada {disagreements} perbedaan. Isi label_final pada "
            f"{DIFF.name}, lalu jalankan --adjudikasi {DIFF}."
        )


if __name__ == "__main__":
    main()
