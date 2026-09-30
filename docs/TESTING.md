# Hyper-RAG Testing Guide

This document describes the testing architecture, test suites, execution commands, and verified baselines across Hyper-RAG.

---

## 1. Test Architecture Overview

Hyper-RAG enforces a strict separation between **fast, hermetic local unit tests** and **live upstream diagnostics**:

```text
tests/
├── unit/                 # Fast, isolated unit & integration tests
│                         # - Pure local execution
│                         # - Zero external network calls
│                         # - Zero API token costs
│                         # - Verified baseline: 67 passed, 0 warnings
│
└── internal/             # Developer diagnostics
                          # - Live upstream provider tests
                          # - Requires active internet & API keys in .env
                          # - Verifies OpenRouter LLM & Mistral Embeddings
```

---

## 2. Fast Local Unit Tests (`tests/unit/`)

The unit test suite validates internal algorithms, data structures, and edge cases using hermetic mocks.

### Test Modules

| Module Path | Tests | Verified Status | Target Component |
|---|---|---|---|
| `tests/unit/test_adaptive_router.py` | 19 | PASS | Phase 1 complexity scoring, feature extraction, Phase 2.1 density bonus |
| `tests/unit/test_retrieval_sufficiency.py` | 10 | PASS | Phase 2 sufficiency scoring, penalty deductions, Lite $\rightarrow$ Core escalation |
| `tests/unit/test_response_validator.py` | 23 | PASS | Phase 3 completeness, evidence support, relevance, null context handling |
| `tests/unit/test_key_rotation.py` | 8 | PASS | KeyPool round-robin rotation, HTTP 429 backoff, 401 blacklisting |
| `tests/unit/test_language_guard.py` | 6 | PASS | Latin-script compliance and English-only output filtering |
| `tests/unit/test_config.py` | 1 | PASS | Environment variable parsing, weight sum validation, bounds checks |
| **Total Pytest Suite** | **67** | **67 PASS** | **0 failures, 0 warnings** |

### Running the Unit Suite
Because `pytest.ini` points directly to `tests/unit`, running pytest is as simple as:

```bash
# Run all unit tests
pytest

# Or via Python module execution
python -m pytest tests/unit -v
```

### Running Individual Test Modules
```bash
# Test Phase 1 & 2.1 router
python -m pytest tests/unit/test_adaptive_router.py -v

# Test Phase 2 sufficiency evaluator
python -m pytest tests/unit/test_retrieval_sufficiency.py -v

# Test Phase 3 response validator
python -m pytest tests/unit/test_response_validator.py -v

# Test API key rotation
python -m pytest tests/unit/test_key_rotation.py -v

# Test language compliance guard
python -m pytest tests/unit/test_language_guard.py -v

# Test configuration validation
python -m pytest tests/unit/test_config.py -v
```

---

## 3. Internal Diagnostics (`tests/internal/`)

These scripts make live calls to external upstream providers to verify API key validity, model availability, and network routing.

> [!CAUTION]
> Do not run internal diagnostics in automated CI/CD pipelines without valid API keys. They consume live API quota.

### 1. Test OpenRouter LLM Reasoning Endpoint
```bash
python tests/internal/test_openrouter.py
```
- **What it checks**: Sends a test prompt to `OPENROUTER_BASE_URL` with `OPENROUTER_MODEL`, confirming the model responds and your key is active.

### 2. Test Mistral Embeddings Endpoint
```bash
python tests/internal/test_embedding.py
```
- **What it checks**: Generates an embedding vector for a test string, verifying the returned tensor has dimension `1024`.

---

## 4. Web UI & Backend Verification

The Web UI verification suite validates both frontend views and backend REST APIs.

### Backend Endpoint Verification
With backend running on `http://127.0.0.1:8000`:
- `GET /`: Returns welcome message and system status.
- `GET /databases`: Confirms hypergraph database connectivity.
- `GET /settings`: Verifies model configuration and API key masking.
- `GET /hyperrag/status`: Verifies HyperRAG engine availability.

### Frontend Build Verification
Verify that the React frontend builds cleanly with Vite:
```bash
cd web-ui/frontend
npm run build
cd ../..
```
Verified build baseline: **Builds cleanly in under 1m 15s with Vite 6.4.3 without errors.**

---

## 5. Benchmark Evaluations

Hyper-RAG includes benchmark scripts for evaluating routing accuracy, latency, and threshold sensitivity:

```bash
# Run Pilot Benchmark (representative query archetypes)
python pilot_benchmark.py

# Run Full 39-Query Benchmark Suite
python run_full_benchmark.py
```

Outputs:
- `benchmark_results.json`: Execution record containing per-query latency, scores, modes, and decisions.
- `threshold_analysis.json`: Multi-threshold sensitivity comparison (thresholds 40, 50, 60, 70).

---

## 6. Full Pipeline Verification Run

The complete verification pipeline executes a full-spectrum validation pass:
- 32 automated pipeline checks
- 67 unit tests
- 6 Web UI views verified
- 4 core API endpoints checked
- 2 benchmark checks
- 3 security checks (secret masking, traversal prevention, CORS)

Verification results are saved under `logs/full_pipeline_YYYYMMDD_HHMMSS/` with a comprehensive `SUMMARY.md` and `TEST_MATRIX.md`.

### Verified Test Baseline
The latest verified baseline from `logs/full_pipeline_20260930_234500/SUMMARY.md` is:
```text
Pipeline Checks:        32 passed, 0 failed
Pytest Unit Tests:      67 passed, 0 failed, 0 warnings
API Checks:              4 passed, 0 failed
Web UI Checks:           6 passed, 0 failed
Benchmark Checks:        2 passed, 0 failed
Security Checks:         3 passed, 0 failed
Overall Warnings:        0
Overall Errors:          0
```
*(Note: These figures represent the verified baseline rather than an unconditional permanent guarantee).*
