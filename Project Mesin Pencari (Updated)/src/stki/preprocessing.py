"""Preprocessing bahasa Indonesia: case folding, tokenisasi, stopword, stemming."""
from __future__ import annotations

import re
from functools import lru_cache

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

_stemmer = StemmerFactory().create_stemmer()
STOPWORDS = set(StopWordRemoverFactory().get_stop_words())


def case_folding(text: str) -> str:
    return text.lower()


def tokenize(text: str) -> list[str]:
    """Memecah teks menjadi token huruf/angka; tanda baca dibuang."""
    return re.findall(r"[a-z0-9]+", text.lower())


def remove_stopwords(tokens: list[str], stopwords: set[str] | None = None) -> list[str]:
    stopwords = STOPWORDS if stopwords is None else stopwords
    return [token for token in tokens if token not in stopwords]


@lru_cache(maxsize=50_000)
def stem(token: str) -> str:
    return _stemmer.stem(token)


def preprocess(
    text: str,
    use_stopword: bool = True,
    use_stemming: bool = True,
    stopwords: set[str] | None = None,
) -> list[str]:
    tokens = tokenize(case_folding(text))
    if use_stopword:
        tokens = remove_stopwords(tokens, stopwords)
    if use_stemming:
        tokens = [stem(token) for token in tokens]
    return tokens
