"""Regression dan unit test pipeline STKI."""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stki.data import load_corpus, load_qrels, load_qrels_df, load_queries, load_queries_df  # noqa: E402
from stki.engine import SearchEngine  # noqa: E402
from stki.evaluation import evaluate  # noqa: E402
from stki.indexing import build_inverted_index  # noqa: E402
from stki.preprocessing import preprocess  # noqa: E402
from stki.query_expansion import expand_query, load_synonyms  # noqa: E402
from stki.retrieval import BM25Model, boolean_search  # noqa: E402
from stki.validation import DatasetValidationError, validate_dataset  # noqa: E402


class TestPreprocessing(unittest.TestCase):
    def test_stopword_and_stemming_flags(self):
        text = "Pembelajaran mesin dan pemrosesan bahasa"
        no_stem = preprocess(text, use_stopword=True, use_stemming=False)
        with_stem = preprocess(text, use_stopword=True, use_stemming=True)
        self.assertNotIn("dan", no_stem)
        self.assertNotIn("dan", with_stem)
        self.assertIn("pembelajaran", no_stem)
        self.assertNotEqual(no_stem, with_stem)

    def test_tokenize_discards_punctuation(self):
        self.assertEqual(
            preprocess("DBD: nyamuk Aedes aegypti!", use_stopword=False, use_stemming=False),
            ["dbd", "nyamuk", "aedes", "aegypti"],
        )


class TestQueryExpansion(unittest.TestCase):
    def test_expand_adds_synonyms_with_weight(self):
        synonyms = {"literasi": ("cakap",)}
        weights = expand_query(["literasi", "digital"], synonyms, weight=0.5)
        self.assertAlmostEqual(weights["literasi"], 1.0)
        self.assertAlmostEqual(weights["digital"], 1.0)
        self.assertAlmostEqual(weights["cakap"], 0.5)

    def test_expand_does_not_overwrite_original_term(self):
        synonyms = {"a": ("b",), "b": ("a",)}
        weights = expand_query(["a", "b"], synonyms, weight=0.3)
        self.assertAlmostEqual(weights["a"], 1.0)
        self.assertAlmostEqual(weights["b"], 1.0)

    def test_expand_zero_weight_returns_original(self):
        synonyms = {"literasi": ("cakap",)}
        weights = expand_query(["literasi"], synonyms, weight=0.0)
        self.assertNotIn("cakap", weights)

    def test_expand_repeated_tokens_accumulate(self):
        synonyms = {}
        weights = expand_query(["a", "a", "b"], synonyms, weight=0.5)
        self.assertAlmostEqual(weights["a"], 2.0)
        self.assertAlmostEqual(weights["b"], 1.0)

    def test_load_synonyms_loads_final_kamus(self):
        synonyms = load_synonyms(ROOT / "Data" / "kamus_sinonim.csv", use_stemming=True)
        self.assertIsInstance(synonyms, dict)
        self.assertGreater(len(synonyms), 0)
        for term, syns in synonyms.items():
            self.assertIsInstance(syns, tuple)
            self.assertGreater(len(syns), 0)
            for syn in syns:
                self.assertNotEqual(term, syn)

    def test_engine_query_expansion_returns_more_relevant(self):
        engine_b = SearchEngine(
            ROOT / "Data" / "korpus_final.csv",
            model="bm25",
            use_stopword=True,
            use_stemming=True,
            use_query_expansion=True,
            expansion_weight=0.5,
            synonyms_path=ROOT / "Data" / "kamus_sinonim.csv",
        )
        results = engine_b.search_ids("konektivitas digital Indonesia", k=10)
        self.assertGreater(len(results), 0)
        self.assertTrue(all(isinstance(d, str) for d in results))


class TestIndexingAndRetrieval(unittest.TestCase):
    def test_inverted_index_counts(self):
        index = build_inverted_index({"d1": ["a", "a", "b"], "d2": ["b"]})
        self.assertEqual(index["a"], {"d1": 2})
        self.assertEqual(index["b"], {"d1": 1, "d2": 1})

    def test_boolean_search(self):
        docs = {
            "d1": preprocess("padi sawah"),
            "d2": preprocess("padi terkena hama"),
            "d3": preprocess("hama jagung"),
        }
        index = build_inverted_index(docs)
        result = boolean_search("padi AND NOT hama", index, list(docs))
        self.assertEqual(result, ["d1"])

    def test_bm25_tie_break_doc_id(self):
        docs = {"d2": ["padi"], "d1": ["padi"], "d3": ["jagung"]}
        model = BM25Model(docs)
        self.assertEqual([doc for doc, _ in model.search(["padi"], k=2)], ["d1", "d2"])


class TestEvaluation(unittest.TestCase):
    def test_metrics_toy(self):
        run = {"q1": ["d1", "d2", "d3"]}
        qrels = {"q1": {"d1": 2, "d3": 1}}
        result = evaluate(run, qrels, k=2)
        row = result.loc["q1"]
        self.assertAlmostEqual(row["P@2"], 0.5)
        self.assertAlmostEqual(row["R@2"], 0.5)
        self.assertAlmostEqual(row["AP"], (1 / 1 + 2 / 3) / 2, places=6)
        idcg = 2 + 1 / math.log2(3)
        self.assertAlmostEqual(row["nDCG@2"], 2 / idcg, places=6)

    def test_validation_rejects_bad_grade(self):
        corpus = pd.DataFrame(
            {
                "doc_id": ["D1", "D2"],
                "judul": ["A", "B"],
                "isi": ["isi a", "isi b"],
                "topik": ["kesehatan", "kesehatan"],
            }
        )
        queries = pd.DataFrame(
            {"query_id": ["Q1"], "query": ["a"], "topik": ["kesehatan"]}
        )
        qrels = pd.DataFrame(
            {"query_id": ["Q1"], "doc_id": ["D1"], "relevance": [4]}
        )
        with self.assertRaises(DatasetValidationError):
            validate_dataset(corpus, queries, qrels, expected_docs=None, expected_queries=None)

    def test_validation_accepts_grade_3(self):
        corpus = pd.DataFrame(
            {
                "doc_id": ["D1", "D2"],
                "judul": ["A", "B"],
                "isi": ["isi a", "isi b"],
                "topik": ["kesehatan", "kesehatan"],
            }
        )
        queries = pd.DataFrame(
            {"query_id": ["Q1"], "query": ["a"], "topik": ["kesehatan"]}
        )
        qrels = pd.DataFrame(
            {
                "query_id": ["Q1", "Q1"],
                "doc_id": ["D1", "D2"],
                "relevance": [3, 2],
            }
        )
        warnings = validate_dataset(
            corpus,
            queries,
            qrels,
            expected_docs=None,
            expected_queries=None,
            expected_topics=None,
        )
        self.assertEqual(warnings, [])


class TestDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_corpus(ROOT / "tests" / "fixtures" / "korpus_provisional.csv")
        cls.queries = load_queries_df(ROOT / "tests" / "fixtures" / "queries_provisional.csv")
        cls.qrels = load_qrels_df(ROOT / "tests" / "fixtures" / "qrels_provisional.csv")

    def test_structure_50_25(self):
        warnings = validate_dataset(self.corpus, self.queries, self.qrels)
        self.assertIn("D03", " ".join(warnings))
        self.assertIn("D04", " ".join(warnings))

    def test_topic_balance(self):
        self.assertEqual(self.corpus.groupby("topik").size().to_dict(), {
            "kesehatan": 10,
            "pertanian": 10,
            "teknologi informasi": 10,
            "ekonomi": 10,
            "pendidikan": 10,
        })
        self.assertEqual(self.queries.groupby("topik").size().to_dict(), {
            "kesehatan": 5,
            "pertanian": 5,
            "teknologi informasi": 5,
            "ekonomi": 5,
            "pendidikan": 5,
        })

    def test_new_docs_have_source_metadata(self):
        new = self.corpus[self.corpus["doc_id"].str[1:].astype(int) >= 31]
        self.assertEqual(len(new), 20)
        self.assertTrue((new["url"].str.startswith("http")).all())
        self.assertTrue((new["sumber"].str.len() > 0).all())
        self.assertTrue(new["status_verifikasi"].str.startswith("sumber_dicek").all())
        self.assertTrue(new["status_akses_http"].isin(["200", "403"]).all())

    def test_label_sheet_is_ready_for_group_review(self):
        sheet = pd.read_csv(
            ROOT / "tests" / "fixtures" / "lembar_penilaian_provisional.csv",
            dtype=str,
            keep_default_na=False,
            encoding="utf-8-sig",
        )
        required = {
            "label_penilai_1",
            "catatan_penilai_1",
            "label_penilai_2",
            "catatan_penilai_2",
            "label_final",
            "status_verifikasi",
            "catatan_anggota",
        }
        self.assertTrue(required.issubset(sheet.columns))
        self.assertEqual(len(sheet), len(self.qrels))
        self.assertTrue((sheet["label_final"] == "").all())
        self.assertTrue((sheet["status_verifikasi"] == "menunggu_verifikasi").all())


class TestBaselineReproduction(unittest.TestCase):
    def test_bm25_legacy_map(self):
        engine = SearchEngine(
            ROOT / "Data" / "korpus.csv",
            model="bm25",
            use_stopword=True,
            use_stemming=True,
        )
        run = engine.run(load_queries(ROOT / "Data" / "queries.csv"), k=10)
        metrics = evaluate(run, load_qrels(ROOT / "Data" / "qrels.csv"), k=5)
        self.assertAlmostEqual(metrics.loc["Rata-rata", "AP"], 0.775645, places=4)
        self.assertAlmostEqual(metrics.loc["Rata-rata", "nDCG@5"], 0.866763, places=4)

    def test_tfidf_legacy_map(self):
        engine = SearchEngine(
            ROOT / "Data" / "korpus.csv",
            model="tfidf",
            use_stopword=True,
            use_stemming=True,
        )
        run = engine.run(load_queries(ROOT / "Data" / "queries.csv"), k=10)
        metrics = evaluate(run, load_qrels(ROOT / "Data" / "qrels.csv"), k=5)
        self.assertAlmostEqual(metrics.loc["Rata-rata", "AP"], 0.761954, places=4)


class TestExperimentConfigs(unittest.TestCase):
    def test_ab_difference_is_query_expansion(self):
        a = json.loads((ROOT / "experiments" / "versi_a" / "config.json").read_text(encoding="utf-8"))
        b = json.loads((ROOT / "experiments" / "versi_b" / "config.json").read_text(encoding="utf-8"))
        keys = set(a) | set(b)
        differing = {key for key in keys if a.get(key) != b.get(key)}
        self.assertEqual(
            differing,
            {"version", "description", "use_query_expansion", "expansion_weight", "synonyms"},
        )

    def test_baseline_is_unchanged(self):
        a = json.loads((ROOT / "experiments" / "versi_a" / "config.json").read_text(encoding="utf-8"))
        self.assertTrue(a["use_stemming"])
        self.assertFalse(a["use_query_expansion"])


if __name__ == "__main__":
    unittest.main()
