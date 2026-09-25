# Adaptive Hyper-RAG Subsystem

Adaptive Hyper-RAG is a two-phase dynamic routing and escalation engine designed to achieve optimal trade-offs between computational overhead, query latency, and retrieval quality.

---

## 1. Multi-Phase Architecture

```text
User Query
    ↓
[Phase 1] Adaptive Query Router (Deterministic Pre-Retrieval Complexity Scoring)
    ↓
Initial Mode Decision: Hyper-Lite OR Hyper-Core
    ├── If Hyper-Core:
    │      ↓
    │   Hyper-Core Retrieval → High-Order Reasoning → Answer
    │
    └── If Hyper-Lite:
           ↓
        Hyper-Lite Retrieval (Keywords & Entities)
           ↓
        [Phase 2] Retrieval Sufficiency Evaluator (Deterministic Post-Retrieval Scoring)
           ↓
        Sufficient Evidence?
            ├── YES (Score >= Threshold):
            │      ↓
            │   Hyper-Lite Reasoning → Answer (Remains Lite)
            │
            └── NO (Score < Threshold / Weak Evidence):
                   ↓
                [Escalation] Escalate to Hyper-Core Retrieval & Reasoning → Answer
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

## 4. Decision Metadata

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

## 5. Diagnostic Logging Output

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
