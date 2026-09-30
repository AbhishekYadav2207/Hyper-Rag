# Adaptive Hyper-RAG Subsystem: Technical Specification

**Dynamic Query Complexity Routing, Post-Retrieval Sufficiency Escalation, and Deterministic Response Validation**

---

## 1. Executive Summary & Architecture

Adaptive Hyper-RAG is a dynamic routing and evaluation subsystem engineered to optimize the trade-off between computational cost, response latency, and retrieval quality.

```text
User Question
    ↓
[Phase 1 + 2.1] Adaptive Query Router (Deterministic Complexity Scoring & Semantic Density)
    ↓
Initial Mode Decision: Hyper-Lite OR Hyper-Core
    ├── If Hyper-Core:
    │      ↓
    │   Hyper-Core Retrieval → High-Order Reasoning
    │
    └── If Hyper-Lite:
           ↓
        Hyper-Lite Retrieval (Keywords & Entities)
           ↓
        [Phase 2] Retrieval Sufficiency Evaluator (Deterministic Evidence Scoring)
           ↓
        Sufficient Evidence?
            ├── YES (Score >= 60):
            │      ↓
            │   Hyper-Lite Reasoning (Remains Lite)
            │
            └── NO (Score < 60):
                   ↓
                [Escalation] Abort Lite Reasoning → Hyper-Core Retrieval & Reasoning
    ↓
FINAL ANSWER
    ↓
[Phase 3] Response Validator (Deterministic In-Process Evaluation: 0 LLM Calls)
    ↓
Validated Answer + Structured Validation Metadata
```

### Core Invariants
1. **Zero LLM Judge Overhead**: All routing, sufficiency evaluation, and response validation algorithms run completely in-process using deterministic Python algorithms. No LLM tokens or external API calls are consumed for decision-making.
2. **Zero Wasted LLM Generation on Escalation**: When Lite retrieval is deemed insufficient in Phase 2, Lite LLM reasoning is aborted *before* sending a prompt to the LLM.
3. **Evidence-Supported $\neq$ Globally Fact-Checked**: Phase 3 validation assesses answer consistency against locally retrieved passages only; it does not claim global truth verification.
4. **Strict Phase 4 Boundary**: Automatic answer rewriting, re-retrieval loops, and self-repair are explicitly out of scope and not implemented.

---

## 2. Phase 1: Deterministic Query Complexity Routing

### Motivation
Different questions demand fundamentally different retrieval depths. Direct factual lookups (*"What is diabetes?"*) require only basic entity-grounded text passages (Hyper-Lite), whereas comparative or causal questions (*"Compare diabetes and hypertension causes and mechanisms"*) require multi-entity relational hyperedge traversal (Hyper-Core).

Phase 1 evaluates complexity **before** executing retrieval, incurring **0 LLM cost** and sub-millisecond execution time.

### Extracted Signals (8 Categories, 12 Signals)

| Feature Category | Detected Signals | Heuristic Trigger Examples |
|---|---|---|
| **1. Multi-Aspect Questions** | Conjunctions, enumerations, domain aspects | `and`, `as well as`, `including`, comma-separated clauses, `causes`, `symptoms`, `treatment` |
| **2. Comparison** | Comparative verbs, contrast prepositions | `compare`, `versus`, `vs`, `difference between`, `differ from`, `in contrast to` |
| **3. Causal / Explanatory** | Causal connectives, mechanism triggers | `why`, `how does`, `how did`, `causes`, `effect`, `mechanism`, `leads to`, `contribute to` |
| **4. Temporal Reasoning** | Chronological markers, evolution | `over time`, `timeline`, `historically`, `evolution`, year ranges (`2000-2020`) |
| **5. Multi-Hop Pathways** | Relational traversal phrases | `relationship between`, `how A affects B through C`, `associated with`, `pathway` |
| **6. Aggregation / Synthesis**| Exhaustive enumeration markers | `summarize all`, `list all`, `across multiple sources`, `synthesize` |
| **7. Entity Count** | Quoted terms, proper nouns, noun chunks | Lightweight regex heuristic extracting quoted entities and capitalized sequences |
| **8. Requested Depth** | Explicit depth directives | `detailed`, `in-depth`, `exhaustive`, `step by step`, `comprehensive` |

### Phase 1 Scoring Formula
Normalized between $0$ and $100$:

$$\text{Complexity Score} = \min(100, \max(0, \text{StructuralPts} + \text{EntityPts} + \text{AspectPts} + \sum \text{SemanticPts}))$$

#### Default Point Allocations
```text
Comparison:                 +20 pts
Causal / Explanatory:       +15 pts
Temporal:                   +15 pts
Multi-Hop:                  +15 pts
Aggregation:                +15 pts
Requested Depth:            +12 pts
Relational Reasoning:       +10 pts

Entity Count:
  1 entity:                  +5 pts
  2 entities:               +10 pts
  3 entities:               +15 pts
  4+ entities:              +20 pts

Multi-Aspect:
  2 aspects:                 +8 pts
  3 aspects:                +12 pts
  4+ aspects:               +16 pts

Structural:
  Word count:      min(10.0, word_count × 0.35)
  Sentence count:  min(6.0, (sentence_count - 1) × 3.0)
  Question marks:  min(4.0, (question_count - 1) × 2.0)
```

#### Decision Boundary
- **Score $< 60$** $\implies$ **Hyper-Lite**
- **Score $\ge 60$** $\implies$ **Hyper-Core**

---

## 3. Phase 2: Retrieval Sufficiency & Lite → Core Escalation

### Motivation
Pre-retrieval complexity scoring cannot predict whether the knowledge base actually contains the required facts for a query. A query may score low on complexity ($35 / 100$), but Lite retrieval might return empty results, repetitive passages, or lack required relational evidence.

Phase 2 inspects the retrieved context **before** invoking the LLM, triggering automatic escalation if evidence is insufficient.

### Retrieved Evidence Metrics
- `num_items`: Number of entities and text units retrieved.
- `num_unique_entities`: Diversity of distinct entities retrieved.
- `context_length`: Total character volume of context text.
- `query_entity_coverage`: Lexical and entity token overlap between query terms and retrieved chunks.
- `duplicate_ratio`: Repetitive chunk overlap penalty using Jaccard token similarity.
- `num_hyperedges`: Presence of high-order relational hyperedge connections.

### Phase 2 Scoring Formula

$$\text{Sufficiency Score} = \min(100, \max(0, S_{\text{base}} - P_{\text{duplicate}} - P_{\text{relational}}))$$

Where:
- $S_{\text{volume}} = \min(1.0, \frac{\text{num\_items}}{\text{expected\_items}}) \times 100$
- $S_{\text{entities}} = \min(1.0, \frac{\text{num\_unique\_entities}}{\text{expected\_entities}}) \times 100$
- $S_{\text{length}} = \min(1.0, \frac{\text{context\_length}}{\text{min\_context\_length}}) \times 100$
- $S_{\text{coverage}} = \text{query\_entity\_coverage} \times 100$
- $S_{\text{base}} = 0.25 S_{\text{volume}} + 0.20 S_{\text{entities}} + 0.25 S_{\text{length}} + 0.30 S_{\text{coverage}}$
- $P_{\text{duplicate}} = \text{duplicate\_ratio} \times 20$ (up to 20 pts deduction)
- $P_{\text{relational}} = 25$ pts deduction if the query is multi-hop or causal with multiple entities, but $\text{num\_hyperedges} == 0$.

### Escalation Policy
- **Threshold**: Default is `60.0` (`ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD`).
- **If Score $\ge$ 60.0**: Retrieval is **SUFFICIENT**. Proceeds directly to Lite LLM reasoning.
- **If Score < 60.0**: Retrieval is **INSUFFICIENT**.
  1. Aborts Lite LLM reasoning.
  2. Sets `decision.escalated = True` and `decision.final_mode = "core"`.
  3. Executes Hyper-Core retrieval and reasoning.
  4. At most **one** escalation check is performed per query.

---

## 4. Phase 2.1: Short-Query Semantic-Density Refinement

### Motivation
In the original Phase 1 complexity router, query score scaled partly with token length and sentence structure. Consequently, concise queries with dense semantic relationships (such as Q32: *"How did greed cause Marley's chains?"* and Q33: *"Compare Fred vs Scrooge"*) scored below the default threshold of 60 (receiving 47 and 51, respectively). While Phase 2 correctly rescued them to Core via sufficiency escalation, executing Lite retrieval first added unnecessary latency.

Phase 2.1 optimizes the **initial routing decision** so that short, high-order relational queries route directly to Core upfront, without altering the routing of simple factual queries.

### Trigger Boundary & Signals
- **Boundary**: `word_count <= ADAPTIVE_SHORT_QUERY_MAX_WORDS` (default: **7 words**).
- **Activation Signals**:
  - `comparison = True` (e.g. *compare*, *vs*, *difference*)
  - `causal_reasoning = True` (e.g. *why*, *how did*, *cause*, *leads to*)
- **Bonus Applied**: `+15.0` (`ADAPTIVE_SHORT_QUERY_DENSITY_BONUS`).
- **Core Threshold**: Strictly preserved at `ADAPTIVE_CORE_THRESHOLD = 60`.

### Score Accounting Breakdown
```text
Final Score = Base Score + Short-Query Density Bonus
```

Observed in benchmark:
- **Q32 ("How did greed cause Marley's chains?")**:
  - Base Score: `47`
  - Density Bonus: `+15`
  - Final Score: `62` $\rightarrow$ **Core** (Initial Mode: Core; Escalation avoided)
- **Q33 ("Compare Fred vs Scrooge")**:
  - Base Score: `51`
  - Density Bonus: `+15`
  - Final Score: `66` $\rightarrow$ **Core** (Initial Mode: Core; Escalation avoided)

Short factual queries without high-order reasoning do not trigger the bonus:
- *"What is Scrooge?"* $\rightarrow$ Score `6` (Lite)
- *"Who is Marley?"* $\rightarrow$ Score `6` (Lite)
- *"What is a counting-house?"* $\rightarrow$ Score `6` (Lite)

### Measured Benchmark Impact (39 Queries)
- **Escalations Reduced**: 5 $\rightarrow$ 3 (40% reduction).
- **Average Latency**: 134.30 ms $\rightarrow$ 82.15 ms (38.8% latency reduction).
- **False-Core Cases**: 0.

---

## 5. Phase 3: Response Validation

### Motivation & Purpose
Validation operates strictly **downstream** of final answer synthesis. It examines the generated answer in relation to the user query and the retrieved context to verify that:
1. All requested query entities, dimensions, and relational questions are addressed;
2. Major answer claims are grounded in retrieved evidence;
3. Topic drift or hallucination away from the query intent is identified;
4. Unsupported claims are isolated and flagged without altering the answer.

### The Three Core Dimensions (0–100)

#### 1. Completeness Analysis ($0-100$)
- Reuses `QueryFeatures` from Phase 1 (`comparison`, `causal_reasoning`, `temporal_reasoning`, `multi_hop`, `aggregation`, `detected_entities`, `aspect_count`).
- **Comparison Validation**: Verifies both compared entities are discussed, along with comparative connective terminology.
- **Causal Validation**: Distinguishes mere entity presence from explanatory causal relationship structures.
- **Multi-Hop Traversal**: Verifies intermediate nodes and relationship pathways.

#### 2. Evidence Support Analysis ($0-100$)
- **Claim-Level Grounding**: Segments answers into discrete assertions.
- **Local Context Comparison**: Checks entity overlap, keyword presence, and n-gram overlap against retrieved context (`text_units`, `entities`, `hyperedges`).
- **Unsupported Claims**: Detects foreign entities, ungrounded dates, or ungrounded statistics not present in the context.

#### 3. Relevance Analysis ($0-100$)
- Measures overlap and topic alignment between user query terms and the answer, penalizing off-topic tangents while permitting legitimate explanatory detail.

### Scoring Formula & Configurable Weights
$$\text{Overall Score} = (\text{Completeness} \times 0.40) + (\text{Evidence} \times 0.40) + (\text{Relevance} \times 0.20)$$

- Default Threshold: **70.0** / 100
- Hard Failure Conditions:
  - Empty or whitespace answer: $\text{Score} = 0$, `valid = False`.
  - Substantial unsupported assertions: $\text{Evidence} < 30 \implies \text{valid} = \text{False}$.
  - Critical missing aspects / comparison entities: $\text{valid} = \text{False}$.
  - Irrelevant topic drift: $\text{Relevance} < 30 \implies \text{valid} = \text{False}$.

### Phase 4 Explicit Boundary
Phase 3 is strictly validation and diagnostics. The following are **NOT** implemented:
- Automatic answer rewriting
- Automatic regeneration loops
- Re-retrieval loops
- Validation-to-Core escalation
- LLM-as-a-judge (0 additional LLM calls)
The generated response remains completely untouched.

---

## 6. Decision Lifecycle Metadata (`AdaptiveDecision`)

Clients can inspect the complete decision lifecycle via `rag.last_adaptive_decision`:

```json
{
  "mode": "core",
  "score": 35,
  "threshold": 60,
  "confidence": 0.35,
  "initial_mode": "lite",
  "initial_complexity_score": 35,
  "retrieval_sufficiency_score": 32.5,
  "retrieval_sufficient": false,
  "final_mode": "core",
  "escalated": true,
  "escalation_reason": "Missing relationship evidence for multi-hop / causal query",
  "features": {
    "has_comparison": false,
    "has_causal": true,
    "has_multi_hop": true,
    "entity_count": 2
  },
  "retrieval_metrics": {
    "num_items": 2,
    "num_unique_entities": 1,
    "context_length": 450,
    "query_entity_coverage": 0.5,
    "duplicate_ratio": 0.0,
    "num_hyperedges": 0
  }
}
```

---

## 7. Diagnostic Logging Examples

When `ADAPTIVE_LOG_DECISIONS=true`:

### Scenario A: Sufficient Lite Query
```text
[Adaptive RAG]
Initial complexity score: 6 (threshold: 60) -> Initial mode: LITE
[Adaptive RAG]
Initial mode: LITE
Retrieval sufficiency score: 65.0
Status: SUFFICIENT
No escalation required
```

### Scenario B: Insufficient Lite Query with Escalation
```text
[Adaptive RAG]
Initial complexity score: 35 (threshold: 60) -> Initial mode: LITE
[Adaptive RAG]
Retrieval sufficiency score: 32.5
Status: INSUFFICIENT

[Adaptive RAG]
Escalating LITE -> CORE
Reason: Missing relationship evidence for multi-hop / causal query
[Adaptive RAG]
Executing Hyper-Core retrieval...
```

### Scenario C: Initially Core Query
```text
[Adaptive RAG]
Initial complexity score: 86 (threshold: 60) -> Initial mode: CORE
[Adaptive RAG]
Initial mode: CORE
Skipping Lite sufficiency check
```

---

## 8. Test Suite Verification

The Adaptive Hyper-RAG implementation is backed by a verified test suite in `tests/unit/`:

| Module | Test Count | Description |
|---|---|---|
| `test_adaptive_router.py` | 19 | Phase 1 scoring, classification, and Phase 2.1 density bonus |
| `test_retrieval_sufficiency.py` | 10 | Phase 2 sufficiency scoring and escalation rules |
| `test_response_validator.py` | 23 | Phase 3 completeness, evidence support, and relevance |
| `test_key_rotation.py` | 8 | Multi-key pool rotation, 429 backoff, concurrency safety |
| `test_language_guard.py` | 6 | Deterministic English Latin-script compliance |
| `test_config.py` | 1 | Environment variable invariants and bounds |
| **Total** | **67** | **67 passed, 0 failures, 0 warnings** |
