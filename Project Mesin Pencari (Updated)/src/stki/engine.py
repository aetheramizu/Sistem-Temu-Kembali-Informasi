"""Mesin pencari yang menyatukan preprocessing, indexing, dan retrieval."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

import pandas as pd

from .config import (
    DEFAULT_B,
    DEFAULT_CORPUS,
    DEFAULT_EXPANSION_WEIGHT,
    DEFAULT_K1,
    DEFAULT_SYNONYMS,
)
from .data import corpus_texts, load_corpus
from .preprocessing import preprocess
from .query_expansion import expand_query, load_synonyms
from .retrieval import BM25Model, TfidfModel


class SearchEngine:
    """Mesin pencari dengan konfigurasi eksplisit.

    Model yang didukung: "bm25" dan "tfidf".
    Boolean tidak dimasukkan ke kelas ini karena bukan bagian eksperimen A/B.
    Query expansion bersifat opsional dan hanya menambah bobot term query.
    """

    def __init__(
        self,
        corpus_path: str | Path = DEFAULT_CORPUS,
        model: str = "bm25",
        use_stopword: bool = True,
        use_stemming: bool = True,
        use_query_expansion: bool = False,
        expansion_weight: float = DEFAULT_EXPANSION_WEIGHT,
        synonyms_path: str | Path = DEFAULT_SYNONYMS,
        k1: float = DEFAULT_K1,
        b: float = DEFAULT_B,
    ):
        self.corpus_path = Path(corpus_path)
        self.corpus_df = load_corpus(self.corpus_path)
        self.corpus = self.corpus_df.set_index("doc_id", drop=False)
        self.options = {
            "use_stopword": bool(use_stopword),
            "use_stemming": bool(use_stemming),
        }
        self.docs_tokens = {
            doc_id: preprocess(text, **self.options)
            for doc_id, text in corpus_texts(self.corpus_df).items()
        }
        if model == "bm25":
            self.model = BM25Model(self.docs_tokens, k1=k1, b=b)
        elif model == "tfidf":
            self.model = TfidfModel(self.docs_tokens)
        else:
            raise ValueError(f"Model tidak dikenal: {model}")
        self.model_name = model
        self.k1 = float(k1)
        self.b = float(b)
        self.use_query_expansion = bool(use_query_expansion)
        self.expansion_weight = float(expansion_weight)
        self._synonyms: dict[str, tuple[str, ...]] = {}
        if self.use_query_expansion:
            self._synonyms = load_synonyms(
                path=Path(synonyms_path),
                use_stemming=bool(use_stemming),
            )

    def search(self, query: str, k: int = 10) -> list[tuple[str, float]]:
        q_tokens = preprocess(query, **self.options)
        if self.use_query_expansion and isinstance(self.model, BM25Model):
            q_weights = expand_query(q_tokens, self._synonyms, self.expansion_weight)
            return self.model.search_weighted(q_weights, k=k)
        return self.model.search(q_tokens, k=k)

    def search_ids(self, query: str, k: int = 10) -> list[str]:
        return [doc_id for doc_id, _ in self.search(query, k=k)]

    def run(self, queries: Mapping[str, str], k: int = 10) -> dict[str, list[str]]:
        return {query_id: self.search_ids(query, k=k) for query_id, query in queries.items()}

    def document_title(self, doc_id: str) -> str:
        return str(self.corpus.loc[doc_id, "judul"])

    def results_frame(self, query: str, k: int = 10) -> pd.DataFrame:
        rows = []
        for rank, (doc_id, score) in enumerate(self.search(query, k=k), start=1):
            row = self.corpus.loc[doc_id]
            rows.append(
                {
                    "rank": rank,
                    "doc_id": doc_id,
                    "judul": row["judul"],
                    "skor": score,
                }
            )
        return pd.DataFrame(rows)
