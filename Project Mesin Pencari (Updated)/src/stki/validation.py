"""Validasi dataset dan checksum untuk reproducibility."""
from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path

import pandas as pd


class DatasetValidationError(ValueError):
    """Dataset tidak memenuhi kontrak minimal."""


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_dataset(
    corpus: pd.DataFrame,
    queries: pd.DataFrame,
    qrels: pd.DataFrame,
    expected_docs: int | None = 50,
    expected_queries: int | None = 25,
    docs_per_topic: int | None = 10,
    queries_per_topic: int | None = 5,
    min_relevant_per_query: int = 2,
    strict_grades: bool = True,
    expected_topics: int | None = 5,
) -> list[str]:
    """Memvalidasi korpus, query, dan qrels.

    Mengembalikan daftar warning (bukan error). Error dilempar sebagai
    DatasetValidationError agar pipeline berhenti sebelum eksperimen.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Untuk dataset legacy/kecil, jangan paksakan distribusi 10/5 kecuali
    # jumlah dokumen/query juga diminta.
    if expected_docs is None:
        docs_per_topic = None
    if expected_queries is None:
        queries_per_topic = None

    for name, frame, columns in [
        ("korpus", corpus, {"doc_id", "judul", "isi"}),
        ("queries", queries, {"query_id", "query"}),
        ("qrels", qrels, {"query_id", "doc_id", "relevance"}),
    ]:
        missing = columns - set(frame.columns)
        if missing:
            errors.append(f"{name}: kolom hilang {sorted(missing)}")

    if errors:
        raise DatasetValidationError("; ".join(errors))

    if expected_docs is not None and len(corpus) != expected_docs:
        errors.append(f"korpus: {len(corpus)} dokumen, seharusnya {expected_docs}")
    if expected_queries is not None and len(queries) != expected_queries:
        errors.append(f"queries: {len(queries)} query, seharusnya {expected_queries}")

    if corpus["doc_id"].duplicated().any():
        dup = corpus.loc[corpus["doc_id"].duplicated(), "doc_id"].tolist()
        errors.append(f"korpus: doc_id duplikat {dup}")
    if queries["query_id"].duplicated().any():
        dup = queries.loc[queries["query_id"].duplicated(), "query_id"].tolist()
        errors.append(f"queries: query_id duplikat {dup}")
    if qrels.duplicated(["query_id", "doc_id"]).any():
        errors.append("qrels: pasangan query_id-doc_id duplikat")

    if (corpus["judul"].str.strip() == "").any():
        errors.append("korpus: ada judul kosong")
    if (corpus["isi"].str.strip() == "").any():
        errors.append("korpus: ada isi kosong")
    if (queries["query"].str.strip() == "").any():
        errors.append("queries: ada query kosong")

    doc_ids = set(corpus["doc_id"])
    query_ids = set(queries["query_id"])
    unknown_docs = sorted(set(qrels["doc_id"]) - doc_ids)
    unknown_queries = sorted(set(qrels["query_id"]) - query_ids)
    if unknown_docs:
        errors.append(f"qrels: doc_id tidak ada di korpus {unknown_docs}")
    if unknown_queries:
        errors.append(f"qrels: query_id tidak ada di queries {unknown_queries}")

    if strict_grades:
        bad_grades = sorted(set(qrels["relevance"]) - {1, 2, 3})
        if bad_grades:
            errors.append(f"qrels: label di luar 1/2/3 {bad_grades}")

    if "topik" in corpus.columns:
        counts = corpus["topik"].value_counts().to_dict()
        if docs_per_topic is not None:
            wrong = {topic: count for topic, count in counts.items() if count != docs_per_topic}
            if wrong:
                errors.append(f"korpus: distribusi topik tidak seimbang {wrong}")
        if expected_topics is not None and len(counts) != expected_topics:
            warnings.append(
                f"korpus: jumlah topik {len(counts)}, seharusnya {expected_topics}"
            )
    else:
        warnings.append("korpus: kolom topik tidak ada; distribusi topik tidak dicek")

    if "topik" in queries.columns:
        counts = queries["topik"].value_counts().to_dict()
        if queries_per_topic is not None:
            wrong = {topic: count for topic, count in counts.items() if count != queries_per_topic}
            if wrong:
                errors.append(f"queries: distribusi topik tidak seimbang {wrong}")
    else:
        warnings.append("queries: kolom topik tidak ada; distribusi topik tidak dicek")

    relevant_per_query = (
        qrels[qrels["relevance"] > 0].groupby("query_id")["doc_id"].nunique().to_dict()
    )
    for query_id in sorted(query_ids):
        count = int(relevant_per_query.get(query_id, 0))
        if count < min_relevant_per_query:
            errors.append(
                f"qrels: query {query_id} hanya punya {count} dokumen relevan "
                f"(minimal {min_relevant_per_query})"
            )

    judged_docs = set(qrels["doc_id"])
    unjudged = sorted(doc_ids - judged_docs)
    if unjudged:
        warnings.append(f"korpus: dokumen tidak pernah dinilai {unjudged}")

    judged_queries = set(qrels["query_id"])
    missing_queries = sorted(query_ids - judged_queries)
    if missing_queries:
        errors.append(f"qrels: query belum dinilai {missing_queries}")

    if errors:
        raise DatasetValidationError("; ".join(errors))
    return warnings


def topic_distribution(df: pd.DataFrame, column: str = "topik") -> dict[str, int]:
    if column not in df.columns:
        return {}
    return dict(Counter(df[column]).most_common())
