"""Pembangunan inverted index dan positional index."""
from __future__ import annotations

from collections import Counter, defaultdict


def build_inverted_index(docs_tokens: dict[str, list[str]]) -> dict[str, dict[str, int]]:
    """{doc_id: [token]} -> {term: {doc_id: tf}}."""
    index: dict[str, dict[str, int]] = defaultdict(dict)
    for doc_id, tokens in docs_tokens.items():
        for term, tf in Counter(tokens).items():
            index[term][doc_id] = tf
    return dict(sorted(index.items()))


def build_positional_index(docs_tokens: dict[str, list[str]]) -> dict[str, dict[str, list[int]]]:
    """{doc_id: [token]} -> {term: {doc_id: [posisi, ...]}}."""
    index: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for doc_id, tokens in docs_tokens.items():
        for position, term in enumerate(tokens):
            index[term][doc_id].append(position)
    return {term: dict(postings) for term, postings in sorted(index.items())}
