"""Model retrieval: Boolean, TF-IDF (cosine), dan BM25 Okapi."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

from .indexing import build_inverted_index
from .preprocessing import preprocess


def boolean_search(
    query: str,
    index: dict[str, dict[str, int]],
    all_docs: list[str] | set[str],
    use_stemming: bool = True,
) -> list[str]:
    """Query Boolean dengan AND, OR, NOT, dan tanda kurung.

    Prioritas: NOT > AND > OR. Term dipreprocess tanpa stopword removal.
    """
    all_docs = set(all_docs)
    tokens = re.findall(r"\(|\)|[^\s()]+", query)
    pos = 0

    def peek() -> str | None:
        return tokens[pos] if pos < len(tokens) else None

    def take() -> str:
        nonlocal pos
        pos += 1
        return tokens[pos - 1]

    def parse_or() -> set[str]:
        result = parse_and()
        while peek() == "OR":
            take()
            result = result | parse_and()
        return result

    def parse_and() -> set[str]:
        result = parse_not()
        while peek() == "AND":
            take()
            result = result & parse_not()
        return result

    def parse_not() -> set[str]:
        if peek() == "NOT":
            take()
            return all_docs - parse_not()
        if peek() == "(":
            take()
            result = parse_or()
            if take() != ")":
                raise ValueError("Kurung tidak seimbang")
            return result
        term = preprocess(take(), use_stopword=False, use_stemming=use_stemming)
        return set(index.get(term[0], {})) if term else set()

    result = parse_or()
    if pos != len(tokens):
        raise ValueError(f"Query tidak valid di dekat '{tokens[pos]}'")
    return sorted(result)


class TfidfModel:
    """TF log10, IDF log10(N/df), cosine normalization."""

    def __init__(self, docs_tokens: dict[str, list[str]]):
        self.index = build_inverted_index(docs_tokens)
        self.N = len(docs_tokens)
        self.idf = {
            term: math.log10(self.N / len(postings))
            for term, postings in self.index.items()
        }
        self.doc_vectors: dict[str, dict[str, float]] = {}
        for doc_id, tokens in docs_tokens.items():
            vector = {
                term: (1 + math.log10(tf)) * self.idf[term]
                for term, tf in Counter(tokens).items()
            }
            self.doc_vectors[doc_id] = _normalize(vector)

    def query_vector(self, q_tokens: list[str]) -> dict[str, float]:
        vector = {
            term: (1 + math.log10(tf)) * self.idf[term]
            for term, tf in Counter(q_tokens).items()
            if term in self.idf
        }
        return _normalize(vector)

    def search(self, q_tokens: list[str], k: int = 10) -> list[tuple[str, float]]:
        qv = self.query_vector(q_tokens)
        scores: dict[str, float] = defaultdict(float)
        for term, weight in qv.items():
            for doc_id in self.index[term]:
                scores[doc_id] += weight * self.doc_vectors[doc_id][term]
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]


def _normalize(vector: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(weight * weight for weight in vector.values()))
    return {term: weight / norm for term, weight in vector.items()} if norm > 0 else {}


class BM25Model:
    """BM25 Okapi dengan tie-break doc_id menaik."""

    def __init__(
        self,
        docs_tokens: dict[str, list[str]],
        k1: float = 1.5,
        b: float = 0.75,
    ):
        if not docs_tokens:
            raise ValueError("Korpus kosong")
        self.index = build_inverted_index(docs_tokens)
        self.k1 = float(k1)
        self.b = float(b)
        self.N = len(docs_tokens)
        self.doc_len = {doc_id: len(tokens) for doc_id, tokens in docs_tokens.items()}
        self.avgdl = sum(self.doc_len.values()) / self.N
        self.idf = {
            term: math.log(1 + (self.N - len(postings) + 0.5) / (len(postings) + 0.5))
            for term, postings in self.index.items()
        }

    def score_term(self, term: str, doc_id: str) -> float:
        tf = self.index.get(term, {}).get(doc_id, 0)
        if tf == 0:
            return 0.0
        norm = self.k1 * (1 - self.b + self.b * self.doc_len[doc_id] / self.avgdl)
        return self.idf[term] * tf * (self.k1 + 1) / (tf + norm)

    def search(self, q_tokens: list[str], k: int = 10) -> list[tuple[str, float]]:
        scores: dict[str, float] = defaultdict(float)
        for term in q_tokens:
            for doc_id in self.index.get(term, {}):
                scores[doc_id] += self.score_term(term, doc_id)
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]

    def search_weighted(
        self, q_weights: dict[str, float], k: int = 10
    ) -> list[tuple[str, float]]:
        scores: dict[str, float] = defaultdict(float)
        for term, weight in q_weights.items():
            for doc_id in self.index.get(term, {}):
                scores[doc_id] += weight * self.score_term(term, doc_id)
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]
