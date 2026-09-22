# -*- coding: utf-8 -*-
"""
Verification script for Hyper-RAG provider configuration.
Verifies all required variables exist without exposing secrets.
"""
import sys
import my_config

def test_configuration():
    print("Testing Hyper-RAG Configuration...")

    # Validate presence
    my_config.validate_config(exit_on_error=True)

    # Check OpenRouter configuration
    assert my_config.OPENROUTER_BASE_URL, "OPENROUTER_BASE_URL is not set"
    assert my_config.OPENROUTER_MODEL == "nvidia/nemotron-3-ultra-550b-a55b:free", (
        f"OPENROUTER_MODEL expected 'nvidia/nemotron-3-ultra-550b-a55b:free', got '{my_config.OPENROUTER_MODEL}'"
    )
    assert my_config.OPENROUTER_API_KEY and len(my_config.OPENROUTER_API_KEY) > 5, "OPENROUTER_API_KEY is empty or too short"
    print(f"  [OK] OpenRouter Primary LLM: model={my_config.OPENROUTER_MODEL}, base_url={my_config.OPENROUTER_BASE_URL}, api_key=configured")

    # Check Mistral fallback configuration
    assert my_config.MISTRAL_BASE_URL, "MISTRAL_BASE_URL is not set"
    assert my_config.MISTRAL_MODEL, "MISTRAL_MODEL is not set"
    assert my_config.MISTRAL_API_KEY and len(my_config.MISTRAL_API_KEY) > 5, "MISTRAL_API_KEY is empty or too short"
    print(f"  [OK] Mistral Fallback LLM: model={my_config.MISTRAL_MODEL}, base_url={my_config.MISTRAL_BASE_URL}, api_key=configured")

    # Check Mistral embeddings configuration
    assert my_config.EMB_BASE_URL, "EMB_BASE_URL is not set"
    assert my_config.EMB_MODEL == "mistral-embed", f"EMB_MODEL expected 'mistral-embed', got '{my_config.EMB_MODEL}'"
    assert my_config.EMB_DIM == 1024, f"EMB_DIM expected 1024, got {my_config.EMB_DIM}"
    assert my_config.EMB_API_KEY and len(my_config.EMB_API_KEY) > 5, "EMB_API_KEY is empty or too short"
    print(f"  [OK] Mistral Embeddings: model={my_config.EMB_MODEL}, dim={my_config.EMB_DIM}, base_url={my_config.EMB_BASE_URL}, api_key=configured")

    print("\nAll configuration checks passed successfully! (No secrets were printed)")

if __name__ == "__main__":
    test_configuration()
