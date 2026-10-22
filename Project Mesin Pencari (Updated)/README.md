# Mesin Pencari STKI — 50 Dokumen, 25 Query

Proyek Sistem Temu Kembali Informasi (STKI) untuk membandingkan dua konfigurasi mesin pencari:

- **Versi A:** BM25 + stopword removal + stemming (baseline).
- **Versi B:** Versi A + **query expansion sinonim domain** (bobot 0,5, kamus 10 pasangan).

Keduanya memakai `k1 = 1,5`, `b = 0,75`, korpus, query, qrels, dan aturan ranking yang sama.

> **Status final (2026-10-21):** korpus 50 dokumen ada di `Data/korpus_final.csv`, qrels final 173 pasangan ada di `Data/qrels_final.csv`, dan hasil A/B ada di `experiments/results/final_review/`. Qrels memakai skala 1/2/3 dengan distribusi 63 label 3, 69 label 2, dan 41 label 1.
> **Koreksi Oktober 2026:** 30 dokumen di `Data/korpus.csv`, 8 query, dan qrels lama adalah contoh praktikum. Koleksi final adalah **50 dokumen baru, 25 query, 5 anggota** untuk domain Transformasi Digital dan Teknologi di Indonesia.

## Struktur proyek

```text
Data/
  korpus.csv                 # 30 dokumen asli (jangan diubah)
  queries.csv                # 8 query asli
  qrels.csv                  # qrels asli
  korpus_final.csv           # FINAL: 50 dokumen baru, 10 subtopik x 5
  kandidat_dokumen_50.csv    # data kandidat final + metadata + status verifikasi/review
  verifikasi_final.csv       # keputusan verifikasi sumber/isi per dokumen
  review/                    # lembar review independen + adjudikasi
  queries_25.csv             # 25 query final Q01–Q25
  qrels_final.csv            # FINAL: 173 pasangan, label 1/2/3
  qrels_final_metadata.json  # checksum, distribusi label, kesepakatan, provenance
  kamus_sinonim.csv          # kamus sinonim domain (10 pasangan, untuk Versi B)
  lembar_penilaian_final.csv # gabungan label, alasan, adjudikasi, status
  spreadsheet_kerja_stki.xlsx    # rekap final: 50 dokumen, 25 query, 173 penilaian, progress
  template_kandidat_dokumen.csv  # template pengumpulan dokumen baru
  kandidat_query_awal.csv        # arsip 30 kandidat query
src/stki/                    # pipeline: preprocessing, indexing, retrieval, query_expansion, evaluation
experiments/
  versi_a/config.json
  versi_b/config.json
  run_experiment.py
  compare_versions.py
  results/final_review/      # hasil A/B final
tests/test_pipeline.py       # unit + regression test
tests/fixtures/              # data uji regresi dataset lama; bukan data final
scripts/
  finalize_candidate_docs.py  # koreksi kandidat + bentuk korpus_final.csv
  merge_review.py             # menggabungkan lembar review + adjudikasi
  freeze_qrels.py             # membekukan qrels final
  label_status.py             # memantau status lembar penilaian
  check_sources.py            # mengecek ulang status HTTP sumber
  build_spreadsheet_kerja.py  # generator workbook rekap final
  build_colab_notebook.py     # generator dua notebook Colab mandiri
notebooks/                   # praktikum 01-11 + mesin_pencari.ipynb (basis Colab) + mesin_pencari_updated.ipynb
```

## Kebutuhan

- Python 3.12+
- Lihat `requirements.txt`.

Instalasi (opsional, hanya jika environment belum siap):

```powershell
python -m pip install -r requirements.txt
```

## Menjalankan test

```powershell
python -m unittest discover -s tests -v
```

Test mencakup reproduksi baseline lama:

- BM25 MAP `0,775645`, nDCG@5 `0,866763`
- TF-IDF MAP `0,761954`
- Boolean OR MAP `0,651128`

Dan test unit untuk modul query expansion: `expand_query`, `load_synonyms`, dan integrasi `SearchEngine` dengan expansion.

## Menjalankan notebook

### Jupyter/VS Code

Buka `notebooks/mesin_pencari_updated.ipynb` dari folder `notebooks/` (default Jupyter/VS Code), lalu **Run All**. Notebook berisi:

- Versi A (BM25 + stopword + stemming) dan Versi B (ditambah ekspansi sinonim dari `Data/kamus_sinonim.csv`),
- demo Q03 (`transformasi → digitalisasi`),
- tabel P@5, MAP, dan nDCG@5 untuk 25 query.

Angka notebook sama dengan `experiments/results/final_review/ringkasan_a_b.csv`.

### Google Colab

Dua notebook mandiri untuk dosen/penguji:

- `notebooks/mesin_pencari_base_colab.ipynb` — **Versi A** (baseline, tanpa query expansion).
- `notebooks/mesin_pencari_updated_colab.ipynb` — **Versi B** (baseline + query expansion sinonim).

Keduanya menyematkan `stki_utils.py` dan data final (50 dokumen, 25 query, 173 qrels); sel setup mengekstraknya ke `/content/stki_project`. Tidak perlu mengunggah data atau mengatur path.

Versi A menampilkan demo Q03 dan tabel ablasi (konfigurasi terbaik: BM25 + stopword + stemming). Versi B menampilkan demo Q03 dan perbandingan A vs B.

1. Buka [Google Colab](https://colab.research.google.com/), lalu **File → Upload notebook** dan upload kedua file.
2. **File → Save a copy in Drive** untuk masing-masing. Di Drive, keduanya bisa dinamai `mesin_pencari.ipynb` (Versi A) dan `mesin_pencari_improved.ipynb` (Versi B), mengikuti contoh teman.
3. **Runtime → Run all** di masing-masing notebook. Sel setup memasang Sastrawi dan menyiapkan 50 dokumen, 25 query, serta 173 qrels.
4. Klik **Share** → **Anyone with the link** pada kedua notebook. Pilih **Editor** agar dosen bisa langsung **Runtime → Run all**; jika ingin read-only, pilih **Viewer** dan minta dosen memilih **File → Save a copy in Drive** sebelum menjalankan.
5. Salin dua tautan. Pastikan keduanya berawalan `https://colab.research.google.com/drive/...`.

Colab meminta dosen login akun Google untuk menjalankan kode. Uji kedua tautan dengan akun Google lain atau jendela incognito sebelum dikumpulkan.

CSV di Google Drive tidak dibutuhkan oleh kedua notebook karena data sudah disematkan. File CSV boleh tetap disimpan sebagai arsip.

Untuk membuat ulang kedua notebook Colab setelah data atau notebook berubah:

```powershell
python scripts/build_colab_notebook.py
```

## Menjalankan eksperimen final

```powershell
python experiments/run_experiment.py --config experiments/versi_a/config.json --qrels Data/qrels_final.csv --output-dir experiments/results/final_review --label final_review
python experiments/run_experiment.py --config experiments/versi_b/config.json --qrels Data/qrels_final.csv --output-dir experiments/results/final_review --label final_review
python experiments/compare_versions.py --results-dir experiments/results/final_review --qrels Data/qrels_final.csv --metric-k 5
```

## Hasil eksperimen final (2026-10-21)

Detail per query ada di `experiments/results/final_review/`.

| Metrik | Versi A | Versi B | Selisih B−A |
|---|---:|---:|---:|
| P@5 | 0,9440 | 0,9680 | +0,0240 |
| R@5 | 0,7145 | 0,7358 | +0,0213 |
| F1@5 | 0,8041 | 0,8266 | +0,0225 |
| MAP | 0,9103 | 0,9295 | +0,0192 |
| nDCG@5 | 0,9370 | 0,9613 | +0,0243 |

Bootstrap AP: 95% CI `[−0,0473; −0,0007]`, **signifikan**. nDCG@5: `[−0,0488; −0,0060]`, **signifikan**. Versi B (baseline + query expansion) lebih tinggi pada semua metrik; expansion membantu menemukan dokumen domain yang menggunakan istilah berbeda dari query.

## Qrels final

- 25 query, 173 pasangan query–dokumen.
- Label: **63 label 3, 69 label 2, 41 label 1**.
- Setiap query punya minimal 5 dokumen relevan.
- Dokumen nonrelevan tidak dimasukkan ke qrels; tidak ada label 0.
- Checksum dan metadata ada di `Data/qrels_final_metadata.json`.
- Rincian review dan adjudikasi ada di `Data/review/`.

## Batasan

- 50 dokumen final berbentuk ringkasan 3 kalimat berdasarkan sumber, bukan kutipan verbatim.
- Review sumber: 9 `cocok`, 41 `cukup`, 0 `tidak_cocok`; status `cukup` berarti isi sudah sesuai ringkasan, tetapi belum diverifikasi baris per baris.
- K033 tidak mencantumkan tanggal publikasi; K038 memakai perkiraan 2022.
- 30 dokumen lama di `Data/korpus.csv` tetap disimpan untuk reproduksi modul 1–6.
- Repository: <https://github.com/aetheramizu/Sistem-Temu-Kembali-Informasi>
- Dokumen kerja (`docs/`, file `.docx`) disimpan lokal dan tidak di-commit.
