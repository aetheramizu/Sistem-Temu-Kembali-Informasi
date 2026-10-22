"""Query expansion berbasis kamus sinonim dan istilah domain.

Kamus disimpan sebagai CSV agar dapat diaudit tanpa membaca kode. Istilah
dinormalisasi dengan preprocessing yang sama seperti query, sehingga kamus
tetap konsisten saat stemming aktif maupun nonaktif.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from .config import DEFAULT_EXPANSION_WEIGHT, DEFAULT_SYNONYMS
from .preprocessing import preprocess


def _normalize_term(term: str, use_stemming: bool) -> str:
    tokens = preprocess(term, use_stopword=False, use_stemming=use_stemming)
    if len(tokens) != 1:
        raise ValueError(
            f"Istilah kamus harus satu token setelah preprocessing: {term!r} -> {tokens}"
        )
    return tokens[0]


@lru_cache(maxsize=8)
def load_synonyms(
    path: str | Path = DEFAULT_SYNONYMS,
    use_stemming: bool = True,
) -> dict[str, tuple[str, ...]]:
    """Memuat kamus CSV menjadi mapping term -> sinonim ternormalisasi.

    Kolom wajib: ``term`` dan ``sinonim``. Kolom ``jenis`` dan ``alasan``
    bersifat dokumentasi. Baris dengan term yang sama digabung.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Kamus sinonim tidak ditemukan: {path}")

    synonyms: dict[str, list[str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"term", "sinonim"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Kolom kamus hilang: {sorted(missing)}")

        for line_number, row in enumerate(reader, start=2):
            raw_term = (row.get("term") or "").strip()
            raw_synonym = (row.get("sinonim") or "").strip()
            if not raw_term and not raw_synonym:
                continue
            if not raw_term or not raw_synonym:
                raise ValueError(f"Baris {line_number}: term dan sinonim wajib diisi")

            term = _normalize_term(raw_term, use_stemming)
            synonym = _normalize_term(raw_synonym, use_stemming)
            if term == synonym:
                raise ValueError(f"Baris {line_number}: sinonim sama dengan term ({term})")

            values = synonyms.setdefault(term, [])
            if synonym not in values:
                values.append(synonym)

    if not synonyms:
        raise ValueError(f"Kamus sinonim kosong: {path}")
    return {term: tuple(values) for term, values in synonyms.items()}


def expand_query(
    tokens: list[str],
    synonyms: dict[str, tuple[str, ...]],
    weight: float = DEFAULT_EXPANSION_WEIGHT,
) -> dict[str, float]:
    """Mengubah token query menjadi bobot term dengan tambahan sinonim.

    Term asli mempertahankan bobot 1,0 per kemunculan. Sinonim ditambahkan
    satu kali dengan bobot ``weight`` dan tidak menimpa term asli. Expansion
    hanya satu langkah (tidak rekursif).
    """
    weight = float(weight)
    if weight < 0:
        raise ValueError("Bobot expansion tidak boleh negatif")

    weights: dict[str, float] = {}
    for token in tokens:
        weights[token] = weights.get(token, 0.0) + 1.0

    if weight == 0:
        return weights

    for token in set(tokens):
        for synonym in synonyms.get(token, ()):
            weights[synonym] = max(weights.get(synonym, 0.0), weight)
    return weights
