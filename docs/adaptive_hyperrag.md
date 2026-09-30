# Adaptive Hyper-RAG Subsystem

Adaptive Hyper-RAG is a two-phase dynamic routing and escalation engine designed to achieve optimal trade-offs between computational overhead, query latency, and retrieval quality.

---

## 1. Multi-Phase Architecture

```text
User Query
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
            ├── YES (Score >= Threshold):
            │      ↓
            │   Hyper-Lite Reasoning (Remains Lite)
            │
            └── NO (Score < Threshold / Weak Evidence):
                   ↓
                [Escalation] Hyper-Core Retrieval & Reasoning
    ↓
FINAL ANSWER
    ↓
[Phase 3] Response Validator (Deterministic In-Process Evaluation: 0 LLM Calls)
    ↓
Validated Answer + Validation Metadata
```

---

## 2. Phase 1: Deterministic Query Complexity Routing

### Motivation
Different questions demand vastly different retrieval depths. Simple factual lookups (*"What is diabetes?"*) require only basic entity-grounded text passages, whereas comparative or causal questions (*"Compare diabetes and hypertension..."*) require multi-entity relational hyperedge traversal.

Phase 1 evaluates complexity **before** executing retrieval, incurring **zero LLM cost**.

### Extracted Signals (8 Categories)

1. **Multi-Aspect Questions**:
   - Conjunctions (`and`, `as well as`, `including`).
   - Comma-separated clause enumerations.
   - Domain aspects (`causes`, `symptoms`, `treatment`, `prevention`).
2. **Comparison**:
   - `compare`, `versus`, `difference between`, `differ from`, `in contrast to`.
3. **Causal / Explanatory Reasoning**:
   - `why`, `how does`, `causes`, `effect`, `mechanism`, `leads to`, `contribute to`.
4. **Temporal Reasoning**:
   - `over time`, `timeline`, `historically`, `evolution`, year ranges (`2000-2020`).
5. **Multi-Hop Reasoning**:
   - `relationship between`, `how A affects B through C`, `associated with`, `pathway`.
6. **Aggregation / Synthesis**:
   - `summarize all`, `list all`, `across multiple sources`, `synthesize`.
7. **Entity Count Estimation**:
   - Quoted phrases (`"Type 1 Diabetes"`).
   - Proper-noun sequences (`Alzheimer's Disease`).
   - Stopword-filtered content noun chunks (dependency-free regex heuristic).
8. **Requested Depth**:
   - `detailed`, `in-depth`, `exhaustive`, `step by step`, `comprehensive`.

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
- $\text{Score} < 60 \implies$ **Hyper-Lite**
- $\text{Score} \ge 60 \implies$ **Hyper-Core**

---

## 3. Phase 2: Retrieval Sufficiency & Lite → Core Escalation

### Motivation
Pre-retrieval routing cannot predict whether the knowledge base actually contains sufficient documents for a query. A query may score low on complexity ($35 / 100$), but Lite retrieval might return empty results, redundant chunks, or lack relational evidence.

Phase 2 inspects the retrieved context **before** LLM reasoning and triggers automatic escalation if evidence is insufficient.

### Retrieved Evidence Metrics
The evaluator measures:
- `num_items`: Number of entities and text units retrieved.
- `num_unique_entities`: Diversity of distinct entities retrieved.
- `context_length`: Total character volume of context text.
- `query_entity_coverage`: Lexical and entity token overlap between query terms and retrieved chunks.
- `duplicate_ratio`: Repetitive chunk overlap penalty using Jaccard token similarity.
- `num_hyperedges`: Presence of high-order relational connections.

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

### Decision Boundary & Escalation Rule
- **Threshold**: Default is `60.0` (`ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD`).
- **If Score $\ge$ 60.0**: Retrieval is **SUFFICIENT**. Proceeds directly to Lite reasoning.
- **If Score < 60.0**: Retrieval is **INSUFFICIENT**.
  1. Aborts Lite LLM reasoning.
  2. Sets `decision.escalated = True` and `decision.final_mode = "core"`.
  3. Executes Hyper-Core retrieval and reasoning.
  4. At most **one** escalation check is performed per query.

---

## 4. Phase 2.1: Short-Query Semantic-Density Refinement

### Motivation
In the original Phase 1 complexity router, query score scaled partly with token length and sentence structure. Consequently, concise queries with dense semantic relationships (such as Q32: *"How did greed cause Marley's chains?"* and Q33: *"Compare Fred vs Scrooge"*) scored below the default threshold of 60 (receiving 47 and 51, respectively). While Phase 2 correctly rescued them to Core via sufficiency escalation, executing Lite retrieval first added unnecessary latency and retrieval operations.

Phase 2.1 optimizes the **initial routing decision** so that short, high-order relational queries route directly to Core upfront, without altering the routing of simple factual queries.

### Short-Query Definition & Trigger Signals
- **Boundary**: `word_count <= ADAPTIVE_SHORT_QUERY_MAX_WORDS` (default: **7 words**).
- **Triggers**: High-order semantic flags identified by `QueryComplexityAnalyzer`:
  - `comparison = True`
  - `causal_reasoning = True`
- **Bonus Applied**: `+15.0` (`ADAPTIVE_SHORT_QUERY_DENSITY_BONUS`).
- **Threshold**: Maintained strictly at `ADAPTIVE_CORE_THRESHOLD = 60`.

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
- *"Who was Tiny Tim?"* $\rightarrow$ Score `6` (Lite)

### Benchmark Impact (39 Queries)
- **Escalations Reduced**: 5 $\rightarrow$ 3 (40% reduction).
- **Average Latency**: 134.30 ms $\rightarrow$ 82.15 ms (38.8% latency reduction).
- **False-Core Cases**: 0.

---

## 5. Decision Metadata

Clients can access the full adaptive decision lifecycle via `rag.last_adaptive_decision`:

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

## 6. Diagnostic Logging Output

When `ADAPTIVE_LOG_DECISIONS=true`:

### Sufficient Lite Query:
```text
[Adaptive RAG]
Initial complexity score: 6 (threshold: 60) -> Initial mode: LITE
[Adaptive RAG]
Initial mode: LITE
Retrieval sufficiency score: 65.0
Status: SUFFICIENT
No escalation required
```

### Insufficient Lite Query with Escalation:
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

### Initially Core Query:
```text
[Adaptive RAG]
Initial complexity score: 86 (threshold: 60) -> Initial mode: CORE
[Adaptive RAG]
Initial mode: CORE
Skipping Lite sufficiency check
```

---

## 7. Phase 3: Response Validation

### Motivation & Purpose
Validation operates strictly **downstream** of final answer synthesis. It examines the generated answer in relation to the user query and the retrieved context to verify that:
1. All requested query entities, dimensions, and relational questions are addressed;
2. Major answer claims are grounded in retrieved evidence;
3. Topic drift or hallucination away from the query intent is identified;
4. Unsupported claims are isolated and flagged without altering the answer.

### Pipeline Location
```text
Final Answer (from Lite or Core reasoning)
    ↓
DeterministicResponseValidator.validate(query, answer, context, adaptive_decision)
    ↓
ValidationResult attached to QueryParam and API response
```

### The Three Core Dimensions (0–100)

#### 1. Completeness Analysis
- **Aspect & Entity Extraction**: Reuses `QueryFeatures` from Phase 1 (`comparison`, `causal_reasoning`, `temporal_reasoning`, `multi_hop`, `aggregation`, `detected_entities`, `aspect_count`).
- **Comparison Validation**: Verifies both compared entities are discussed, along with requested dimensions and comparative connective terminology.
- **Causal Validation**: Distinguishes mere entity presence from explanatory causal relationship structures.
- **Temporal Progression**: Confers completeness for chronological progression over time, penalizing single-point answers for multi-period questions.
- **Multi-Hop Traversal**: Verifies intermediate nodes and relationship pathways.
- **Aggregation**: Flags potential incompleteness relative to retrieved evidence if comprehensive enumeration was requested.

#### 2. Evidence Support Analysis
- **Claim-Level Grounding**: Segment answers into discrete assertions.
- **Local Context Comparison**: Checks entity overlap, keyword presence, and n-gram overlap against retrieved context (`text_units`, `entities`, `hyperedges`).
- **Unsupported Claims**: Detects foreign entities, ungrounded dates, or ungrounded statistics not present in the context.
- *CRITICAL INVARIANT*: **Evidence-supported does NOT mean globally fact-checked.** The validator only checks alignment against locally retrieved context.

#### 3. Relevance Analysis
- Measures overlap and topic alignment between user query terms and the answer, penalizing off-topic tangents while permitting legitimate explanatory detail.

### Scoring Formula & Configurable Weights
$$\text{Overall Score} = (\text{Completeness} \times 0.40) + (\text{Evidence} \times 0.40) + (\text{Relevance} \times 0.20)$$

- Default Threshold: **70.0**
- Hard Failure Rules:
  - Empty or whitespace answer: $\text{Score} = 0$, `valid = False`.
  - Substantial unsupported assertions: $\text{Evidence} < 30 \implies \text{valid} = \text{False}$.
  - Major missing aspects / comparison entities: $\text{valid} = \text{False}$.
  - Irrelevant topic drift: $\text{Relevance} < 30 \implies \text{valid} = \text{False}$.

### Result Schema (`ValidationResult`)
```python
ValidationResult(
    valid=True,
    score=88.0,
    completeness_score=94.0,
    evidence_score=84.0,
    relevance_score=90.0,
    missing_aspects=[],
    unsupported_claims=[],
    reasons=["All requested aspects addressed", "Major claims supported by retrieved evidence"],
    metrics={"claim_count": 3, "supported_claims": 3, "context_length": 1420}
)
```

### Configuration Parameters
```env
ADAPTIVE_VALIDATION_ENABLED=true
ADAPTIVE_VALIDATION_THRESHOLD=70
ADAPTIVE_VALIDATION_LOG_DECISIONS=true
ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT=0.40
ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT=0.40
ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT=0.20
```

### Phase 4 Explicit Boundary
Phase 3 is strictly validation and diagnostics. The following are **NOT** implemented:
- Automatic answer rewriting
- Automatic regeneration
- Re-retrieval loops
- Validation-to-Core escalation
- LLM-as-a-judge (0 additional LLM calls)
The generated response remains completely untouched.

---

## 8. Test Architecture & Execution

The test suite enforces full regression testing across all phases:

### Directory Structure

- `tests/unit/`: Fast, hermetic, mocked unit tests testing components in isolation:
  - `test_adaptive_router.py`: Tests Phase 1 query complexity scoring, classification, and Phase 2.1 short query density bonuses.
  - `test_retrieval_sufficiency.py`: Tests Phase 2 retrieval sufficiency evaluation and Lite $\rightarrow$ Core escalation logic.
  - `test_response_validator.py`: Tests Phase 3 response validation across completeness, evidence support, relevance, unsupported claim detection, and failure modes.
  - `test_key_rotation.py`: Tests multi-key pool rotation, 429 backoff, 401 handling, and concurrency safety.
  - `test_language_guard.py`: Tests deterministic Latin-script compliance and English-only validation.
  - `test_config.py`: Tests environment variable parsing and configuration invariants.
- `tests/internal/`: Live diagnostic scripts verifying external upstream providers (OpenRouter LLM and Mistral embeddings).

### Running Tests

```bash
# Run all maintained unit tests (67 tests, 0 warnings)
python -m pytest tests/unit -v

# Run individual test modules
python -m pytest tests/unit/test_adaptive_router.py
python -m pytest tests/unit/test_retrieval_sufficiency.py
python -m pytest tests/unit/test_response_validator.py
python -m pytest tests/unit/test_language_guard.py
```

---

## 9. Web UI Adaptive Integration & English-Only Policy

### Web UI Integration
The Web UI (`web-ui/frontend` and `web-ui/backend`) natively integrates the Adaptive RAG pipeline:
- **Default Mode**: Adaptive RAG is the default operational mode across both the chat interface and the backend API (`QueryModel.mode = "adaptive"`).
- **Frontend Transmission**: The frontend sends an explicit payload (`mode: "adaptive"`) when executing queries.
- **Canonical Routing**: The backend server calls `rag.aquery()` / `rag.astream_query()` with `QueryParam(mode="adaptive")`, which dispatches directly to `AdaptiveRouter` in `hyperrag/adaptive_router.py`.
- **Metadata Visibility**: The backend emits structured metadata including `adaptive_decision`, `validation`, and `language_guard` results alongside the answer.

### English-Only Output Policy
All user-facing prose, UI text, API responses, generated answers, and internal documentation are strictly English-only:
- **`LanguageGuard`**: A deterministic in-process script analyzer (`hyperrag/language_guard.py`) verifies that output answers do not contain CJK or non-Latin prose.
- **Zero LLM Judge Overhead**: Language compliance is verified deterministically without secondary LLM invocations or rewriting.

### Existing-Data Validation Methodology
- Verification uses existing repository fixtures, mock databases (`hyperrag_cache/mock`), and unit tests.
- **No External Maritime Corpus**: Validation is strictly self-contained within project-owned data and does not reference or depend upon external datasets.


