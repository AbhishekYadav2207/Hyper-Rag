# Adaptive Hyper-RAG: Deterministic Query Complexity Routing & Escalation

> [!NOTE]
> This document provides the architectural theory and historical design notes for Adaptive Hyper-RAG. For the complete, beginner-friendly user manual and operational runbooks, see [**`docs/USER_MANUAL.md`**](docs/USER_MANUAL.md). For the in-depth technical specification covering Phases 1, 2, 2.1, and 3, see [**`docs/ADAPTIVE_HYPERRAG.md`**](docs/ADAPTIVE_HYPERRAG.md).

---

## 1. Overview

Adaptive Hyper-RAG introduces a deterministic routing layer positioned above the existing Hyper-Lite and Hyper-Core retrieval pipelines.

### The Original Problem
In the original Hyper-RAG implementation, every query must manually specify a static retrieval mode:
- Forcing **Hyper-Core** on all queries introduces unnecessary graph diffusion and high-order hyperedge processing for simple, single-entity factual lookups.
- Forcing **Hyper-Lite** on all queries strips away higher-order relationship structures, causing complex, multi-entity, comparative, or causal queries to lack contextual connectivity.

### The Adaptive Solution
Adaptive Hyper-RAG dynamically evaluates the syntactic, structural, and semantic complexity of incoming queries before retrieval, and evaluates retrieval sufficiency after retrieval:

```text
User Question
    ↓
Query Complexity Analysis (Phase 1 & 2.1)
    ↓
Lite / Core Selection
    ├── If Core: Core Retrieval → High-Order Reasoning
    └── If Lite: Lite Retrieval → Sufficiency Check (Phase 2)
                                       ├── Sufficient → Lite Reasoning
                                       └── Insufficient → Escalates to Core
    ↓
Final Answer
    ↓
Phase 3 Response Validation
    ↓
Client
```

### Architectural Principles
- **Local Execution**: The routing evaluation runs entirely in-process using deterministic rule-based algorithms.
- **Zero LLM Overhead**: No LLM call is made to score query complexity, evaluate retrieval sufficiency, or validate responses.
- **Zero Additional API Costs or Latency**: Query routing incurs zero external network latency and zero API tokens.
- **Pipeline Preservation**: The router does not alter, replace, or redesign existing Hyper-Lite or Hyper-Core retrieval algorithms.
- **At Most One Escalation**: Exactly one escalation check occurs per query (Lite $\rightarrow$ Core).

---

## 2. Multi-Phase Architecture

### Phase 1: Pre-Retrieval Complexity Scoring
- **12 Signals across 8 Categories**: Multi-aspect, comparison, causal, temporal, multi-hop, aggregation, entity count, and depth requests.
- **Point System**: Additive transparent point contributions normalized to a $0 - 100$ scale.
- **Threshold**: Default `60` (`ADAPTIVE_CORE_THRESHOLD`). Score $< 60$ routes to Lite; $\ge 60$ routes to Core.

### Phase 2: Post-Retrieval Sufficiency Evaluation & Early Escalation
- Evaluates the concrete retrieved context *before* calling the LLM.
- **Metrics**: Item volume, unique entities, context length, query-context lexical overlap, redundancy penalty, and missing relationship penalty.
- **Threshold**: Default `60.0` (`ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD`).
- **Escalation**: If score $< 60.0$, Lite reasoning is aborted before calling the LLM and the query escalates to Hyper-Core.

### Phase 2.1: Short-Query Semantic-Density Refinement
- Queries with $\le 7$ words (`ADAPTIVE_SHORT_QUERY_MAX_WORDS`) containing comparison or causal terms receive a $+15.0$ density bonus (`ADAPTIVE_SHORT_QUERY_DENSITY_BONUS`).
- Directly routes compact relational queries (e.g. *"Compare Fred vs Scrooge"*) to Core upfront, eliminating unnecessary Lite retrieval attempts.

### Phase 3: Post-Reasoning Response Validation
- Evaluates the synthesized answer on **Completeness** ($0.40$), **Evidence Support** ($0.40$), and **Relevance** ($0.20$).
- Minimum threshold: `70.0` / 100.
- Hard failures for empty answers, evidence $< 30$, or relevance $< 30$.
- **Boundary Statement**: Evidence-supported $\neq$ globally fact-checked.
- **Phase 4 Explicit Boundary**: Self-repair, automatic rewriting, and regeneration are strictly not implemented.

---

## 3. Configuration Reference

```env
# Master Toggle
ADAPTIVE_RAG_ENABLED=true
ADAPTIVE_RAG_MODE=adaptive

# Phase 1 Complexity Cutoff (0-100)
ADAPTIVE_CORE_THRESHOLD=60

# Phase 2 Sufficiency Cutoff (0-100)
ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED=true
ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD=60

# Phase 2.1 Short-Query Density Bonus
ADAPTIVE_SHORT_QUERY_MAX_WORDS=7
ADAPTIVE_SHORT_QUERY_DENSITY_BONUS=15.0

# Phase 3 Response Validation
ADAPTIVE_VALIDATION_ENABLED=true
ADAPTIVE_VALIDATION_THRESHOLD=70
ADAPTIVE_VALIDATION_LOG_DECISIONS=true
ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT=0.40
ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT=0.40
ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT=0.20

# Diagnostics Logging
ADAPTIVE_LOG_DECISIONS=true
```

---

## 4. Test Verification & Code Examples

See detailed examples and test commands in:
- [**`docs/USER_MANUAL.md`**](docs/USER_MANUAL.md#11-first-query-walkthrough)
- [**`docs/TESTING.md`**](docs/TESTING.md)
- [**`docs/ADAPTIVE_HYPERRAG.md`**](docs/ADAPTIVE_HYPERRAG.md)
