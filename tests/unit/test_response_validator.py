# -*- coding: utf-8 -*-
"""
Unit tests for Phase 3: Response Validation in Adaptive Hyper-RAG.
Tests all required deterministic validation dimensions without live external API dependencies:
- Completeness
- Evidence support
- Relevance
- Comparison, causal, temporal, multi-hop, aggregation
- Unsupported claim detection
- Hard failure conditions & empty answer safety
- Phase 1 & 2 regression integration
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
from hyperrag.response_validator import (
    ResponseValidator,
    DeterministicResponseValidator,
    ValidationResult,
    ValidationWeights,
    ValidationMetrics,
    RequestedAspectExtractor,
)
from hyperrag.adaptive_router import QueryComplexityAnalyzer, AdaptiveRouter
from hyperrag.retrieval_sufficiency import RetrievalSufficiencyEvaluator
import my_config


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def validator():
    return ResponseValidator(threshold=70.0, log_decisions=False)


# =============================================================================
# TEST 1: Simple Complete
# =============================================================================

def test_1_simple_complete(validator):
    """
    Query: 'What is diabetes?'
    Answer directly defines and explains diabetes.
    Context provides definition.
    Expected: valid = True
    """
    query = "What is diabetes?"
    context = (
        "Diabetes mellitus is a chronic condition characterized by high levels of blood glucose. "
        "It occurs when the pancreas cannot produce enough insulin or when the body cannot effectively use insulin."
    )
    answer = (
        "Diabetes is a chronic metabolic disease characterized by elevated levels of blood glucose. "
        "It occurs because the pancreas does not produce enough insulin or the body cannot effectively use it."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert result.valid is True
    assert result.score >= 70.0
    assert result.completeness_score >= 80.0
    assert result.evidence_score >= 70.0
    assert result.relevance_score >= 80.0
    assert len(result.missing_aspects) == 0


# =============================================================================
# TEST 2: Multi-Aspect Incomplete
# =============================================================================

def test_2_multi_aspect_incomplete(validator):
    """
    Query: 'What are the causes, symptoms, treatment, and prevention of diabetes?'
    Answer contains causes and symptoms only; treatment and prevention are omitted.
    Expected: valid = False, missing_aspects contains treatment and prevention
    """
    query = "What are the causes, symptoms, treatment, and prevention of diabetes?"
    context = (
        "Diabetes causes include genetic susceptibility and lifestyle factors such as obesity. "
        "Symptoms include frequent urination, excessive thirst, and unexplained weight loss. "
        "Treatment involves insulin therapy and metformin. Prevention focuses on diet and exercise."
    )
    answer = (
        "The primary causes of diabetes include genetic susceptibility and lifestyle factors such as physical inactivity. "
        "Common symptoms of diabetes include frequent urination, excessive thirst, and unexplained weight loss."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert result.valid is False
    assert any("treatment" in ma for ma in result.missing_aspects)
    assert any("prevention" in ma for ma in result.missing_aspects)
    assert result.completeness_score < 70.0
    assert "INCOMPLETE" in result.failure_categories


# =============================================================================
# TEST 3: Multi-Aspect Complete
# =============================================================================

def test_3_multi_aspect_complete(validator):
    """
    All requested aspects (causes, symptoms, treatment, prevention) are addressed.
    Expected: valid = True
    """
    query = "What are the causes, symptoms, treatment, and prevention of diabetes?"
    context = (
        "Diabetes causes include genetic susceptibility and lifestyle factors. "
        "Symptoms include frequent urination and excessive thirst. "
        "Treatment involves insulin injections and medication like metformin. "
        "Prevention focuses on maintaining a healthy diet and active lifestyle."
    )
    answer = (
        "Causes: Diabetes is caused by genetic factors, autoimmune destruction of beta cells, and lifestyle habits. "
        "Symptoms: Patients experience symptoms such as frequent urination, persistent thirst, and fatigue. "
        "Treatment: Standard medical treatment involves insulin therapy, metformin, and glucose monitoring. "
        "Prevention: Disease prevention involves maintaining a healthy weight, regular exercise, and balanced diet."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert result.valid is True
    assert result.score >= 70.0
    assert len(result.missing_aspects) == 0
    assert result.completeness_score >= 80.0


# =============================================================================
# TEST 4: Comparison Incomplete
# =============================================================================

def test_4_comparison_incomplete(validator):
    """
    Query: 'Compare Ebenezer Scrooge and Mr. Fezziwig in terms of treatment of employees.'
    Answer discusses only Ebenezer Scrooge; Mr. Fezziwig is omitted.
    Expected: valid = False
    """
    query = "Compare Ebenezer Scrooge and Mr. Fezziwig in terms of treatment of employees."
    context = (
        "Ebenezer Scrooge was a harsh and miserly employer who underpaid his clerk Bob Cratchit. "
        "In contrast, Mr. Fezziwig was a generous and jovial master who hosted grand celebrations for his apprentices."
    )
    answer = (
        "Ebenezer Scrooge treated his clerk Bob Cratchit terribly, keeping the counting-house freezing cold "
        "and begrudging Bob even a single day off for Christmas with meager wages."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert result.valid is False
    assert "INCOMPLETE" in result.failure_categories
    assert any("Fezziwig" in ma or "entity" in ma or "Comparison" in r for ma in result.missing_aspects for r in result.reasons)


# =============================================================================
# TEST 5: Comparison Complete
# =============================================================================

def test_5_comparison_complete(validator):
    """
    Both entities and comparative dimensions compared with synthesis.
    Expected: valid = True
    """
    query = "Compare Ebenezer Scrooge and Mr. Fezziwig in terms of treatment of employees."
    context = (
        "Ebenezer Scrooge was a harsh and miserly employer who underpaid his clerk Bob Cratchit. "
        "In contrast, Mr. Fezziwig was a generous and jovial master who treated his employees with kindness and joy."
    )
    answer = (
        "When comparing Ebenezer Scrooge and Mr. Fezziwig, their treatment of employees differs dramatically. "
        "Scrooge acted as a callous, stingy employer who exploited Bob Cratchit with cold offices and minimal pay. "
        "In contrast, Mr. Fezziwig was a warm, generous master who viewed his apprentices as family, "
        "fostering happiness and celebrating Christmas with festive joy."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert result.valid is True
    assert result.score >= 70.0
    assert result.completeness_score >= 80.0
    assert len(result.missing_aspects) == 0


# =============================================================================
# TEST 6: Causal Incomplete
# =============================================================================

def test_6_causal_incomplete(validator):
    """
    Query: 'How did Marley's death cause Scrooge's isolation?'
    Answer mentions Marley's death and Scrooge's isolation, but does NOT explain the causal link.
    Expected: valid = False
    """
    query = "How did Marley's death cause Scrooge's isolation?"
    context = (
        "Jacob Marley died on Christmas Eve seven years ago. "
        "Scrooge lived alone in gloomy chambers and walked alone in London."
    )
    answer = (
        "Jacob Marley died seven years ago on Christmas Eve. "
        "Ebenezer Scrooge is an isolated man who lives alone in London."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert result.valid is False
    assert "INCOMPLETE" in result.failure_categories
    assert any("causal" in r.lower() for r in result.reasons)


# =============================================================================
# TEST 7: Causal Complete
# =============================================================================

def test_7_causal_complete(validator):
    """
    Query: 'How did Marley's death cause Scrooge's isolation?'
    Answer explains the explanatory causal mechanism.
    Expected: valid = True
    """
    query = "How did Marley's death cause Scrooge's isolation?"
    context = (
        "Marley was Scrooge's sole friend and business partner. His death removed the only remaining human bond Scrooge had, "
        "leading him to retreat completely inward into avarice and isolation."
    )
    answer = (
        "Marley's death caused Scrooge's deepened isolation because Jacob Marley was Scrooge's sole friend and confidant. "
        "As a result of losing his only human companion, Scrooge retreated into complete misanthropy, "
        "which led him to reject all social interactions and focus entirely on accumulating money."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert result.valid is True
    assert result.score >= 70.0
    assert result.completeness_score >= 75.0


# =============================================================================
# TEST 8: Temporal Incomplete
# =============================================================================

def test_8_temporal_incomplete(validator):
    """
    Query asks for progression over time.
    Answer provides only one static time point without chronological progression.
    Expected: valid = False
    """
    query = "How has Scrooge's relationship with Christmas evolved over time from his youth to old age?"
    context = (
        "In his youth, Scrooge enjoyed festive gatherings at Fezziwig's warehouse. Later, his obsession with wealth made him cold. "
        "In his old age, after the spirits' visits, he embraced Christmas with boundless charity."
    )
    answer = (
        "Scrooge is an old miser who despises Christmas and calls it a humbug."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert result.valid is False
    assert "INCOMPLETE" in result.failure_categories
    assert any("temporal" in r.lower() or "chronolog" in r.lower() for r in result.reasons)


# =============================================================================
# TEST 9: Multi-Hop Incomplete
# =============================================================================

def test_9_multi_hop_incomplete(validator):
    """
    Query: 'How does Scrooge's treatment of Bob Cratchit affect Tiny Tim through family circumstances?'
    Answer omits Tiny Tim or the intermediary pathway.
    Expected: valid = False
    """
    query = "How does Scrooge's treatment of Bob Cratchit affect Tiny Tim through family circumstances?"
    context = (
        "Scrooge pays Bob Cratchit only fifteen shillings a week. This low salary prevents the Cratchit family from affording "
        "proper nutrition and medical care for Tiny Tim, endangering the boy's life."
    )
    answer = (
        "Scrooge treats Bob Cratchit harshly and pays him very low wages at the counting house."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert result.valid is False
    assert "INCOMPLETE" in result.failure_categories


# =============================================================================
# TEST 10: Multi-Hop Complete
# =============================================================================

def test_10_multi_hop_complete(validator):
    """
    All nodes (Scrooge, Bob Cratchit, Tiny Tim) and relationship pathway explained.
    Expected: valid = True
    """
    query = "How does Scrooge's treatment of Bob Cratchit affect Tiny Tim through family circumstances?"
    context = (
        "Scrooge pays Bob Cratchit only fifteen shillings a week. This low salary prevents the Cratchit family from affording "
        "proper nutrition and medical care for Tiny Tim, directly jeopardizing the child's survival."
    )
    answer = (
        "Scrooge's miserly treatment of Bob Cratchit directly impacts Tiny Tim through the family's financial hardship. "
        "Because Scrooge pays Bob an meager wage of fifteen shillings, the Cratchit family cannot afford necessary medical treatment "
        "or nourishment, which in turn leads to Tiny Tim's failing health."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert result.valid is True
    assert result.score >= 70.0
    assert result.completeness_score >= 80.0


# =============================================================================
# TEST 11: Evidence Supported
# =============================================================================

def test_11_evidence_supported(validator):
    """
    Retrieved context directly supports the answer's factual assertions.
    Expected: high evidence_score, valid = True
    """
    query = "Who was Jacob Marley in relation to Scrooge?"
    context = (
        "Jacob Marley was Ebenezer Scrooge's business partner and only friend. "
        "Together they operated the firm Scrooge and Marley for many years until Marley died."
    )
    answer = (
        "Jacob Marley was the long-time business partner and sole friend of Ebenezer Scrooge. "
        "Together they ran their commercial firm Scrooge and Marley until Marley's death."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert result.valid is True
    assert result.evidence_score >= 80.0
    assert len(result.unsupported_claims) == 0


# =============================================================================
# TEST 12: Unsupported Claim
# =============================================================================

def test_12_unsupported_claim(validator):
    """
    Retrieved context supports main answer, but does NOT support one fabricated claim.
    Expected: unsupported_claims contains that specific claim, evidence score reduced.
    Does NOT label it globally false; labels it unsupported by retrieved evidence.
    """
    query = "Who was Jacob Marley in relation to Scrooge?"
    context = (
        "Jacob Marley was Ebenezer Scrooge's business partner. "
        "They worked together in London for decades."
    )
    answer = (
        "Jacob Marley was Ebenezer Scrooge's business partner in London. "
        "Scrooge moved to Paris in 1899 to open a second office."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert len(result.unsupported_claims) > 0
    assert any("Paris in 1899" in c or "1899" in c for c in result.unsupported_claims)
    assert result.evidence_score < 75.0


# =============================================================================
# TEST 13: Empty Answer
# =============================================================================

def test_13_empty_answer(validator):
    """
    Safely handle None, empty string, and whitespace-only answer without crashing.
    Expected: valid = False, score = 0, no exception
    """
    query = "What is diabetes?"

    for empty_val in [None, "", "   \n\t  "]:
        result = validator.validate(query, empty_val, retrieved_context="Some context")
        assert result.valid is False
        assert result.score == 0.0
        assert result.completeness_score == 0.0
        assert result.evidence_score == 0.0
        assert result.relevance_score == 0.0
        assert "EMPTY" in result.failure_categories
        assert "Empty answer" in result.reasons


# =============================================================================
# TEST 14: Irrelevant Answer
# =============================================================================

def test_14_irrelevant_answer(validator):
    """
    Query asks about quantum computing; answer discusses French cuisine.
    Expected: low relevance, valid = False, failure_categories contains IRRELEVANT
    """
    query = "How do quantum computers achieve superposition?"
    context = "Quantum computers use qubits to achieve quantum superposition and entanglement."
    answer = (
        "French cuisine is renowned worldwide for its croissants, baguettes, wine, and gourmet cheeses "
        "prepared with traditional culinary techniques in Paris."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert result.valid is False
    assert result.relevance_score < 30.0
    assert "IRRELEVANT" in result.failure_categories


# =============================================================================
# TEST 15: Legitimate Detail
# =============================================================================

def test_15_legitimate_detail(validator):
    """
    Answer contains useful explanatory context beyond the exact query keywords.
    Expected: not falsely penalized; valid = True
    """
    query = "Who is Bob Cratchit?"
    context = (
        "Bob Cratchit is Ebenezer Scrooge's clerk who works diligently in the cold counting-house. "
        "He is a loving family man, father to Tiny Tim, and remains cheerful despite immense financial poverty."
    )
    answer = (
        "Bob Cratchit is Ebenezer Scrooge's underpaid clerk at the counting-house. "
        "Despite working in poor conditions and facing poverty, he embodies warmth and devotion as a father to Tiny Tim "
        "and maintains a cheerful Christmas spirit."
    )
    result = validator.validate(query, answer, retrieved_context=context)

    assert result.valid is True
    assert result.score >= 75.0
    assert result.relevance_score >= 80.0


# =============================================================================
# TEST 16: Phase 1 Regression
# =============================================================================

def test_16_phase1_regression():
    """
    Verify that Phase 1 AdaptiveRouter continues to route correctly.
    """
    router = AdaptiveRouter()
    d1 = router.route("What is diabetes?")
    assert d1.mode == "lite"

    d2 = router.route("Compare Ebenezer Scrooge and Mr. Fezziwig in terms of treatment of employees.")
    assert d2.mode == "core"


# =============================================================================
# TEST 17: Phase 2 Regression
# =============================================================================

def test_17_phase2_regression():
    """
    Verify that Phase 2 RetrievalSufficiencyEvaluator continues to evaluate correctly.
    """
    evaluator = RetrievalSufficiencyEvaluator()
    empty_context = {"context": "", "entities": [], "hyperedges": [], "text_units": []}
    res = evaluator.evaluate("What is diabetes?", empty_context)
    assert res.sufficient is False
    assert res.score < 60


# =============================================================================
# TEST 18: Configuration Regression
# =============================================================================

def test_18_config_regression():
    """
    Verify that all configuration parameters and weights are valid and normalized.
    """
    assert my_config.validate_config() is True
    weights = ValidationWeights(0.40, 0.40, 0.20)
    w_c, w_e, w_r = weights.normalized()
    assert pytest.approx(w_c + w_e + w_r, 0.001) == 1.0
    assert pytest.approx(w_c, 0.001) == 0.40
    assert pytest.approx(w_e, 0.001) == 0.40
    assert pytest.approx(w_r, 0.001) == 0.20


# =============================================================================
# TEST 19: Serialization & Result Schema
# =============================================================================

def test_19_result_serialization(validator):
    """
    Verify ValidationResult serializes cleanly to dict matching expected schema.
    """
    res = validator.validate(
        query="What is diabetes?",
        answer="Diabetes is high blood sugar.",
        retrieved_context="Diabetes is characterized by high blood sugar."
    )
    d = res.to_dict()
    assert isinstance(d, dict)
    assert "valid" in d
    assert "score" in d
    assert "completeness_score" in d
    assert "evidence_score" in d
    assert "relevance_score" in d
    assert "missing_aspects" in d
    assert "unsupported_claims" in d
    assert "reasons" in d
    assert "metrics" in d
    assert "failure_categories" in d


# =============================================================================
# TEST 20: HyperRAG aquery Integration
# =============================================================================

def test_20_hyperrag_aquery_integration(monkeypatch, tmp_path):
    """
    End-to-end integration test verifying that HyperRAG.aquery attaches ValidationResult
    to rag.last_validation_result, param.validation_result, and json response.
    """
    import asyncio
    from hyperrag import HyperRAG, QueryParam
    from hyperrag.utils import EmbeddingFunc
    import numpy as np

    async def _run():
        async def mock_llm(prompt, system_prompt=None, history_messages=None, **kwargs):
            if "low_level_keywords" in prompt or "keywords_extraction" in prompt:
                return '{"low_level_keywords": ["diabetes"], "high_level_keywords": ["treatment"]}'
            return "Diabetes is a chronic disease characterized by elevated blood glucose levels."

        async def mock_embed(texts):
            return np.random.randn(len(texts), 1024).astype(np.float32)

        work_dir = tmp_path / "rag_cache"
        work_dir.mkdir(parents=True, exist_ok=True)
        rag = HyperRAG(
            working_dir=str(work_dir),
            llm_model_func=mock_llm,
            embedding_func=EmbeddingFunc(embedding_dim=1024, max_token_size=8192, func=mock_embed)
        )

        qp = QueryParam(mode="adaptive", return_type="json")
        resp = await rag.aquery("What is diabetes?", param=qp)

        assert isinstance(resp, dict)
        assert "validation" in resp
        assert isinstance(resp["validation"], dict)
        assert "valid" in resp["validation"]
        assert rag.last_validation_result is not None
        assert qp.validation_result is not None
        assert isinstance(rag.last_validation_result, ValidationResult)
        assert rag.last_validation_result.score >= 0.0

    asyncio.run(_run())


# =============================================================================
# TEST 21: HyperRAG astream_query Integration
# =============================================================================

def test_21_hyperrag_astream_query_integration(tmp_path):
    """
    End-to-end integration test verifying that HyperRAG.astream_query yields all tokens intact,
    and post-stream populates rag.last_validation_result with ValidationResult.
    """
    import asyncio
    from hyperrag import HyperRAG, QueryParam
    from hyperrag.utils import EmbeddingFunc
    import numpy as np

    async def _run():
        async def mock_llm(prompt, system_prompt=None, history_messages=None, **kwargs):
            if "low_level_keywords" in prompt or "keywords_extraction" in prompt:
                return '{"low_level_keywords": ["diabetes"], "high_level_keywords": ["treatment"]}'
            return "Diabetes is high blood sugar."

        async def mock_stream(prompt, system_prompt=None, history_messages=None, **kwargs):
            tokens = ["Diabetes ", "is ", "a ", "chronic ", "condition."]
            for t in tokens:
                yield t

        async def mock_embed(texts):
            return np.random.randn(len(texts), 1024).astype(np.float32)

        work_dir = tmp_path / "rag_stream_cache"
        work_dir.mkdir(parents=True, exist_ok=True)
        rag = HyperRAG(
            working_dir=str(work_dir),
            llm_model_func=mock_llm,
            llm_model_stream_func=mock_stream,
            embedding_func=EmbeddingFunc(embedding_dim=1024, max_token_size=8192, func=mock_embed)
        )

        qp = QueryParam(mode="adaptive")
        tokens_received = []
        async for tok in rag.astream_query("What is diabetes?", param=qp):
            tokens_received.append(tok)

        assert "".join(tokens_received) == "Diabetes is a chronic condition."
        assert rag.last_validation_result is not None
        assert qp.validation_result is not None
        assert isinstance(rag.last_validation_result, ValidationResult)

    asyncio.run(_run())


# =============================================================================
# TEST 22: Disabled Validation Setting
# =============================================================================

def test_22_disabled_validation(monkeypatch, tmp_path):
    """
    Verify that when ADAPTIVE_VALIDATION_ENABLED=False, the pipeline executes
    normally without performing validation, leaving last_validation_result as None.
    """
    import asyncio
    import hyperrag.hyperrag as hr_module
    monkeypatch.setattr(hr_module, "ADAPTIVE_VALIDATION_ENABLED", False)

    from hyperrag import HyperRAG, QueryParam
    from hyperrag.utils import EmbeddingFunc
    import numpy as np

    async def _run():
        async def mock_llm(prompt, system_prompt=None, history_messages=None, **kwargs):
            if "low_level_keywords" in prompt or "keywords_extraction" in prompt:
                return '{"low_level_keywords": ["diabetes"], "high_level_keywords": ["treatment"]}'
            return "Diabetes answer."

        async def mock_embed(texts):
            return np.random.randn(len(texts), 1024).astype(np.float32)

        work_dir = tmp_path / "rag_disabled_cache"
        work_dir.mkdir(parents=True, exist_ok=True)
        rag = HyperRAG(
            working_dir=str(work_dir),
            llm_model_func=mock_llm,
            embedding_func=EmbeddingFunc(embedding_dim=1024, max_token_size=8192, func=mock_embed)
        )

        qp = QueryParam(mode="adaptive", return_type="json")
        resp = await rag.aquery("What is diabetes?", param=qp)

        assert isinstance(resp, dict)
        assert "validation" not in resp
        assert rag.last_validation_result is None
        assert qp.validation_result is None

    asyncio.run(_run())
