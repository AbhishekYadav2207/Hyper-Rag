# -*- coding: utf-8 -*-
"""
Verification script for Hyper-RAG multi-key provider configuration.
Verifies all required variables exist without exposing secrets.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import my_config


def test_configuration():
    print("Testing Hyper-RAG Configuration...")

    # Validate presence
    my_config.validate_config(exit_on_error=True)

    # Check OpenRouter configuration (ONLY LLM provider)
    assert my_config.OPENROUTER_BASE_URL, "OPENROUTER_BASE_URL is not set"
    assert my_config.OPENROUTER_MODEL == "nvidia/nemotron-3-ultra-550b-a55b:free", (
        f"OPENROUTER_MODEL expected 'nvidia/nemotron-3-ultra-550b-a55b:free', got '{my_config.OPENROUTER_MODEL}'"
    )
    assert len(my_config.OPENROUTER_API_KEYS) >= 1, "OPENROUTER_API_KEYS is empty"
    for idx, k in enumerate(my_config.OPENROUTER_API_KEYS):
        assert len(k) > 5, f"OpenRouter key {idx + 1} is empty or too short"
    print(
        f"  [OK] OpenRouter Primary LLM (ONLY LLM provider): model={my_config.OPENROUTER_MODEL}, "
        f"base_url={my_config.OPENROUTER_BASE_URL}, keys_configured={len(my_config.OPENROUTER_API_KEYS)}"
    )

    # Check Mistral embeddings configuration (EMBEDDINGS ONLY)
    assert my_config.EMB_BASE_URL, "EMB_BASE_URL is not set"
    assert my_config.EMB_MODEL == "mistral-embed", (
        f"EMB_MODEL expected 'mistral-embed', got '{my_config.EMB_MODEL}'"
    )
    assert my_config.EMB_DIM == 1024, f"EMB_DIM expected 1024, got {my_config.EMB_DIM}"
    assert len(my_config.EMB_API_KEYS) >= 1, "EMB_API_KEYS is empty"
    for idx, k in enumerate(my_config.EMB_API_KEYS):
        assert len(k) > 5, f"Embedding key {idx + 1} is empty or too short"
    print(
        f"  [OK] Mistral Embeddings (EMBEDDINGS ONLY): model={my_config.EMB_MODEL}, "
        f"dim={my_config.EMB_DIM}, base_url={my_config.EMB_BASE_URL}, keys_configured={len(my_config.EMB_API_KEYS)}"
    )

    assert my_config.ADAPTIVE_CORE_THRESHOLD == 60, f"ADAPTIVE_CORE_THRESHOLD expected 60, got {my_config.ADAPTIVE_CORE_THRESHOLD}"
    assert my_config.ADAPTIVE_RAG_MODE in ("adaptive", "core", "lite", "hyper", "hyper-lite"), f"Unexpected ADAPTIVE_RAG_MODE {my_config.ADAPTIVE_RAG_MODE}"
    assert my_config.ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD == 60, f"ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD expected 60, got {my_config.ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD}"
    assert my_config.ADAPTIVE_SHORT_QUERY_MAX_WORDS == 7, f"ADAPTIVE_SHORT_QUERY_MAX_WORDS expected 7, got {my_config.ADAPTIVE_SHORT_QUERY_MAX_WORDS}"
    assert my_config.ADAPTIVE_SHORT_QUERY_DENSITY_BONUS == 15.0, f"ADAPTIVE_SHORT_QUERY_DENSITY_BONUS expected 15.0, got {my_config.ADAPTIVE_SHORT_QUERY_DENSITY_BONUS}"
    assert my_config.ADAPTIVE_VALIDATION_THRESHOLD == 70.0, f"ADAPTIVE_VALIDATION_THRESHOLD expected 70.0, got {my_config.ADAPTIVE_VALIDATION_THRESHOLD}"
    assert my_config.ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT == 0.40, f"ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT expected 0.40, got {my_config.ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT}"
    assert my_config.ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT == 0.40, f"ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT expected 0.40, got {my_config.ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT}"
    assert my_config.ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT == 0.20, f"ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT expected 0.20, got {my_config.ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT}"
    print(
        f"  [OK] Adaptive Hyper-RAG: enabled={my_config.ADAPTIVE_RAG_ENABLED}, "
        f"mode={my_config.ADAPTIVE_RAG_MODE}, threshold={my_config.ADAPTIVE_CORE_THRESHOLD}, "
        f"sufficiency_enabled={my_config.ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED}, "
        f"sufficiency_threshold={my_config.ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD}, "
        f"short_query_max_words={my_config.ADAPTIVE_SHORT_QUERY_MAX_WORDS}, "
        f"short_query_density_bonus={my_config.ADAPTIVE_SHORT_QUERY_DENSITY_BONUS}, "
        f"validation_enabled={my_config.ADAPTIVE_VALIDATION_ENABLED}, "
        f"validation_threshold={my_config.ADAPTIVE_VALIDATION_THRESHOLD}, "
        f"log_decisions={my_config.ADAPTIVE_LOG_DECISIONS}"
    )

    print("\nAll configuration checks passed successfully! (No secrets were printed)")


if __name__ == "__main__":
    test_configuration()
