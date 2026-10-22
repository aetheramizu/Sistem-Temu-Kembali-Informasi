"""
Membuat dua notebook Colab mandiri:
- notebooks/mesin_pencari_base_colab.ipynb      (Versi A, baseline)
- notebooks/mesin_pencari_updated_colab.ipynb   (Versi B, query expansion)

Keduanya menyematkan stki_utils.py dan data final ke dalam zip base64, lalu
mengekstraknya ke /content/stki_project. Dosen cukup membuka tautan Colab dan
memilih Runtime > Run all; tidak perlu mengunggah data atau mengatur path.

Jalankan dari root proyek:
    python scripts/build_colab_notebook.py
"""
from __future__ import annotations

import base64
import io
import textwrap
import zipfile
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parent.parent
BASE_SOURCE = ROOT / "notebooks" / "mesin_pencari.ipynb"
UPDATED_SOURCE = ROOT / "notebooks" / "mesin_pencari_updated.ipynb"
BASE_OUTPUT = ROOT / "notebooks" / "mesin_pencari_base_colab.ipynb"
UPDATED_OUTPUT = ROOT / "notebooks" / "mesin_pencari_updated_colab.ipynb"
LEGACY_OUTPUT = ROOT / "notebooks" / "mesin_pencari_colab.ipynb"

FILES = [
    "notebooks/stki_utils.py",
    "Data/korpus_final.csv",
    "Data/queries_25.csv",
    "Data/qrels_final.csv",
    "Data/kamus_sinonim.csv",
]

SETUP_TEMPLATE = '''#@title Setup data & modul (jalankan sekali) { display-mode: "form" }
# Sel ini membuat notebook mandiri: menulis stki_utils.py dan data final
# ke folder kerja, lalu menambahkan folder modul ke sys.path.
from pathlib import Path
import base64
import io
import sys
import zipfile

!pip -q --disable-pip-version-check install Sastrawi

BASE = Path("/content/stki_project") if Path("/content").exists() else Path.cwd() / "stki_project_colab"
BASE.mkdir(parents=True, exist_ok=True)

ZIP_B64 = """
__ZIP_B64__
"""

with zipfile.ZipFile(io.BytesIO(base64.b64decode(ZIP_B64))) as z:
    z.extractall(BASE)

sys.path.insert(0, str(BASE / "notebooks"))

import pandas as pd

korpus = pd.read_csv(BASE / "Data/korpus_final.csv")
queries = pd.read_csv(BASE / "Data/queries_25.csv")
qrels = pd.read_csv(BASE / "Data/qrels_final.csv")
assert (len(korpus), len(queries), len(qrels)) == (50, 25, 173), "Data tidak sesuai dataset final"
print(f"Setup selesai: {len(korpus)} dokumen, {len(queries)} query, {len(qrels)} qrels")
print(f"Modul dan data ada di: {BASE}")
'''

PATH_SETUP = '''import sys
from pathlib import Path

BASE = Path("/content/stki_project") if Path("/content/stki_project").exists() else Path.cwd() / "stki_project_colab"
if not (BASE / "notebooks" / "stki_utils.py").exists():
    raise FileNotFoundError(
        "Modul belum disiapkan. Jalankan sel setup di atas (Runtime > Run all)."
    )
sys.path.insert(0, str(BASE / "notebooks"))
'''

BASE_INTRO = '''# Mesin Pencari — Versi Dasar (Baseline)

**Kelompok 5 · Sistem Temu Kembali Informasi**

Notebook ini adalah **Versi A (baseline)** tanpa query expansion. Sistem dasar
memakai BM25 + stopword removal + stemming Sastrawi. Notebook juga menampilkan
eksperimen ablasi TF-IDF/BM25 × stopword × stemming untuk menunjukkan
konfigurasi terbaik yang dipakai sebagai baseline.

> **Menjalankan di Google Colab:** pilih **Runtime → Run all**. Sel setup
> pertama menyiapkan modul `stki_utils.py` dan data final secara otomatis,
> jadi tidak perlu mengunggah file atau mengatur path.

Versi B (baseline + query expansion sinonim) ada di notebook
`mesin_pencari_updated_colab.ipynb`.
'''

BASE_DEMO_MD = '''## Demo: Q03 (baseline)

Query Q03 (*strategi transformasi digital UMKM Indonesia*) dengan konfigurasi
baseline BM25 + stopword + stemming.
'''

BASE_EVAL_MD = '''## Evaluasi ablasi 25 query (k = 5)

Membandingkan TF-IDF/BM25 dan kombinasi stopword/stemming. Baris terakhir
(BM25 + stopword + stemming) adalah konfigurasi yang dipakai sebagai Versi A.
'''

BASE_OUTRO = '''**Hasil.** Konfigurasi terbaik adalah **BM25 + stopword + stemming**:
P@5 0,944; MAP 0,9103; nDCG@5 0,9370. Konfigurasi ini menjadi **Versi A
(baseline)**. Notebook **Versi B** (`mesin_pencari_updated_colab.ipynb`)
menambahkan query expansion sinonim dan membandingkan A vs B; hasilnya
P@5 0,968; MAP 0,9295; nDCG@5 0,9613.
'''

UPDATED_INTRO = '''# Mesin Pencari — BM25 + Stopword + Stemming + Query Expansion

**Kelompok 5 · Sistem Temu Kembali Informasi**

Notebook ini membandingkan **Versi A (baseline)** dan **Versi B (baseline +
ekspansi sinonim)** pada 50 dokumen, 25 query, dan 173 qrels final. Versi A
baseline ada di notebook `mesin_pencari_base_colab.ipynb`.

> **Menjalankan di Google Colab:** pilih **Runtime → Run all**. Sel setup
> pertama menyiapkan modul `stki_utils.py` dan data final secara otomatis,
> jadi tidak perlu mengunggah file atau mengatur path.

Peningkatan dilakukan pada sistem dasar BM25: term query yang punya padanan di
`Data/kamus_sinonim.csv` (10 pasangan) ditambah dengan sinonimnya berbobot
**0,5** sebelum dicari.

- `use_sinonim=False` → Versi A (baseline).
- `use_sinonim=True` → Versi B (baseline + sinonim).
'''

UPDATED_IMPORT_OLD = '''import re
import sys
import pandas as pd

sys.path.insert(1, "notebooks")  # bila notebook dijalankan dari root proyek
pd.set_option("display.max_colwidth", 120)
'''

UPDATED_IMPORT_NEW = '''import re
import sys
from pathlib import Path

import pandas as pd

# Sel setup menyiapkan modul di BASE/notebooks. Fallback ini membuat sel
# tetap bisa dijalankan ulang tanpa mengubah path.
BASE = Path("/content/stki_project") if Path("/content/stki_project").exists() else Path.cwd() / "stki_project_colab"
if not (BASE / "notebooks" / "stki_utils.py").exists():
    raise FileNotFoundError(
        "Modul belum disiapkan. Jalankan sel setup di atas (Runtime > Run all)."
    )
sys.path.insert(0, str(BASE / "notebooks"))

pd.set_option("display.max_colwidth", 120)
'''


def build_zip_b64() -> str:
    """Zip file yang dibutuhkan notebook, lalu base64 dengan baris 100 karakter."""
    missing = [f for f in FILES if not (ROOT / f).is_file()]
    if missing:
        raise FileNotFoundError("File tidak ditemukan: " + ", ".join(missing))

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in FILES:
            zf.write(ROOT / rel, arcname=rel)
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return "\n".join(textwrap.wrap(b64, width=100))


def make_setup_cell(b64_wrapped: str):
    setup_source = SETUP_TEMPLATE.replace("__ZIP_B64__", b64_wrapped)
    cell = nbformat.v4.new_code_cell(setup_source)
    cell["id"] = "colabsetup"
    cell["metadata"]["cellView"] = "form"
    cell["execution_count"] = None
    cell["outputs"] = []
    return cell


def set_metadata(nb) -> None:
    nb.metadata["colab"] = {"provenance": []}
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.metadata.setdefault("language_info", {"name": "python", "version": "3.12.5"})


def build_base(b64_wrapped: str):
    """Versi A: kelas baseline + demo Q03 + tabel ablasi 25 query."""
    src = nbformat.read(BASE_SOURCE, as_version=4)
    if len(src.cells) != 1 or src.cells[0].cell_type != "code":
        raise ValueError("Struktur mesin_pencari.ipynb berubah: expected 1 code cell.")

    code = src.cells[0].source
    marker = "queries, qrels = load_queries(), load_qrels()"
    if marker not in code:
        raise ValueError("Titik pemisah evaluasi tidak ditemukan di mesin_pencari.ipynb.")

    class_code, eval_code = code.split(marker, 1)
    class_code = PATH_SETUP.rstrip() + "\n\n" + class_code.strip() + "\n"
    eval_code = marker + eval_code

    demo_code = (
        "mesin = MesinPencari()\n"
        'mesin.tampilkan("strategi transformasi digital UMKM Indonesia", k=5)\n'
    )

    eval_cell = nbformat.v4.new_code_cell(eval_code)
    # Simpan output tabel asli agar notebook tetap informatif sebelum Run all.
    eval_cell["outputs"] = src.cells[0].get("outputs", [])
    eval_cell["execution_count"] = src.cells[0].get("execution_count")

    nb = nbformat.v4.new_notebook()
    set_metadata(nb)
    nb.cells = [
        nbformat.v4.new_markdown_cell(BASE_INTRO),
        make_setup_cell(b64_wrapped),
        nbformat.v4.new_code_cell(class_code),
        nbformat.v4.new_markdown_cell(BASE_DEMO_MD),
        nbformat.v4.new_code_cell(demo_code),
        nbformat.v4.new_markdown_cell(BASE_EVAL_MD),
        eval_cell,
        nbformat.v4.new_markdown_cell(BASE_OUTRO),
    ]
    return nb


def build_updated(b64_wrapped: str):
    """Versi B: Versi A vs Versi B + demo Q03 + tabel perbandingan."""
    nb = nbformat.read(UPDATED_SOURCE, as_version=4)
    if len(nb.cells) != 7:
        raise ValueError(f"Struktur notebook berubah: {len(nb.cells)} sel, expected 7.")

    intro_cell, import_cell, last_cell = nb.cells[0], nb.cells[1], nb.cells[-1]
    if "Mesin Pencari" not in intro_cell.source:
        raise ValueError("Sel pertama bukan judul notebook yang diharapkan.")
    if UPDATED_IMPORT_OLD not in import_cell.source:
        raise ValueError("Blok import notebook sumber tidak cocok.")
    if "Rincian ada di `docs/15_hasil_eksperimen.md`." not in last_cell.source:
        raise ValueError("Teks penutup notebook sumber tidak cocok.")

    intro_cell.source = UPDATED_INTRO
    import_cell.source = import_cell.source.replace(UPDATED_IMPORT_OLD, UPDATED_IMPORT_NEW, 1)
    last_cell.source = last_cell.source.replace(
        "Rincian ada di `docs/15_hasil_eksperimen.md`.",
        "Rincian lengkap ada di laporan proyek dan `docs/15_hasil_eksperimen.md` (di repo). "
        "Versi A baseline ada di notebook `mesin_pencari_base_colab.ipynb`.",
        1,
    )

    nb.cells.insert(1, make_setup_cell(b64_wrapped))
    set_metadata(nb)
    return nb


def main() -> None:
    b64_wrapped = build_zip_b64()

    base_nb = build_base(b64_wrapped)
    updated_nb = build_updated(b64_wrapped)

    nbformat.validate(base_nb)
    nbformat.validate(updated_nb)
    nbformat.write(base_nb, BASE_OUTPUT)
    nbformat.write(updated_nb, UPDATED_OUTPUT)

    if LEGACY_OUTPUT.exists():
        LEGACY_OUTPUT.unlink()
        print(f"Menghapus file lama: {LEGACY_OUTPUT.relative_to(ROOT)}")

    print(f"Ditulis: {BASE_OUTPUT.relative_to(ROOT)} ({len(base_nb.cells)} sel)")
    print(f"Ditulis: {UPDATED_OUTPUT.relative_to(ROOT)} ({len(updated_nb.cells)} sel)")
    print(f"Zip data: {len(base64.b64decode(b64_wrapped)):,} byte; base64: {len(b64_wrapped.replace(chr(10), '')):,} karakter")


if __name__ == "__main__":
    main()
