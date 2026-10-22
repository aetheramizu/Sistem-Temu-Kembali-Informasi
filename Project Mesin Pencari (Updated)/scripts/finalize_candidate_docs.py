"""Finalisasi 50 dokumen kandidat setelah verifikasi sumber.

Script ini:
1. membuat backup CSV kandidat,
2. menerapkan koreksi isi/tanggal/sumber yang ditemukan saat verifikasi,
3. menandai status `terverifikasi`,
4. membentuk `Data/korpus_final.csv` untuk eksperimen.

Jalankan: python scripts/finalize_candidate_docs.py
"""
from __future__ import annotations

import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
CANDIDATES = DATA / "kandidat_dokumen_50.csv"
BACKUP = DATA / "kandidat_dokumen_50_sebelum_verifikasi.csv"
CORPUS = DATA / "korpus_final.csv"
VERIFIED_AT = "2026-10-20"

# Koreksi yang didasarkan pada pembacaan teks sumber.
OVERRIDES = {
    "K002": {"tanggal_publikasi": "2023"},
    "K004": {"tanggal_publikasi": "2025-08-13"},
    "K006": {"tanggal_publikasi": "2022-01-15"},
    "K008": {
        "isi": (
            "Artikel MPR menyoroti 70,2 persen UMKM menghadapi kendala saat "
            "bertransformasi menggunakan teknologi digital. Kendala itu antara lain "
            "akses permodalan, bahan baku, dan adopsi teknologi digital. Pemerintah "
            "diminta segera mengatasinya agar digitalisasi UMKM berjalan merata."
        ),
        "tanggal_publikasi": "2023-08-04",
        "catatan": (
            "Isi diperbaiki agar sesuai sumber: kendala yang disebut adalah akses "
            "permodalan, bahan baku, dan adopsi teknologi, bukan kesiapan SDM."
        ),
    },
    "K009": {"tanggal_publikasi": "2024-09-17"},
    "K012": {"tanggal_publikasi": "2025-10-02"},
    "K013": {"tanggal_publikasi": "2023-08-19"},
    "K015": {"tanggal_publikasi": "2025-06-02"},
    "K016": {"tanggal_publikasi": "2022-10-17"},
    "K017": {"tanggal_publikasi": "2023"},
    "K018": {"tanggal_publikasi": "2025"},
    "K019": {
        "isi": (
            "Komdigi menyatakan Indonesia sedang menyiapkan otoritas pelindungan "
            "data pribadi yang independen. Lembaga tersebut akan bekerja secara "
            "independen dan melaporkan kepada presiden melalui Komdigi. Pembentukan "
            "otoritas ini menjadi langkah penting untuk memperkuat pelindungan data pribadi."
        ),
        "tanggal_publikasi": "2026-07-22",
        "catatan": (
            "Kalimat terakhir disesuaikan agar tidak mengklaim penegakan UU PDP "
            "yang tidak disebut eksplisit di sumber."
        ),
    },
    "K020": {"tanggal_publikasi": "2025-12-17"},
    "K023": {"tanggal_publikasi": "2025"},
    "K024": {"tanggal_publikasi": "2022-10-11"},
    "K025": {
        "judul": "Perkembangan Ekonomi Digital",
        "isi": (
            "Materi INDEF membahas perkembangan ekonomi digital Indonesia dan "
            "perannya bagi UMKM. Ekonomi digital tumbuh cepat seiring meningkatnya "
            "koneksi daring dan transaksi e-commerce. Materi ini juga menyoroti "
            "tantangan digital divide antarwilayah dan antarjenis usaha."
        ),
        "tanggal_publikasi": "2024",
        "catatan": (
            "Sumber asli dilindungi Cloudflare; teks diverifikasi melalui arsip "
            "Wayback Machine. Isi disesuaikan dengan bagian UMKM dan digital divide."
        ),
    },
    "K028": {
        "judul": (
            "Seluruh Sekolah Akan Mendapatkan Program Digitalisasi Sesuai Asas "
            "Keadilan dan Pemerataan"
        ),
        "isi": (
            "Program digitalisasi pembelajaran didukung Instruksi Presiden Nomor 7 "
            "Tahun 2025. Pemerintah menargetkan seluruh sekolah, termasuk di daerah "
            "terpencil dan tertinggal, menerima perangkat seperti IFP dan laptop. "
            "Langkah ini diarahkan untuk pemerataan kualitas pendidikan berbasis teknologi."
        ),
        "sumber": "Kementerian Pendidikan Dasar dan Menengah (Kemendikdasmen)",
        "jenis_sumber": "pemerintah",
        "url": (
            "https://www.kemendikdasmen.go.id/siaran-pers/13477-seluruh-sekolah-"
            "akan-mendapatkan-program-digitalisasi-sesuai-asas-keadilan-dan-pemerataan"
        ),
        "tanggal_publikasi": "2025-08-22",
        "catatan": (
            "Sumber diganti dari halaman program dinamis ke siaran pers resmi "
            "22 Agustus 2025 yang memuat fakta yang sama."
        ),
    },
    "K029": {"tanggal_publikasi": "2026-07-20"},
    "K031": {"tanggal_publikasi": "2023-05-26"},
    "K036": {"tanggal_publikasi": "2024"},
    "K038": {
        "tanggal_publikasi": "2022",
        "catatan": (
            "Tanggal 2022 adalah perkiraan dari konteks artikel (peristiwa 2019 "
            "disebut tiga tahun lalu); halaman tidak mencantumkan tanggal."
        ),
    },
    "K039": {"tanggal_publikasi": "2026-06-29"},
    "K040": {"tanggal_publikasi": "2025-08-29"},
    "K044": {"tanggal_publikasi": "2025-12-17"},
    "K045": {"tanggal_publikasi": "2025"},
    "K046": {"tanggal_publikasi": "2025-07-15"},
    "K047": {"tanggal_publikasi": "2025"},
    "K048": {"tanggal_publikasi": "2022-11-22"},
}

# Catatan tambahan untuk sumber yang judul halamannya generik/tidak terbaca.
NOTE_ADDITIONS = {
    "K002": "Judul halaman unduhan hanya menampilkan ID; isi PDF mendukung ringkasan.",
    "K004": "Judul halaman tidak terbaca dari metadata; isi berita mendukung ringkasan.",
    "K005": "Judul halaman berupa URL-terenkode; isi artikel mendukung ringkasan.",
    "K006": "Judul halaman generik; isi berita memuat angka 8 juta dan 16,4 juta UMKM.",
    "K007": "Judul halaman generik; isi berita memuat Program Level Up 2024.",
    "K009": "Judul halaman generik; isi berita memuat satu dekade transformasi UMKM.",
    "K011": "Judul PDF tidak terbaca; isi laporan memuat pilar literasi digital IMDI.",
    "K012": "Judul halaman generik; isi siaran pers memuat IMDI 44,53 dan kenaikan 1,19.",
    "K016": "Judul PDF tidak terbaca; isi artikel memuat UU Nomor 27 Tahun 2022.",
    "K023": "Judul diambil dari halaman sampul laporan PMSE 2025.",
    "K024": "Judul halaman generik; isi berita memuat USD77 miliar dan Rp1.197,8 triliun.",
    "K031": "Judul halaman generik; isi berita membahas integrasi layanan digital/SPBE.",
    "K033": "Halaman transformasi digital tidak mencantumkan tanggal publikasi.",
    "K038": "Isi artikel memuat Palapa Ring 12.148 km dan 90 kabupaten/kota.",
    "K046": "Judul halaman generik; isi berita memuat narasi Silicon Valley Asia Tenggara.",
}

FIELDS = [
    "no", "doc_id", "judul", "isi", "topik", "sumber", "jenis_sumber", "url",
    "tanggal_publikasi", "tanggal_akses", "status_verifikasi", "catatan",
    "anggota_pengumpul", "verifikator_1", "verifikator_2", "tanggal_verifikasi",
]


def main() -> None:
    if not BACKUP.exists():
        shutil.copy2(CANDIDATES, BACKUP)
        print(f"Backup dibuat: {BACKUP.name}")

    with CANDIDATES.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    for row in rows:
        doc_id = row["doc_id"]
        row.update(OVERRIDES.get(doc_id, {}))
        row["status_verifikasi"] = "terverifikasi"
        row["verifikator_1"] = "Review sumber"
        row["verifikator_2"] = "Review sumber"
        row["tanggal_verifikasi"] = VERIFIED_AT
        note = (
            "Verifikasi sumber: sumber dapat diakses dan teks sumber mendukung isi; "
            "bukan pengganti verifikasi penuh baris per baris."
        )
        if doc_id in NOTE_ADDITIONS:
            note += " " + NOTE_ADDITIONS[doc_id]
        if row.get("catatan"):
            note += " " + row["catatan"]
        row["catatan"] = note

    with CANDIDATES.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    corpus_fields = [
        "doc_id", "judul", "isi", "topik", "sumber", "jenis_sumber", "url",
        "tanggal_publikasi", "tanggal_akses", "status_verifikasi", "catatan",
    ]
    with CORPUS.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=corpus_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in corpus_fields})

    print(f"Kandidat final: {len(rows)} dokumen -> {CANDIDATES.name}")
    print(f"Korpus final  : {len(rows)} dokumen -> {CORPUS.name}")
    print("Status        :", {r["status_verifikasi"] for r in rows})
    print("Tanggal kosong:", [r["doc_id"] for r in rows if not r["tanggal_publikasi"]])


if __name__ == "__main__":
    main()
