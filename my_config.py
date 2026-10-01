# -*- coding: utf-8 -*-
"""
Hyper-RAG Configuration Module
Manages environment variables for OpenRouter LLM and Mistral Embeddings.
Supports multiple comma-separated API keys with automatic whitespace stripping.
Maintains backward compatibility with singular variables.
"""

import os
import sys
from typing import List
from dotenv import load_dotenv

# Load values from .env
load_dotenv()


def parse_api_keys(
    plural_var: str, singular_var: str, fallback_var: str = None
) -> List[str]:
    """
    Parse comma-separated API keys from environment variable.
    If plural_var exists and is non-empty, use it.
    Otherwise fall back to singular_var (and optional fallback_var).
    Strips whitespace and ignores empty entries.
    """
    raw_plural = os.getenv(plural_var)
    if raw_plural is not None and raw_plural.strip():
        keys = [k.strip() for k in raw_plural.split(",") if k.strip()]
        if keys:
            return keys

    raw_singular = os.getenv(singular_var)
    if raw_singular is not None and raw_singular.strip():
        keys = [k.strip() for k in raw_singular.split(",") if k.strip()]
        if keys:
            return keys

    if fallback_var:
        raw_fallback = os.getenv(fallback_var)
        if raw_fallback is not None and raw_fallback.strip():
            keys = [k.strip() for k in raw_fallback.split(",") if k.strip()]
            if keys:
                return keys

    return []


# ============================================================
# OPENROUTER - ONLY LLM PROVIDER
# ============================================================
OPENROUTER_BASE_URL: str = os.getenv(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)
OPENROUTER_MODEL: str = os.getenv(
    "OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"
)
OPENROUTER_API_KEYS: List[str] = parse_api_keys(
    "OPENROUTER_API_KEYS", "OPENROUTER_API_KEY"
)
OPENROUTER_API_KEY: str = (
    OPENROUTER_API_KEYS[0]
    if OPENROUTER_API_KEYS
    else os.getenv("OPENROUTER_API_KEY", "")
)

# ============================================================
# MISTRAL - EMBEDDINGS ONLY (NO LLM)
# ============================================================
EMB_BASE_URL: str = os.getenv("EMB_BASE_URL", "https://api.mistral.ai/v1")
EMB_MODEL: str = os.getenv("EMB_MODEL", "mistral-embed")
EMB_DIM: int = int(os.getenv("EMB_DIM", "1024"))
EMB_API_KEYS: List[str] = parse_api_keys(
    "EMB_API_KEYS", "EMB_API_KEY", fallback_var="MISTRAL_API_KEY"
)
EMB_API_KEY: str = (
    EMB_API_KEYS[0]
    if EMB_API_KEYS
    else os.getenv("EMB_API_KEY", os.getenv("MISTRAL_API_KEY", ""))
)

# ============================================================
# ADAPTIVE HYPER-RAG CONFIGURATION
# ============================================================
ADAPTIVE_RAG_ENABLED: bool = (
    os.getenv("ADAPTIVE_RAG_ENABLED", "true").strip().lower() in ("true", "1", "yes")
)
ADAPTIVE_RAG_MODE: str = os.getenv("ADAPTIVE_RAG_MODE", "adaptive").strip().lower()
ADAPTIVE_CORE_THRESHOLD: int = int(os.getenv("ADAPTIVE_CORE_THRESHOLD", "60"))
ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED: bool = (
    os.getenv("ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED", "true").strip().lower() in ("true", "1", "yes")
)
ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD: int = int(
    os.getenv("ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD", "60")
)
ADAPTIVE_LOG_DECISIONS: bool = (
    os.getenv("ADAPTIVE_LOG_DECISIONS", "true").strip().lower() in ("true", "1", "yes")
)
# Phase 2.1: Short-Query Semantic Density
ADAPTIVE_SHORT_QUERY_MAX_WORDS: int = int(
    os.getenv("ADAPTIVE_SHORT_QUERY_MAX_WORDS", "7")
)
ADAPTIVE_SHORT_QUERY_DENSITY_BONUS: float = float(
    os.getenv("ADAPTIVE_SHORT_QUERY_DENSITY_BONUS", "15.0")
)
# Phase 3: Response Validation
ADAPTIVE_VALIDATION_ENABLED: bool = (
    os.getenv("ADAPTIVE_VALIDATION_ENABLED", "true").strip().lower() in ("true", "1", "yes")
)
ADAPTIVE_VALIDATION_THRESHOLD: float = float(
    os.getenv("ADAPTIVE_VALIDATION_THRESHOLD", "70.0")
)
ADAPTIVE_VALIDATION_LOG_DECISIONS: bool = (
    os.getenv("ADAPTIVE_VALIDATION_LOG_DECISIONS", "true").strip().lower() in ("true", "1", "yes")
)
ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT: float = float(
    os.getenv("ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT", "0.40")
)
ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT: float = float(
    os.getenv("ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT", "0.40")
)
ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT: float = float(
    os.getenv("ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT", "0.20")
)

# ============================================================
# OLD CONFIGURATION BACKWARD COMPATIBILITY
# Mistral is NOT an LLM provider; these aliases prevent import breaks.
# ============================================================
MISTRAL_BASE_URL: str = os.getenv("MISTRAL_BASE_URL", EMB_BASE_URL)
MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-embed")
MISTRAL_API_KEY: str = EMB_API_KEY


def reload_config() -> None:
    """Reload configuration from environment variables."""
    global OPENROUTER_BASE_URL, OPENROUTER_MODEL, OPENROUTER_API_KEYS, OPENROUTER_API_KEY
    global EMB_BASE_URL, EMB_MODEL, EMB_DIM, EMB_API_KEYS, EMB_API_KEY
    global MISTRAL_BASE_URL, MISTRAL_MODEL, MISTRAL_API_KEY
    global ADAPTIVE_RAG_ENABLED, ADAPTIVE_RAG_MODE, ADAPTIVE_CORE_THRESHOLD
    global ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED, ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD
    global ADAPTIVE_LOG_DECISIONS
    global ADAPTIVE_SHORT_QUERY_MAX_WORDS, ADAPTIVE_SHORT_QUERY_DENSITY_BONUS
    global ADAPTIVE_VALIDATION_ENABLED, ADAPTIVE_VALIDATION_THRESHOLD, ADAPTIVE_VALIDATION_LOG_DECISIONS
    global ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT, ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT, ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT

    load_dotenv(override=True)
    OPENROUTER_BASE_URL = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )
    OPENROUTER_MODEL = os.getenv(
        "OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"
    )
    OPENROUTER_API_KEYS = parse_api_keys(
        "OPENROUTER_API_KEYS", "OPENROUTER_API_KEY"
    )
    OPENROUTER_API_KEY = (
        OPENROUTER_API_KEYS[0]
        if OPENROUTER_API_KEYS
        else os.getenv("OPENROUTER_API_KEY", "")
    )

    EMB_BASE_URL = os.getenv("EMB_BASE_URL", "https://api.mistral.ai/v1")
    EMB_MODEL = os.getenv("EMB_MODEL", "mistral-embed")
    EMB_DIM = int(os.getenv("EMB_DIM", "1024"))
    EMB_API_KEYS = parse_api_keys(
        "EMB_API_KEYS", "EMB_API_KEY", fallback_var="MISTRAL_API_KEY"
    )
    EMB_API_KEY = (
        EMB_API_KEYS[0]
        if EMB_API_KEYS
        else os.getenv("EMB_API_KEY", os.getenv("MISTRAL_API_KEY", ""))
    )

    MISTRAL_BASE_URL = os.getenv("MISTRAL_BASE_URL", EMB_BASE_URL)
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-embed")
    MISTRAL_API_KEY = EMB_API_KEY

    ADAPTIVE_RAG_ENABLED = (
        os.getenv("ADAPTIVE_RAG_ENABLED", "true").strip().lower() in ("true", "1", "yes")
    )
    ADAPTIVE_RAG_MODE = os.getenv("ADAPTIVE_RAG_MODE", "adaptive").strip().lower()
    ADAPTIVE_CORE_THRESHOLD = int(os.getenv("ADAPTIVE_CORE_THRESHOLD", "60"))
    ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED = (
        os.getenv("ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED", "true").strip().lower() in ("true", "1", "yes")
    )
    ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD = int(
        os.getenv("ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD", "60")
    )
    ADAPTIVE_LOG_DECISIONS = (
        os.getenv("ADAPTIVE_LOG_DECISIONS", "true").strip().lower() in ("true", "1", "yes")
    )
    ADAPTIVE_SHORT_QUERY_MAX_WORDS = int(
        os.getenv("ADAPTIVE_SHORT_QUERY_MAX_WORDS", "7")
    )
    ADAPTIVE_SHORT_QUERY_DENSITY_BONUS = float(
        os.getenv("ADAPTIVE_SHORT_QUERY_DENSITY_BONUS", "15.0")
    )
    ADAPTIVE_VALIDATION_ENABLED = (
        os.getenv("ADAPTIVE_VALIDATION_ENABLED", "true").strip().lower() in ("true", "1", "yes")
    )
    ADAPTIVE_VALIDATION_THRESHOLD = float(
        os.getenv("ADAPTIVE_VALIDATION_THRESHOLD", "70.0")
    )
    ADAPTIVE_VALIDATION_LOG_DECISIONS = (
        os.getenv("ADAPTIVE_VALIDATION_LOG_DECISIONS", "true").strip().lower() in ("true", "1", "yes")
    )
    ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT = float(
        os.getenv("ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT", "0.40")
    )
    ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT = float(
        os.getenv("ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT", "0.40")
    )
    ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT = float(
        os.getenv("ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT", "0.20")
    )


def validate_config(exit_on_error: bool = False) -> bool:
    """
    Validate that required configuration is present without printing secret values.
    Returns True if configuration is valid, or raises/exits if invalid.
    """
    missing = []
    if not OPENROUTER_API_KEYS:
        missing.append("OPENROUTER_API_KEYS (or OPENROUTER_API_KEY)")
    if not OPENROUTER_BASE_URL:
        missing.append("OPENROUTER_BASE_URL")
    if not OPENROUTER_MODEL:
        missing.append("OPENROUTER_MODEL")
    if not EMB_API_KEYS:
        missing.append("EMB_API_KEYS (or EMB_API_KEY)")
    if not EMB_BASE_URL:
        missing.append("EMB_BASE_URL")
    if not EMB_MODEL:
        missing.append("EMB_MODEL")
    if not EMB_DIM or EMB_DIM != 1024:
        missing.append("EMB_DIM (must be 1024)")
    if not (0 <= ADAPTIVE_CORE_THRESHOLD <= 100):
        missing.append("ADAPTIVE_CORE_THRESHOLD (must be between 0 and 100)")
    if not (0 <= ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD <= 100):
        missing.append("ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD (must be between 0 and 100)")
    if not (1 <= ADAPTIVE_SHORT_QUERY_MAX_WORDS <= 50):
        missing.append("ADAPTIVE_SHORT_QUERY_MAX_WORDS (must be between 1 and 50)")
    if not (0 <= ADAPTIVE_SHORT_QUERY_DENSITY_BONUS <= 100):
        missing.append("ADAPTIVE_SHORT_QUERY_DENSITY_BONUS (must be between 0 and 100)")
    if not (0 <= ADAPTIVE_VALIDATION_THRESHOLD <= 100):
        missing.append("ADAPTIVE_VALIDATION_THRESHOLD (must be between 0 and 100)")
    if ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT < 0:
        missing.append("ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT (must be >= 0)")
    if ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT < 0:
        missing.append("ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT (must be >= 0)")
    if ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT < 0:
        missing.append("ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT (must be >= 0)")
    if (
        ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT
        + ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT
        + ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT
    ) <= 0:
        missing.append("Validation weights sum must be greater than 0")

    if missing:
        msg = f"[Config Error] Missing or invalid configuration: {', '.join(missing)}. Please set them in .env"
        if exit_on_error:
            print(msg, file=sys.stderr)
            sys.exit(1)
        raise ValueError(msg)

    return True