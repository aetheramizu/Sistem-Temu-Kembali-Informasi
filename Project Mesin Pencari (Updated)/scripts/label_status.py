"""Menampilkan progres pengisian lembar penilaian tanpa membuat qrels final."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def resolve(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="Data/lembar_penilaian_final.csv")
    args = parser.parse_args()

    path = resolve(args.input)
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    total = len(df)

    for column in ["label_penilai_1", "label_penilai_2", "label_final"]:
        if column not in df.columns:
            raise ValueError(f"Kolom tidak ditemukan: {column}")
        df[column] = pd.to_numeric(df[column], errors="coerce")

    filled_1 = df["label_penilai_1"].notna()
    filled_2 = df["label_penilai_2"].notna()
    filled_final = df["label_final"].notna()
    both = filled_1 & filled_2
    disagreements = both & (df["label_penilai_1"] != df["label_penilai_2"])
    noted = disagreements & (df["catatan_anggota"].str.strip() != "")

    print(f"Lembar: {path}")
    print(f"Total pasangan           : {total}")
    print(f"Label penilai 1 terisi   : {filled_1.sum()}/{total}")
    print(f"Label penilai 2 terisi   : {filled_2.sum()}/{total}")
    print(f"Label final terisi       : {filled_final.sum()}/{total}")
    print(f"Kedua penilai terisi     : {both.sum()}/{total}")
    print(f"Pasangan berbeda label   : {disagreements.sum()}")
    print(f"Sudah ada catatan adjudikasi: {noted.sum()}/{max(disagreements.sum(), 1)}")
    print("Status verifikasi:")
    print(df["status_verifikasi"].value_counts().to_string())

    if both.sum() < total:
        print("\nLangkah berikutnya: lengkapi label penilai 1 dan 2 yang masih kosong.")
    elif disagreements.sum() > noted.sum():
        print("\nLangkah berikutnya: adjudikasi pasangan yang berbeda dan isi `catatan_anggota`.")
    elif not filled_final.all():
        print("\nLangkah berikutnya: isi `label_final` untuk semua baris.")
    else:
        print("\nLangkah berikutnya: set `status_verifikasi` menjadi `disetujui`, lalu jalankan scripts/freeze_qrels.py.")


if __name__ == "__main__":
    main()
