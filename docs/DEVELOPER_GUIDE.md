# Hyper-RAG Developer Guide

This guide is designed for contributors and developers extending, maintaining, or customizing Hyper-RAG.

---

## 1. Codebase Architecture & File Mapping

```text
hyperrag/
├── adaptive_router.py        # Phase 1: Query complexity feature extraction & scoring
├── retrieval_sufficiency.py  # Phase 2: Post-retrieval evidence scoring & escalation logic
├── response_validator.py     # Phase 3: Post-reasoning deterministic answer validation
├── language_guard.py         # Latin-script compliance filter (English-only policy)
├── key_pool.py               # Thread-safe API key pool, rotation, and backoff manager
├── llm.py                    # External provider connectors (OpenRouter & Mistral)
├── hyperrag.py               # HyperRAG engine orchestrator, query dispatch & escalation
├── operate.py                # Retrieval execution, graph diffusion, and prompt synthesis
├── base.py                   # QueryParam, storage protocols, and core dataclasses
└── utils.py                  # EmbeddingFunc, logging configuration, hashing utilities
```

---

## 2. Core Extension Points

### 2.1 Extending Adaptive Query Routing (`hyperrag/adaptive_router.py`)
To add a new linguistic feature to Phase 1:
1. Open [`QueryFeatures`](../hyperrag/adaptive_router.py). Add the new boolean or integer field to the dataclass.
2. In `QueryFeatureExtractor.extract()`, add the regular expression or token pattern detecting the feature.
3. In `ComplexityWeights`, add a corresponding weight parameter with a default point allocation.
4. In `HeuristicComplexityScorer.score()`, add the point contribution to the score accumulation.
5. In `tests/unit/test_adaptive_router.py`, add regression test cases verifying:
   - Queries with the feature receive points.
   - Queries without the feature are unaffected.
   - Total score remains bounded between $0$ and $100$.

### 2.2 Extending Retrieval Sufficiency (`hyperrag/retrieval_sufficiency.py`)
To add a new retrieval metric to Phase 2:
1. In `RetrievalSufficiencyEvaluator.evaluate()`, extract the new metric from the retrieved `retrieval_context`.
2. In `SufficiencyWeights`, define the metric's weight or penalty value.
3. Incorporate the metric into the sufficiency formula, maintaining the $0 - 100$ score bounds.
4. Add regression tests to `tests/unit/test_retrieval_sufficiency.py`.

### 2.3 Extending Response Validation (`hyperrag/response_validator.py`)
To add new validation criteria:
1. In `DeterministicResponseValidator`, implement the evaluation helper method (e.g. `_evaluate_my_dimension()`).
2. Update `ValidationResult` if new diagnostic fields are returned.
3. In `tests/unit/test_response_validator.py`, add isolated test assertions.

> [!CAUTION]
> **Zero LLM Invariant**: Never introduce an LLM call inside `adaptive_router.py`, `retrieval_sufficiency.py`, or `response_validator.py`. All three phases must remain 100% deterministic and execute in-process.

---

## 3. Web UI Development (`web-ui/`)

### Frontend (`web-ui/frontend/`)
- **Framework**: React 18 with Vite.
- **Routing**: React Router (HashRouter: `/#/Chat`, `/#/DB`, `/#/Graph`, `/#/Files`, `/#/API`, `/#/Setting`).
- **Icons & Visualization**: Lucide React, 2D/3D Force Graph (`react-force-graph`).
- **Development Server**: `npm run dev` (proxies `/api` to backend on port 8000).
- **Production Build**: `npm run build` generates optimized assets in `web-ui/frontend/dist/`.

### Backend (`web-ui/backend/`)
- **Framework**: FastAPI with asynchronous endpoints.
- **File Management**: `file_manager.py` handles chunking, storage mapping, and filename sanitization.
- **Database Layer**: `db.py` exposes vertices, hyperedges, and neighbors.
- **Real-Time Updates**: WebSocket endpoint `/ws` broadcasts embedding progress.

---

## 4. Coding & Architecture Standards

1. **Python Compatibility**: Target Python 3.10 and 3.11. Use `from __future__ import annotations` where appropriate.
2. **Pydantic V2**: Use modern Pydantic V2 syntax (e.g., `model_dump()` instead of `.dict()`).
3. **No Unmanaged File Handlers**: Always use explicit context managers or the logger deduplication in `hyperrag/utils.py` to prevent resource leaks.
4. **No Raw Warnings in Pipelines**: Use `logger.warning(...)` instead of `warnings.warn(...)` for operational diagnostic messages.
5. **English-Only Prose**: All user-facing strings, API error messages, documentation, and log outputs must be strictly in clear English.
6. **Key Masking**: Never print or log raw API keys. Always use masked representation (`sk-or-***`).

---

## 5. Documentation Maintenance Guide

To ensure documentation remains accurate and synchronized with code changes, follow this update matrix:

| Code / Feature Changed | Documents Requiring Updates |
|---|---|
| **Adaptive Routing / Thresholds** | `docs/ADAPTIVE_HYPERRAG.md`, `docs/CONFIGURATION.md`, `docs/USER_MANUAL.md`, `ADAPTIVE_ROUTING.md`, `docs/APPENDICES.md` |
| **Sufficiency / Escalation** | `docs/ADAPTIVE_HYPERRAG.md`, `docs/ARCHITECTURE.md`, `docs/USER_MANUAL.md` |
| **Response Validator (Phase 3)** | `docs/ADAPTIVE_HYPERRAG.md`, `docs/API_REFERENCE.md`, `docs/USER_MANUAL.md` |
| **REST Endpoints / Schemas** | `docs/API_REFERENCE.md`, `docs/WEB_UI_GUIDE.md`, `docs/USER_MANUAL.md` |
| **Environment Variables (`.env`)**| `docs/CONFIGURATION.md`, `.env.example`, `docs/USER_MANUAL.md`, `docs/GETTING_STARTED.md` |
| **Web UI Views / Components** | `docs/WEB_UI_GUIDE.md`, `docs/USER_MANUAL.md` |
| **Test Suites / Counts** | `docs/TESTING.md`, `docs/VERIFICATION_AND_OUTCOMES.md`, `docs/APPENDICES.md` |

### Recording Verification Outcomes
When full pipeline verification is executed:
1. Check outputs in `logs/full_pipeline_YYYYMMDD_HHMMSS/SUMMARY.md`.
2. Update the baseline metrics in `docs/VERIFICATION_AND_OUTCOMES.md` and `docs/APPENDICES.md`.
3. Record newly resolved issues in `docs/VERIFICATION_AND_OUTCOMES.md`.
4. Update `docs/DOCUMENTATION_CHANGELOG.md` with the changes.
