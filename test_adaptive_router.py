# -*- coding: utf-8 -*-
"""
Dedicated Test Suite for Adaptive Hyper-RAG Router
Covering STEP 13 (Tests 1 to 12) & STEP 14 (Evaluation Output)
"""

import sys
import unittest
from unittest.mock import MagicMock

from hyperrag.adaptive_router import (
    AdaptiveRouter,
    AdaptiveDecision,
    QueryFeatures,
    ComplexityWeights,
    QueryComplexityAnalyzer,
    QueryFeatureExtractor,
    HeuristicComplexityScorer,
    ComplexityScorer,
    BaseComplexityScorer,
)
from hyperrag.base import QueryParam
from hyperrag.hyperrag import HyperRAG


class TestAdaptiveRouterStep13(unittest.TestCase):
    """
    Dedicated unit test suite covering all 12 test specifications from STEP 13.
    """

    def setUp(self):
        self.router = AdaptiveRouter(core_threshold=60, log_decisions=False)
        self.rag = HyperRAG.__new__(HyperRAG)
        self.rag.working_dir = "./test_cache"
        self.rag.adaptive_router = self.router
        self.rag.last_adaptive_decision = None

    def test_01_simple_factual_query(self):
        """TEST 1 — SIMPLE FACTUAL QUERY ("What is diabetes?" -> Lite)"""
        q = "What is diabetes?"
        decision = self.router.route(q)
        self.assertEqual(decision.mode, "lite")
        self.assertLess(decision.score, 30)
        self.assertIn("Simple single-entity factual query", decision.reason)

    def test_02_simple_definition(self):
        """TEST 2 — SIMPLE DEFINITION ("What is a neural network?" -> Lite)"""
        q = "What is a neural network?"
        decision = self.router.route(q)
        self.assertEqual(decision.mode, "lite")
        self.assertLess(decision.score, 30)

    def test_03_multi_aspect_query(self):
        """
        TEST 3 — MULTI-ASPECT QUERY
        "What are the causes, symptoms, treatment, and prevention of diabetes?"
        Expected: Higher score than TEST 1, Likely Core
        """
        q1 = "What is diabetes?"
        q3 = "What are the causes, symptoms, treatment, and prevention of diabetes?"
        d1 = self.router.route(q1)
        d3 = self.router.route(q3)
        self.assertGreater(d3.score, d1.score)
        self.assertGreaterEqual(d3.score, 60)
        self.assertEqual(d3.mode, "core")

    def test_04_comparison(self):
        """
        TEST 4 — COMPARISON
        "Compare diabetes and hypertension in terms of causes, symptoms, and treatment."
        Expected: Core
        """
        q = "Compare diabetes and hypertension in terms of causes, symptoms, and treatment."
        decision = self.router.route(q)
        self.assertEqual(decision.mode, "core")
        self.assertGreaterEqual(decision.score, 60)
        self.assertTrue(decision.features["comparison"])

    def test_05_causal_query(self):
        """
        TEST 5 — CAUSAL QUERY
        "How does diabetes contribute to kidney disease?"
        Expected: Higher complexity due to relationship/causal reasoning
        """
        q1 = "What is diabetes?"
        q5 = "How does diabetes contribute to kidney disease?"
        d1 = self.router.route(q1)
        d5 = self.router.route(q5)
        self.assertGreater(d5.score, d1.score)
        self.assertTrue(d5.features["causal_reasoning"])
        self.assertTrue(any("causal" in r.lower() for r in d5.reasons))

    def test_06_temporal_query(self):
        """
        TEST 6 — TEMPORAL QUERY
        "How has the disease progressed over the last decade?"
        Expected: Higher complexity due to temporal reasoning
        """
        q1 = "What is diabetes?"
        q6 = "How has the disease progressed over the last decade?"
        d1 = self.router.route(q1)
        d6 = self.router.route(q6)
        self.assertGreater(d6.score, d1.score)
        self.assertTrue(d6.features["temporal_reasoning"])
        self.assertTrue(any("temporal" in r.lower() for r in d6.reasons))

    def test_07_multi_hop_query(self):
        """
        TEST 7 — MULTI-HOP QUERY
        "How does treatment A affect condition B through mechanism C?"
        Expected: Core or significantly elevated score
        """
        q1 = "What is diabetes?"
        q7 = "How does treatment A affect condition B through mechanism C?"
        d1 = self.router.route(q1)
        d7 = self.router.route(q7)
        self.assertGreater(d7.score, d1.score)
        # Significantly elevated score (near or above threshold, compared to basic queries ~6)
        self.assertGreaterEqual(d7.score, 45)
        self.assertTrue(d7.features["multi_hop"])

    def test_08_long_but_simple_query(self):
        """
        TEST 8 — LONG BUT SIMPLE QUERY
        Verify that long wording alone does not automatically force Core.
        """
        q = (
            "Could you please be kind enough to provide me with a basic, straightforward "
            "definition and some general introductory background regarding what people commonly "
            "mean by the single medical condition known simply as diabetes?"
        )
        decision = self.router.route(q)
        self.assertEqual(decision.mode, "lite")
        self.assertLess(decision.score, 60)

    def test_09_short_but_complex_query(self):
        """
        TEST 9 — SHORT BUT COMPLEX QUERY
        "Why does A cause B?"
        Verify that a short query can still receive a high complexity score because of reasoning type.
        """
        q_simple_short = "What is A?"
        q_complex_short = "Why does A cause B?"
        d_simple = self.router.route(q_simple_short)
        d_complex = self.router.route(q_complex_short)
        # Verify complexity score is significantly higher due to causal relationship reasoning
        self.assertGreater(d_complex.score, d_simple.score)
        self.assertTrue(d_complex.features["causal_reasoning"])

    def test_10_manual_mode_lite(self):
        """
        TEST 10 — MANUAL MODE
        mode="lite" -> Expected: Always Lite regardless of complexity.
        """
        complex_q = (
            "Compare diabetes and hypertension and explain how they affect kidney disease over time. "
            "Provide an in-depth analysis of the underlying mechanisms and resulting consequences."
        )
        mode, decision = self.rag._resolve_query_mode(complex_q, QueryParam(mode="lite"))
        self.assertEqual(mode, "hyper-lite")
        self.assertIsNone(decision)

    def test_11_manual_mode_core(self):
        """
        TEST 11 — MANUAL MODE
        mode="core" -> Expected: Always Core regardless of simplicity.
        """
        simple_q = "What is diabetes?"
        mode, decision = self.rag._resolve_query_mode(simple_q, QueryParam(mode="core"))
        self.assertEqual(mode, "hyper")
        self.assertIsNone(decision)

    def test_12_adaptive_mode(self):
        """
        TEST 12 — ADAPTIVE MODE
        mode="adaptive" -> Expected: Router chooses automatically.
        """
        simple_q = "What is diabetes?"
        mode_simple, dec_simple = self.rag._resolve_query_mode(simple_q, QueryParam(mode="adaptive"))
        self.assertEqual(mode_simple, "hyper-lite")
        self.assertIsNotNone(dec_simple)
        self.assertEqual(dec_simple.mode, "lite")

        complex_q = "Compare diabetes and hypertension in terms of causes, symptoms, and treatment."
        mode_complex, dec_complex = self.rag._resolve_query_mode(complex_q, QueryParam(mode="adaptive"))
        self.assertEqual(mode_complex, "hyper")
        self.assertIsNotNone(dec_complex)
        self.assertEqual(dec_complex.mode, "core")


class TestShortQuerySemanticDensityPhase21(unittest.TestCase):
    """
    Phase 2.1: Short-Query Semantic-Density Refinement Unit Tests (Step 12: Tests A to F).
    """

    def setUp(self):
        self.router = AdaptiveRouter(core_threshold=60, log_decisions=False)

    def test_a_short_factual_query(self):
        """
        TEST A — Short factual query ("What is Scrooge?")
        Verify:
        - short query = true
        - semantic density = false
        - mode = Lite
        - no erroneous density bonus
        """
        q = "What is Scrooge?"
        d = self.router.route(q)
        self.assertTrue(d.features["is_short_query"])
        self.assertFalse(d.features["short_query_semantic_density"])
        self.assertEqual(d.mode, "lite")
        self.assertEqual(d.short_query_density_bonus, 0.0)
        self.assertNotIn("short-query semantic density detected", d.reasons)
        self.assertLess(d.score, 30)

    def test_b_short_comparison(self):
        """
        TEST B — Short comparison ("Compare Fred vs Scrooge")
        Verify:
        - short query = true
        - comparison = true
        - semantic density = true
        - density bonus applied (+15)
        - final score increases appropriately
        - mode = Core when score crosses threshold 60
        """
        q = "Compare Fred vs Scrooge"
        d = self.router.route(q)
        self.assertTrue(d.features["is_short_query"])
        self.assertTrue(d.features["comparison"])
        self.assertTrue(d.features["short_query_semantic_density"])
        self.assertEqual(d.short_query_density_bonus, 15.0)
        self.assertEqual(d.base_score, 51)
        self.assertEqual(d.score, 66)
        self.assertGreaterEqual(d.score, 60)
        self.assertEqual(d.mode, "core")
        self.assertIn("short-query semantic density detected", d.reasons)

    def test_c_short_causal(self):
        """
        TEST C — Short causal ("Why does greed cause suffering?")
        Verify:
        - causal feature detected
        - semantic density detected
        - density bonus applied (+15)
        - final score behaves as expected
        """
        q = "Why does greed cause suffering?"
        d = self.router.route(q)
        self.assertTrue(d.features["is_short_query"])
        self.assertTrue(d.features["causal_reasoning"])
        self.assertTrue(d.features["short_query_semantic_density"])
        self.assertEqual(d.short_query_density_bonus, 15.0)
        self.assertEqual(d.base_score, 27)
        self.assertEqual(d.score, 42)
        self.assertIn("short-query semantic density detected", d.reasons)
        self.assertEqual(d.mode, "lite")

        # Causal query crossing threshold with 3 entities + multi-hop
        q_core = "Why did Marley warn Scrooge?"
        d_core = self.router.route(q_core)
        self.assertTrue(d_core.features["causal_reasoning"])
        self.assertTrue(d_core.features["short_query_semantic_density"])
        self.assertEqual(d_core.short_query_density_bonus, 15.0)
        self.assertEqual(d_core.base_score, 47)
        self.assertEqual(d_core.score, 62)
        self.assertEqual(d_core.mode, "core")

    def test_d_short_multihop_relationship(self):
        """
        TEST D — Short multi-hop / relationship ("How does A affect B?")
        Verify the actual behavior produced by the configured feature policy.
        """
        q = "How does A affect B?"
        d = self.router.route(q)
        self.assertTrue(d.features["is_short_query"])
        self.assertTrue(d.features["causal_reasoning"])
        self.assertTrue(d.features["multi_hop"])
        self.assertTrue(d.features["short_query_semantic_density"])
        self.assertEqual(d.short_query_density_bonus, 15.0)
        self.assertEqual(d.base_score, 47)
        self.assertEqual(d.score, 62)
        self.assertEqual(d.mode, "core")
        self.assertIn("short-query semantic density detected", d.reasons)

    def test_e_long_simple_query(self):
        """
        TEST E — Long simple query
        Verify that the new rule does NOT activate for long queries.
        """
        q = (
            "Could you please be kind enough to provide me with a basic, straightforward "
            "definition and some general introductory background regarding what people commonly "
            "mean by the single medical condition known simply as diabetes?"
        )
        d = self.router.route(q)
        self.assertFalse(d.features["is_short_query"])
        self.assertFalse(d.features["short_query_semantic_density"])
        self.assertEqual(d.short_query_density_bonus, 0.0)
        self.assertEqual(d.mode, "lite")
        self.assertNotIn("short-query semantic density detected", d.reasons)

    def test_f_short_factual_baseline_queries(self):
        """
        TEST F — Additional short factual baseline queries remain Lite without density bonus.
        """
        factual_queries = [
            "Who is Marley?",
            "What is a counting-house?",
            "Who was Tiny Tim?",
        ]
        for q in factual_queries:
            d = self.router.route(q)
            self.assertTrue(d.features["is_short_query"], f"Failed for {q}")
            self.assertFalse(d.features["short_query_semantic_density"], f"Failed for {q}")
            self.assertEqual(d.short_query_density_bonus, 0.0, f"Failed for {q}")
            self.assertEqual(d.mode, "lite", f"Failed for {q}")
            self.assertLess(d.score, 30, f"Failed for {q}")


class TestEvaluationOutputStep14(unittest.TestCase):
    """
    Test Step 14 evaluation output formatting for inspection.
    """

    def test_inspect_query_format(self):
        router = AdaptiveRouter(core_threshold=60, log_decisions=False)
        output = router.inspect_query("Compare A and B in terms of causes and effects.")
        self.assertIn("Query:", output)
        self.assertIn("Score:", output)
        self.assertIn("Detected:", output)
        self.assertIn("Selected:", output)
        self.assertIn("Reasons:", output)
        self.assertIn("CORE", output)


def print_step14_evaluation():
    """Print evaluation format for all test queries as specified in Step 14."""
    router = AdaptiveRouter(core_threshold=60, log_decisions=False)
    test_queries = [
        "What is diabetes?",
        "What is a neural network?",
        "What are the causes, symptoms, treatment, and prevention of diabetes?",
        "Compare diabetes and hypertension in terms of causes, symptoms, and treatment.",
        "How does diabetes contribute to kidney disease?",
        "How has the disease progressed over the last decade?",
        "How does treatment A affect condition B through mechanism C?",
        "Could you please provide a basic factual overview explaining what is diabetes?",
        "Why does A cause B?",
    ]

    print("\n" + "=" * 60)
    print("STEP 14 — ADAPTIVE ROUTER EVALUATION OUTPUT")
    print("=" * 60)
    for q in test_queries:
        print(router.inspect_query(q))
        print("-" * 60)


if __name__ == "__main__":
    if "--eval" in sys.argv:
        print_step14_evaluation()
    else:
        unittest.main(verbosity=2)
