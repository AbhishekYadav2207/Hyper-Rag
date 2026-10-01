# Hyper-RAG Documentation Appendices

---

## Appendix A: Final Verification Outcomes

The verified baseline recorded in `logs/full_pipeline_20260930_234500/SUMMARY.md`:

```text
================================================================================
                    HYPER-RAG FINAL VERIFICATION OUTCOMES
================================================================================
Pipeline Automated Checks:      32 / 32 PASS
Pytest Unit Tests:              67 / 67 PASS
Web UI Views:                    6 /  6 PASS
FastAPI Endpoints:               4 /  4 PASS
Benchmark Evaluations:           2 /  2 PASS
Security & Boundary Checks:      3 /  3 PASS
Active Runtime Warnings:         0
Active Runtime Errors:           0
================================================================================
```

---

## Appendix B: Adaptive Routing Reference

### Phase 1 Complexity Scoring Weights
Defined in [`hyperrag/adaptive_router.py`](../hyperrag/adaptive_router.py#L28):

```text
Point Allocations:
  Comparison:                   +20 pts
  Causal / Explanatory:         +15 pts
  Temporal Reasoning:           +15 pts
  Multi-Hop Reasoning:          +15 pts
  Aggregation / Synthesis:      +15 pts
  Requested Depth:              +12 pts
  Relational Reasoning:         +10 pts

Entity Count Scoring:
  1 detected entity:             +5 pts
  2 detected entities:          +10 pts
  3 detected entities:          +15 pts
  4+ detected entities:         +20 pts

Multi-Aspect Scoring:
  2 distinct aspects:            +8 pts
  3 distinct aspects:           +12 pts
  4+ distinct aspects:          +16 pts

Structural Scaling:
  Word Count:         min(10.0, word_count * 0.35)
  Sentence Count:     min(6.0, (sentence_count - 1) * 3.0)
  Question Marks:     min(4.0, (question_count - 1) * 2.0)
```

- **Core Threshold**: `60` (`ADAPTIVE_CORE_THRESHOLD`).
- **Phase 2.1 Density Bonus**: `+15.0` points applied to queries with $\le 7$ words containing comparison or causal signals.

---

## Appendix C: Phase 3 Response Validation Reference

### Validation Formula
$$\text{Score} = (0.40 \times \text{Completeness}) + (0.40 \times \text{Evidence}) + (0.20 \times \text{Relevance})$$

- **Threshold**: `70.0` (`ADAPTIVE_VALIDATION_THRESHOLD`).
- **Hard Failure Criteria**:
  - Empty or whitespace answer: $\text{Score} = 0$, `valid = False`.
  - Evidence support $< 30$: `valid = False`.
  - Missing $>50\%$ of requested query aspects: `valid = False`.
  - Topic relevance $< 30$: `valid = False`.

---

## Appendix D: Configuration Quick Reference

| Environment Variable | Default | Permitted Values | Purpose |
|---|---|---|---|
| `OPENROUTER_API_KEYS` | *None* | Comma-separated | OpenRouter API keys for round-robin rotation |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | URL | OpenAI-compatible endpoint |
| `OPENROUTER_MODEL` | `nvidia/nemotron-3-ultra-550b-a55b:free` | Model ID | Model used for text reasoning & streaming |
| `EMB_API_KEYS` | *None* | Comma-separated | Mistral API keys for rotation |
| `EMB_BASE_URL` | `https://api.mistral.ai/v1` | URL | Mistral API endpoint |
| `EMB_MODEL` | `mistral-embed` | Model ID | Embedding model (1024 dimensions) |
| `EMB_DIM` | `1024` | Strict `1024` | Embedding output dimension |
| `ADAPTIVE_RAG_ENABLED`| `true` | `true`, `false` | Master toggle for dynamic routing |
| `ADAPTIVE_CORE_THRESHOLD`| `60` | `0` - `100` | Pre-retrieval complexity threshold |
| `ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED` | `true` | `true`, `false` | Post-retrieval sufficiency check |
| `ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD` | `60` | `0` - `100` | Sufficiency threshold for Lite $\rightarrow$ Core escalation |
| `ADAPTIVE_VALIDATION_ENABLED` | `true` | `true`, `false` | Phase 3 response validation toggle |
| `ADAPTIVE_VALIDATION_THRESHOLD` | `70` | `0` - `100` | Minimum score for `valid = True` |

---

## Appendix E: Test Command Quick Reference

```bash
# 1. Run all 67 fast unit tests
python -m pytest tests/unit -v

# 2. Run specific test modules
python -m pytest tests/unit/test_adaptive_router.py -v
python -m pytest tests/unit/test_retrieval_sufficiency.py -v
python -m pytest tests/unit/test_response_validator.py -v
python -m pytest tests/unit/test_key_rotation.py -v
python -m pytest tests/unit/test_language_guard.py -v
python -m pytest tests/unit/test_config.py -v

# 3. Run live provider smoke tests (requires API keys in .env)
python tests/internal/test_openrouter.py
python tests/internal/test_embedding.py

# 4. Run benchmarks
python pilot_benchmark.py
python run_full_benchmark.py

# 5. Build Web UI production bundle
cd web-ui/frontend && npm run build && cd ../..

# 6. Start Web UI backend
python -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000 --reload

# 7. Start Web UI frontend
cd web-ui/frontend && npm run dev
```

---

## Appendix F: Repository File Map

| File / Path | Category | Purpose | Importance |
|---|---|---|---|
| `hyperrag/hyperrag.py` | Core Library | Primary orchestrator class (`HyperRAG`) | **Critical** |
| `hyperrag/adaptive_router.py` | Core Library | Phase 1 & 2.1 complexity scoring and routing | **Critical** |
| `hyperrag/retrieval_sufficiency.py` | Core Library | Phase 2 post-retrieval sufficiency and escalation | **Critical** |
| `hyperrag/response_validator.py` | Core Library | Phase 3 response validation | **Critical** |
| `hyperrag/key_pool.py` | Core Library | Multi-key round-robin rotation and 429 backoff | High |
| `hyperrag/llm.py` | Core Library | OpenRouter and Mistral API wrappers | High |
| `hyperrag/operate.py` | Core Library | Low-level retrieval and hypergraph diffusion | **Critical** |
| `service_api.py` | Server | Standalone production REST & streaming server | High |
| `web-ui/backend/main.py` | Web UI | FastAPI server for full Web Console | High |
| `web-ui/frontend/` | Web UI | React 18 / Vite frontend single-page application | High |
| `my_config.py` | Configuration | Central environment variable parser and validator | **Critical** |
| `.env.example` | Configuration | Deployment environment template | **Critical** |
| `tests/unit/` | Testing | 67 fast hermetic unit tests | **Critical** |

---

## Appendix G: Glossary

- **RAG (Retrieval-Augmented Generation)**: Architecture that enhances LLMs by retrieving relevant context documents before generating an answer.
- **Hypergraph**: A generalized graph structure where an edge (hyperedge) can connect an arbitrary number of vertices simultaneously, rather than just two.
- **Hyperedge**: A multi-entity relational connector binding two or more entities together within a single unified fact or interaction.
- **Hyper-Lite**: Fast, lightweight retrieval pipeline utilizing direct vector search over entity embeddings and text chunks without hyperedge diffusion.
- **Hyper-Core**: Full hypergraph retrieval pipeline traversing incident hyperedges, performing graph diffusion, and aggregating multi-hop relational pathways.
- **Adaptive RAG**: Dynamic routing system that automatically selects Lite or Core based on measured query complexity and retrieved evidence.
- **Query Complexity**: Quantitative measure ($0-100$) of the structural and semantic reasoning depth demanded by a question.
- **Retrieval Sufficiency**: Evaluation assessing whether the retrieved context passages provide adequate evidence to answer the query.
- **Response Validation**: Deterministic post-generation evaluation scoring an answer on completeness, evidence support, and relevance.
- **Embedding**: Dense numerical vector representing the semantic meaning of text (1024 dimensions via Mistral).
- **Streaming (SSE)**: Server-Sent Events protocol delivering answer tokens to the client incrementally as they are generated.

---

## Appendix H: Frequently Asked Questions (FAQ)

### 1. Why does Hyper-RAG default to Adaptive mode?
Adaptive mode delivers the best of both worlds: simple questions receive instantaneous answers with minimal compute, while complex relational questions automatically receive deep hypergraph reasoning.

### 2. Can I force Hyper-Lite or Hyper-Core manually?
Yes. Pass `QueryParam(mode="lite")` to force Lite mode or `QueryParam(mode="core")` to force Core mode. Manual modes bypass adaptive routing and sufficiency checks.

### 3. What triggers a Lite $\rightarrow$ Core escalation?
If a query begins in Lite mode, but the retrieved context has low volume, low unique entity diversity, poor query coverage, or lacks required hyperedges for causal/multi-hop questions, Phase 2 detects insufficient evidence ($<60$) and escalates to Core.

### 4. Does escalation waste LLM generation tokens?
No. Lite retrieval is split into retrieval (`hyper_retrieve_lite`) and reasoning (`hyper_query_lite_reasoning`). If escalated, Lite reasoning is aborted before calling the LLM.

### 5. Why are OpenRouter and Mistral both used?
OpenRouter provides top-tier text reasoning models and token streaming. Mistral provides state-of-the-art 1024-dimensional dense embeddings. Using each provider for its specialized strength achieves optimal price-to-performance.

### 6. Where are local hypergraphs stored?
Hypergraphs and vector databases are stored in the directory defined by `WORKING_DIR` (defaults to `./caches/pathology` or `./caches/default`).

### 7. How do I clear cached data?
Delete the cache directory or use the Web UI **Reset Knowledge Base** button in Settings.
