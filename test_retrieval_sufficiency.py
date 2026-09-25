# -*- coding: utf-8 -*-
"""
Dedicated Test Suite for Phase 2: Retrieval Sufficiency + Automatic Lite -> Core Escalation
Testing Step 13 (Tests 1 to 10) & Step 14 (Performance Comparison on controlled mock contexts)
"""

import sys
import time
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

from hyperrag.adaptive_router import AdaptiveRouter, AdaptiveDecision
from hyperrag.retrieval_sufficiency import (
    RetrievalSufficiencyEvaluator,
    RetrievalSufficiency,
    RetrievalMetrics,
    SufficiencyWeights,
)
from hyperrag.base import QueryParam
from hyperrag.hyperrag import HyperRAG


class TestRetrievalSufficiencyUnit(unittest.TestCase):
    """Unit tests for RetrievalSufficiencyEvaluator metrics and scoring."""

    def setUp(self):
        self.evaluator = RetrievalSufficiencyEvaluator(threshold=60, log_evaluations=False)

    def test_empty_retrieval(self):
        """TEST 6 — Empty retrieval produces sufficient=False, score=0."""
        res = self.evaluator.evaluate("What is diabetes?", None)
        self.assertFalse(res.sufficient)
        self.assertEqual(res.score, 0)
        self.assertTrue(any("empty" in r.lower() for r in res.reasons))

        res2 = self.evaluator.evaluate("What is diabetes?", {"entities": [], "text_units": [], "hyperedges": []})
        self.assertFalse(res2.sufficient)
        self.assertEqual(res2.score, 0)

    def test_simple_query_sufficient_retrieval(self):
        """TEST 1 — Simple query with good entity and text chunks is sufficient."""
        query = "What is diabetes?"
        context = {
            "entities": [{"entity_name": "diabetes", "rank": 5}],
            "hyperedges": [],
            "text_units": [
                {"content": "Diabetes is a chronic metabolic disease characterized by elevated levels of blood glucose."},
                {"content": "There are two main types of diabetes: type 1 and type 2 diabetes affecting insulin production."}
            ]
        }
        res = self.evaluator.evaluate(query, context, features={"detected_entities": ["diabetes"], "multi_hop": False, "comparison": False})
        self.assertTrue(res.sufficient)
        self.assertGreaterEqual(res.score, 60)
        self.assertEqual(res.metrics["entity_count"], 1)
        self.assertEqual(res.metrics["text_unit_count"], 2)
        self.assertGreaterEqual(res.metrics["query_entity_coverage"], 0.9)

    def test_multihop_query_weak_relation_evidence(self):
        """TEST 4 — Multi-hop query with missing hyperedges/relations fails sufficiency."""
        query = "How does treatment A affect condition B through mechanism C?"
        context = {
            "entities": [
                {"entity_name": "treatment A", "rank": 2},
                {"entity_name": "condition B", "rank": 2},
                {"entity_name": "mechanism C", "rank": 2},
            ],
            "hyperedges": [],  # Crucial: NO relational hyperedges retrieved!
            "text_units": [
                {"content": "Treatment A is administered in patients."},
                {"content": "Condition B is a common clinical disorder."}
            ]
        }
        features = {
            "detected_entities": ["treatment A", "condition B", "mechanism C"],
            "multi_hop": True,
            "causal_reasoning": True,
            "comparison": False
        }
        res = self.evaluator.evaluate(query, context, features=features)
        self.assertFalse(res.sufficient)
        self.assertLess(res.score, 60)
        self.assertTrue(any("relationship evidence" in r.lower() for r in res.reasons))

    def test_multihop_query_strong_evidence(self):
        """TEST 5 — Multi-hop query with hyperedges and full entity coverage is sufficient."""
        query = "How does treatment A affect condition B through mechanism C?"
        context = {
            "entities": [
                {"entity_name": "treatment A", "rank": 3},
                {"entity_name": "condition B", "rank": 3},
                {"entity_name": "mechanism C", "rank": 3},
            ],
            "hyperedges": [
                {"src_tgt": "treatment A, mechanism C", "description": "Treatment A activates mechanism C.", "weight": 5, "rank": 2},
                {"src_tgt": "mechanism C, condition B", "description": "Mechanism C suppresses condition B.", "weight": 4, "rank": 2},
            ],
            "text_units": [
                {"content": "Treatment A specifically stimulates pathway mechanism C to downregulate condition B."},
                {"content": "Clinical trials demonstrate that condition B severity reduces through mechanism C when using treatment A."}
            ]
        }
        features = {
            "detected_entities": ["treatment A", "condition B", "mechanism C"],
            "multi_hop": True,
            "causal_reasoning": True,
            "comparison": False
        }
        res = self.evaluator.evaluate(query, context, features=features)
        self.assertTrue(res.sufficient)
        self.assertGreaterEqual(res.score, 60)
        self.assertTrue(res.metrics["has_relational_evidence"])

    def test_duplicate_heavy_retrieval(self):
        """TEST 7 — Duplicate-heavy retrieval suffers diversity penalty and produces low sufficiency."""
        query = "What are the complications of diabetes?"
        # Three identical chunks
        chunk = "Diabetes can cause serious complications over time."
        context = {
            "entities": [{"entity_name": "diabetes", "rank": 1}],
            "hyperedges": [],
            "text_units": [
                {"content": chunk},
                {"content": chunk},
                {"content": chunk},
            ]
        }
        res = self.evaluator.evaluate(query, context, features={"detected_entities": ["diabetes", "complications"], "multi_hop": False})
        self.assertGreaterEqual(res.metrics["duplicate_ratio"], 0.6)
        self.assertTrue(any("duplicate" in r.lower() for r in res.reasons))


class TestAdaptiveEscalationPipeline(unittest.IsolatedAsyncioTestCase):
    """Integration tests for HyperRAG Lite -> Core escalation execution."""

    def setUp(self):
        self.asdict_patcher = patch("hyperrag.hyperrag.asdict", return_value={"llm_model_func": AsyncMock()})
        self.asdict_patcher.start()
        self.rag = HyperRAG.__new__(HyperRAG)
        self.rag.working_dir = "./test_cache"
        self.rag.adaptive_router = AdaptiveRouter(core_threshold=60, log_decisions=False)
        self.rag.sufficiency_evaluator = RetrievalSufficiencyEvaluator(threshold=60, log_evaluations=False)
        self.rag.last_adaptive_decision = None
        self.rag._query_done = AsyncMock()
        self.rag.chunk_entity_relation_hypergraph = MagicMock()
        self.rag.entities_vdb = MagicMock()
        self.rag.relationships_vdb = MagicMock()
        self.rag.text_chunks = MagicMock()
        self.rag.llm_response_cache = None

    def tearDown(self):
        self.asdict_patcher.stop()

    @patch("hyperrag.hyperrag.hyper_retrieve_lite")
    @patch("hyperrag.hyperrag.hyper_query_lite_reasoning")
    async def test_01_simple_query_sufficient_lite_remains_lite(self, mock_reasoning, mock_retrieve):
        """TEST 1 — Simple query with sufficient Lite retrieval stays Lite (no escalation)."""
        mock_retrieve.return_value = (
            {
                "entities": [{"entity_name": "diabetes", "rank": 5}],
                "hyperedges": [],
                "text_units": [{"content": "Diabetes is a metabolic disorder characterized by high blood sugar."}],
            },
            "diabetes",
        )
        mock_reasoning.return_value = "Diabetes answer"

        q = "What is diabetes?"
        res = await self.rag.aquery(q, param=QueryParam(mode="adaptive"))

        self.assertEqual(res, "Diabetes answer")
        dec = self.rag.last_adaptive_decision
        self.assertIsNotNone(dec)
        self.assertEqual(dec.initial_mode, "lite")
        self.assertEqual(dec.final_mode, "lite")
        self.assertFalse(dec.escalated)
        self.assertTrue(dec.retrieval_sufficient)
        mock_retrieve.assert_awaited_once()
        mock_reasoning.assert_awaited_once()

    @patch("hyperrag.hyperrag.hyper_retrieve_lite")
    @patch("hyperrag.hyperrag.hyper_query")
    @patch("hyperrag.hyperrag.hyper_query_lite_reasoning")
    async def test_02_simple_looking_insufficient_retrieval_escalates(self, mock_lite_reasoning, mock_core_query, mock_retrieve):
        """TEST 2 — Simple-looking query with empty/insufficient retrieval escalates Lite -> Core."""
        # Lite retrieval yields 0 text units (e.g. unknown term in local index)
        mock_retrieve.return_value = (None, "")
        mock_core_query.return_value = "Core escalated answer"

        q = "What is condition_unknown_x?"
        res = await self.rag.aquery(q, param=QueryParam(mode="adaptive"))

        self.assertEqual(res, "Core escalated answer")
        dec = self.rag.last_adaptive_decision
        self.assertIsNotNone(dec)
        self.assertEqual(dec.initial_mode, "lite")
        self.assertEqual(dec.final_mode, "core")
        self.assertTrue(dec.escalated)
        self.assertFalse(dec.retrieval_sufficient)
        # Ensure Lite reasoning was NOT called (avoiding two complete generations)
        mock_lite_reasoning.assert_not_called()
        # Core query was called
        mock_core_query.assert_awaited_once()

    @patch("hyperrag.hyperrag.hyper_retrieve_lite")
    @patch("hyperrag.hyperrag.hyper_query")
    async def test_03_complex_query_runs_core_directly(self, mock_core_query, mock_retrieve):
        """TEST 3 — Complex query (score >= 60) runs Core directly without Lite retrieval."""
        mock_core_query.return_value = "Core direct answer"

        q = "Compare diabetes and hypertension in terms of causes, symptoms, and treatment."
        res = await self.rag.aquery(q, param=QueryParam(mode="adaptive"))

        self.assertEqual(res, "Core direct answer")
        dec = self.rag.last_adaptive_decision
        self.assertIsNotNone(dec)
        self.assertEqual(dec.initial_mode, "core")
        self.assertEqual(dec.final_mode, "core")
        self.assertFalse(dec.escalated)
        # Lite retrieval must NOT be executed for initially Core queries
        mock_retrieve.assert_not_called()
        mock_core_query.assert_awaited_once()

    @patch("hyperrag.hyperrag.hyper_query_lite")
    async def test_08_manual_mode_lite_preserves_direct_execution(self, mock_lite_query):
        """TEST 8 — Manual Lite (mode='lite') bypasses adaptive routing & escalation."""
        mock_lite_query.return_value = "Direct Lite answer"
        q = "Compare diabetes and hypertension in terms of causes and treatment."
        res = await self.rag.aquery(q, param=QueryParam(mode="lite"))

        self.assertEqual(res, "Direct Lite answer")
        self.assertIsNone(self.rag.last_adaptive_decision)
        mock_lite_query.assert_awaited_once()

    @patch("hyperrag.hyperrag.hyper_query")
    async def test_09_manual_mode_core_preserves_direct_execution(self, mock_core_query):
        """TEST 9 — Manual Core (mode='core') always runs Core directly."""
        mock_core_query.return_value = "Direct Core answer"
        q = "What is diabetes?"
        res = await self.rag.aquery(q, param=QueryParam(mode="core"))

        self.assertEqual(res, "Direct Core answer")
        self.assertIsNone(self.rag.last_adaptive_decision)
        mock_core_query.assert_awaited_once()


def run_step14_performance_benchmark():
    """
    STEP 14 — Performance comparison across:
    1. Fixed Lite
    2. Fixed Core
    3. Adaptive Phase 1
    4. Adaptive Phase 2 (with Sufficiency & Escalation)
    """
    print("\n" + "=" * 80)
    print("STEP 14 — PERFORMANCE BENCHMARK & COMPARISON")
    print("=" * 80)

    # Synthetic test corpus representing 3 query archetypes:
    # 1. Simple factual with good local evidence
    # 2. Simple-looking query with missing evidence (needs escalation in Phase 2)
    # 3. High-complexity comparison query
    test_cases = [
        {
            "id": "Q1 (Simple Factual)",
            "query": "What is diabetes?",
            "expected_lite_evidence": {
                "entities": [{"entity_name": "diabetes"}],
                "hyperedges": [],
                "text_units": [{"content": "Diabetes is a metabolic disease characterized by hyperglycemia."}]
            },
        },
        {
            "id": "Q2 (Deficient Lite)",
            "query": "What is rare_syndrome_z?",
            "expected_lite_evidence": {
                "entities": [],
                "hyperedges": [],
                "text_units": []
            },
        },
        {
            "id": "Q3 (Complex Comparison)",
            "query": "Compare diabetes and hypertension in terms of causes, symptoms, and treatment.",
            "expected_lite_evidence": {
                "entities": [{"entity_name": "diabetes"}, {"entity_name": "hypertension"}],
                "hyperedges": [{"src_tgt": "diabetes, hypertension"}],
                "text_units": [{"content": "Comparison data."}]
            },
        },
    ]

    router = AdaptiveRouter(core_threshold=60, log_decisions=False)
    evaluator = RetrievalSufficiencyEvaluator(threshold=60, log_evaluations=False)

    print(f"{'Query ID':<24} | {'Mode Strategy':<18} | {'Initial':<7} | {'Final':<7} | {'Escalated':<9} | {'CompScore':<9} | {'SuffScore':<9}")
    print("-" * 105)

    for tc in test_cases:
        qid = tc["id"]
        q = tc["query"]
        evidence = tc["expected_lite_evidence"]

        # 1. Fixed Lite
        print(f"{qid:<24} | {'Fixed Lite':<18} | {'lite':<7} | {'lite':<7} | {'N/A':<9} | {'N/A':<9} | {'N/A':<9}")

        # 2. Fixed Core
        print(f"{qid:<24} | {'Fixed Core':<18} | {'core':<7} | {'core':<7} | {'N/A':<9} | {'N/A':<9} | {'N/A':<9}")

        # 3. Adaptive Phase 1
        d_p1 = router.route(q)
        print(f"{qid:<24} | {'Adaptive Phase 1':<18} | {d_p1.mode:<7} | {d_p1.mode:<7} | {'False':<9} | {d_p1.score:<9} | {'N/A':<9}")

        # 4. Adaptive Phase 2
        d_p2 = router.route(q)
        initial_mode = d_p2.mode
        if initial_mode == "lite":
            suff = evaluator.evaluate(q, evidence, features=d_p2.features, complexity_score=d_p2.score)
            if not suff.sufficient:
                final_mode = "core"
                escalated = True
            else:
                final_mode = "lite"
                escalated = False
            suff_score = str(suff.score)
        else:
            final_mode = "core"
            escalated = False
            suff_score = "Skipped"

        print(f"{qid:<24} | {'Adaptive Phase 2':<18} | {initial_mode:<7} | {final_mode:<7} | {str(escalated):<9} | {d_p2.score:<9} | {suff_score:<9}")
        print("-" * 105)


if __name__ == "__main__":
    if "--benchmark" in sys.argv:
        run_step14_performance_benchmark()
    else:
        unittest.main(verbosity=2)
