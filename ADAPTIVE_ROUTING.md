# Adaptive Hyper-RAG: Deterministic Query Complexity Routing
### Adaptive Selection Between Hyper-Lite and Hyper-Core

---

## 1. Overview

Adaptive Hyper-RAG introduces a deterministic routing layer positioned above the existing Hyper-Lite and Hyper-Core retrieval pipelines.

### The Original Problem
In the original Hyper-RAG implementation, every query must manually specify a static retrieval mode:
```text
All queries manually specify a retrieval mode
```
This forces developers and applications into a rigid trade-off:
- Forcing **Hyper-Core** on all queries introduces unnecessary graph diffusion and high-order hyperedge processing for simple, single-entity factual lookups.
- Forcing **Hyper-Lite** on all queries strips away higher-order relationship structures, causing complex, multi-entity, comparative, or causal queries to lack contextual connectivity.

### The Adaptive Solution
Adaptive Hyper-RAG addresses this limitation by dynamically evaluating the syntactic, structural, and semantic complexity of incoming queries before retrieval:
```text
User Query
    ↓
Query Complexity Analysis
    ↓
Complexity Score
    ↓
Lite / Core
```

### Architectural Principles
- **Local Execution**: The routing evaluation runs entirely in-process using deterministic rule-based algorithms.
- **Zero LLM Overhead**: No LLM call is made to score query complexity or decide routing.
- **No Additional API Costs or Latency**: Query routing incurs zero external network latency and zero API tokens.
- **Pipeline Preservation**: The router does not alter, replace, or redesign existing Hyper-Lite or Hyper-Core retrieval algorithms.
- **Path Selection**: It solely selects which existing execution path will handle the query.

---

## 2. Architecture

```text
User Query
    |
    v
Adaptive Query Router
    |
    v
Query Feature Extraction
    |
    v
Heuristic Complexity Scoring
    |
    v
0–100 Complexity Score
    |
    +-------------------------+
    |                         |
 score < threshold       score >= threshold
    |                         |
    v                         v
Hyper-Lite                 Hyper-Core
    |                         |
    +-------------+-----------+
                  |
                  v
              Reasoning
                  |
                  v
                Answer
```

### Execution Stages

1. **User Query**: The input question string is submitted to Hyper-RAG with `param=QueryParam(mode="adaptive")`.
2. **Adaptive Query Router**: The routing coordinator inspects configuration (`ADAPTIVE_RAG_ENABLED`, `ADAPTIVE_CORE_THRESHOLD`) and triggers query evaluation.
3. **Query Feature Extraction**: The query is normalized and scanned for 12 structural and semantic complexity signals across 8 feature categories.
4. **Heuristic Complexity Scoring**: Detected features are mapped to transparent, additive point allocations.
5. **0–100 Complexity Score**: Point values are bounded and normalized into a final integer score between `0` and `100`.
6. **Threshold Comparison**: The score is compared against `ADAPTIVE_CORE_THRESHOLD` (default: `60`):
   - **Score < Threshold**: Routes execution to **Hyper-Lite** (entity-focused lightweight vector retrieval).
   - **Score $\ge$ Threshold**: Routes execution to **Hyper-Core** (full hypergraph community and hyperedge retrieval).
7. **Existing Reasoning**: The selected retrieval pipeline populates its context and invokes the configured LLM reasoning engine.
8. **Answer**: The final generated response is returned alongside structured decision metadata.

---

## 3. File-Level Implementation

| File Path | Component / Function | Responsibility |
| :--- | :--- | :--- |
| `hyperrag/adaptive_router.py` | `QueryComplexityAnalyzer` | Protocol / interface defining complexity analysis contracts. |
| | `QueryFeatureExtractor` | Extracts structural, entity, and semantic features from input strings using regex and token heuristics. |
| | `QueryFeatures` | Dataclass holding detected boolean flags (comparison, causal, multi-hop, etc.) and discrete counts (entities, aspects). |
| | `BaseComplexityScorer` | Abstract base class defining scoring interfaces. |
| | `HeuristicComplexityScorer` | Implements additive, bounded $0-100$ heuristic scoring logic. |
| | `ComplexityWeights` | Dataclass encapsulating all point allocations, multipliers, and threshold values. |
| | `AdaptiveDecision` | Dataclass encapsulating decision output (`mode`, `score`, `threshold`, `confidence`, `features`, `reasons`). |
| | `AdaptiveRouter` | Public coordinator orchestrating extraction, scoring, decision generation, and logging. |
| `hyperrag/hyperrag.py` | `_resolve_query_mode()` | Resolves effective execution mode (`hyper` vs `hyper-lite`). Preserves manual `core` and `lite` overrides; invokes `AdaptiveRouter` when `mode="adaptive"`. |
| `hyperrag/base.py` | `QueryParam` | Defines query parameters including supported modes (`"adaptive"`, `"core"`, `"lite"`, etc.) and stores `adaptive_decision`. |
| `my_config.py` | Configuration Definitions | Defines environment mappings: `ADAPTIVE_RAG_ENABLED`, `ADAPTIVE_RAG_MODE`, `ADAPTIVE_CORE_THRESHOLD`, `ADAPTIVE_LOG_DECISIONS`. |
| `.env.example` | Environment Variables | Documents default variables, recommended thresholds, and logging toggles for deployments. |
| `config_temp.py` | Configuration Template | Provides configuration support and fallback definitions. |
| `service_api.py` | FastAPI Service Layer | Validates incoming modes (`adaptive`, `core`, `lite`, etc.) and returns structured `adaptive_decision` metadata in `QueryResponse`. |
| `test_adaptive_router.py` | Test Suite | Isolated unit tests validating Phase 1 & 2.1 complexity dimensions, boundary conditions, and short-query semantic density. |
| `test_retrieval_sufficiency.py` | Test Suite | Isolated unit tests validating Phase 2 retrieval sufficiency evaluation, scoring formulas, and escalation policies. |
| `test_key_rotation.py` | Test Suite | Isolated unit tests validating multi-key pool rotation, 429 backoff, 401 handling, embedding isolation, and concurrency. |
| `test_config.py` | Test Suite | Validates configuration loading, environment parsing, and key initialization. |
| `README.md` | User-Facing Documentation | Provides setup instructions, architecture descriptions, and user guidance for adaptive routing. |

---

## 4. Query Feature Extraction

Features are extracted using regex patterns and lightweight token analysis, organized into the following categories:

### A. Multi-Aspect
Detects queries asking for multiple distinct attributes, categories, or lists.
- **Triggers**: Conjunctions (`and`, `as well as`, `including`), comma-separated clause enumerations.
- **Aspect Counter**: Identifies question aspects such as `causes`, `symptoms`, `treatment`, `prevention`, `pros and cons`, `advantages and disadvantages`.

### B. Comparison
Identifies queries demanding comparative analysis between two or more subjects.
- **Triggers**: `compare`, `comparison`, `versus`, `vs.`, `difference between`, `differ from`, `in contrast to`, `relative to`.

### C. Causal / Explanatory
Identifies queries investigating underlying mechanisms, cause-and-effect relationships, or functional outcomes.
- **Triggers**: `why`, `how does`, `how do`, `causes`, `cause of`, `effect of`, `impact of`, `mechanism`, `leads to`, `contribute to`, `result in`.

### D. Temporal
Detects chronological, evolutionary, or time-series inquiries.
- **Triggers**: `over time`, `timeline`, `historically`, `evolution`, `progression`, `trends`, year ranges (e.g., `2010-2020`), century references.

### E. Multi-Hop
Detects requirements to traverse relational chains across multiple entities.
- **Triggers**: `relationship between`, `connection between`, `how A affects B through C`, `associated with`, `pathway`, `link between`, `interplay between`.

### F. Aggregation / Synthesis
Detects requests to synthesize or exhaustively enumerate information across the knowledge base.
- **Triggers**: `summarize all`, `list all`, `overview of all`, `across multiple`, `synthesize`, `aggregate`, `comprehensive review`.

### G. Entity Estimation
Performs fast, dependency-free entity estimation.
- **Implementation Note**: Does **NOT** use heavyweight NLP/NER libraries (such as spaCy or Stanza).
- **Mechanism**:
  1. Quoted terms (e.g., `"Type 1 Diabetes"`).
  2. Capitalized proper-noun sequences (e.g., `Alzheimer's Disease`).
  3. Stopword-filtered content noun chunks extracted via regex pattern matching.

### H. Requested Depth
Detects explicit user instructions demanding exhaustive or granular explanations.
- **Triggers**: `detailed`, `in-depth`, `exhaustive`, `step by step`, `thorough`, `comprehensive`, `elaborate`.

### I. Structural Signals
Captures query syntax complexity to calibrate scoring:
- **Word count**: Total tokens in the query.
- **Query length**: Total character length.
- **Sentence count**: Number of sentences separated by punctuation.
- **Question marks**: Multi-part question markers.
*(Note: Structural signals serve strictly as secondary supporting signals and never determine the routing decision alone).*

---

## 5. Scoring System

Complexity is calculated additively and bounded between `0` and `100`:

```text
Score = min(
    100,
    max(
        0,
        StructuralPts
        + EntityPts
        + AspectPts
        + Σ SemanticFeaturePts
    )
)
```

### Exact Default Weights

#### Semantic Feature Weights
```text
Comparison:             +20 pts
Causal / Explanatory:   +15 pts
Temporal:               +15 pts
Multi-Hop:              +15 pts
Aggregation:            +15 pts
Requested Depth:        +12 pts
Relationship Reasoning: +10 pts
```

#### Entity Count Weights
```text
1 entity:                +5 pts
2 entities:             +10 pts
3 entities:             +15 pts
4+ entities:            +20 pts
```

#### Multi-Aspect Weights
```text
2 aspects:               +8 pts
3 aspects:              +12 pts
4+ aspects:             +16 pts
```

#### Structural Weights
```text
Word count:      min(10.0, word_count × 0.35)
Sentence count:  min(6.0, (sentence_count - 1) × 3.0)
Question marks:  min(4.0, (question_count - 1) × 2.0)
```

---

## 6. Threshold

```python
DEFAULT_CORE_THRESHOLD = 60
```

### Decision Rule
- **Score < 60**: Routes to **Hyper-Lite**.
- **Score $\ge$ 60**: Routes to **Hyper-Core**.

### Configuration Philosophy
The threshold `60` serves as an initial, configurable reference baseline. It separates simple factual, definitional, and single-relation queries from complex, multi-entity, comparative, or multi-hop inquiries. It is exposed as a configuration parameter so that administrators can calibrate sensitivity to domain requirements.

---

## 7. Configuration

Configured via environment variables or `.env`:

```env
# Master enable switch for adaptive routing
ADAPTIVE_RAG_ENABLED=true

# Default query mode when none is specified (adaptive, core, lite)
ADAPTIVE_RAG_MODE=adaptive

# Complexity threshold separating Lite (< 60) and Core (>= 60)
ADAPTIVE_CORE_THRESHOLD=60

# Enable diagnostic decision logging
ADAPTIVE_LOG_DECISIONS=true

# Phase 2.1: Short-Query Semantic Density
ADAPTIVE_SHORT_QUERY_MAX_WORDS=7
ADAPTIVE_SHORT_QUERY_DENSITY_BONUS=15.0
```

### Configuration Behaviors
- `ADAPTIVE_RAG_ENABLED=false`: Disables the router completely. All queries default to standard Hyper-Core (`hyper`) execution.
- `ADAPTIVE_RAG_MODE`: Governs default query behavior when `param.mode` is omitted in client requests.
- `ADAPTIVE_CORE_THRESHOLD`: Configures the integer boundary ($0-100$) between Lite and Core.
- `ADAPTIVE_LOG_DECISIONS`: Toggles human-readable terminal logs detailing score breakdowns and selected modes.
- `ADAPTIVE_SHORT_QUERY_MAX_WORDS`: Max words (default: 7) defining a short query for semantic density detection.
- `ADAPTIVE_SHORT_QUERY_DENSITY_BONUS`: Additive score bonus (default: 15.0) awarded to short queries with high-order relational signals.

---

## 7.1 Phase 2.1: Short-Query Semantic-Density Refinement

### Purpose & Benchmark Motivation
The 39-query benchmark exposed a category of short queries with strong relational depth (e.g., Q32: *"How did greed cause Marley's chains?"*, Q33: *"Compare Fred vs Scrooge"*) that received low complexity scores (47 and 51) strictly due to brief token length. Although rescued by Phase 2 retrieval sufficiency escalation, routing them to Lite first caused redundant retrieval passes and elevated latency.

Phase 2.1 refines the Phase 1 complexity router to recognize **dense short queries** upfront.

### Activation Criteria
A query receives the semantic-density bonus if and only if:
1. `word_count <= ADAPTIVE_SHORT_QUERY_MAX_WORDS` (7 words)
2. `features.comparison == True` OR `features.causal_reasoning == True`

### Observable Score Accounting
```text
Final Score = Base Score + Short-Query Density Bonus
```

- **Q32 ("How did greed cause Marley's chains?")**: Base `47` + Bonus `15` = **62** $\rightarrow$ **Core**
- **Q33 ("Compare Fred vs Scrooge")**: Base `51` + Bonus `15` = **66** $\rightarrow$ **Core**
- **Factual Short ("What is Scrooge?")**: Base `6` + Bonus `0` = **6** $\rightarrow$ **Lite** (Remains Lite)

---

## 8. Manual vs. Adaptive Modes

Manual and adaptive modes are configured through `QueryParam`:

```python
QueryParam(mode="lite")      # Forces Hyper-Lite; bypasses router
QueryParam(mode="core")      # Forces Hyper-Core; bypasses router
QueryParam(mode="adaptive")  # Executes Adaptive Router
```

### Behavioral Guarantees
- **`mode="lite"`**: Completely bypasses the router and executes lightweight vector retrieval.
- **`mode="core"`**: Completely bypasses the router and executes hypergraph retrieval.
- **`mode="adaptive"`**: Analyzes the query, computes the complexity score, and delegates to either Lite or Core based on the configured threshold.

---

## 9. Code Examples

### Example 1: Simple Factual Query (Routes to Lite)
```python
from hyperrag import HyperRAG, QueryParam

rag = HyperRAG(working_dir="./workspace")

# Simple definitional query: score = 6 (< 60) -> Executes Hyper-Lite
response = rag.query(
    "What is diabetes?",
    param=QueryParam(mode="adaptive")
)
```

### Example 2: Multi-Aspect Comparative Query (Routes to Core)
```python
# Comparative, multi-entity, multi-aspect query: score = 86 (>= 60) -> Executes Hyper-Core
response = rag.query(
    "Compare diabetes and hypertension in terms of causes, symptoms, and treatment.",
    param=QueryParam(mode="adaptive")
)
```

### Example 3: Manual Override (Bypasses Router)
```python
# Force Hyper-Core regardless of query simplicity
response = rag.query(
    "What is diabetes?",
    param=QueryParam(mode="core")
)
```

### Example 4: Direct Query Inspection
```python
from hyperrag import AdaptiveRouter

router = AdaptiveRouter()

# Inspect query features, points, and reasons without executing retrieval
decision = router.inspect_query(
    "Compare diabetes and hypertension in terms of causes and treatment."
)

print(decision)
```

---

## 10. Routing Decision Metadata

Every adaptive query records decision metadata on the `HyperRAG` instance:

```python
decision = rag.last_adaptive_decision
```

### Available Metadata Fields
- `mode`: Selected execution mode (`"lite"` or `"core"`).
- `score`: Computed complexity score ($0-100$).
- `threshold`: Threshold value used for the evaluation.
- `confidence`: Normalized confidence score ($0.0 - 1.0$).
- `features`: Dictionary of extracted feature flags and entity counts.
- `reasons`: List of human-readable rationale strings.

### Example Structured Output
```json
{
  "mode": "core",
  "score": 86,
  "threshold": 60,
  "confidence": 0.86,
  "features": {
    "word_count": 10,
    "char_length": 69,
    "sentence_count": 1,
    "question_count": 1,
    "has_comparison": true,
    "has_causal": true,
    "has_temporal": false,
    "has_multi_hop": true,
    "has_aggregation": false,
    "has_depth_request": false,
    "has_relational_reasoning": true,
    "num_aspects": 3,
    "entity_count": 5
  },
  "reasons": [
    "multiple entities (5 detected)",
    "multiple requested aspects (3 aspects)",
    "comparison detected",
    "causal reasoning detected",
    "multi-hop structure detected",
    "relationship reasoning detected"
  ]
}
```

---

## 11. Test Results

The deterministic router has been verified using the isolated test suite in `test_adaptive_router.py`:

| Test Query | Complexity Score | Selected Mode | Evaluated Traits |
| :--- | :---: | :---: | :--- |
| `"What is diabetes?"` | **6** | **Lite** | Single entity, direct definition |
| `"What is a neural network?"` | **7** | **Lite** | Single concept definition |
| `"What are the causes, symptoms, treatment, and prevention of diabetes?"` | **64** | **Core** | Multi-aspect (4 aspects), high scope |
| `"Compare diabetes and hypertension in terms of causes, symptoms, and treatment."` | **86** | **Core** | Comparison, 5 entities, 3 aspects, causal |
| `"How does diabetes contribute to kidney disease?"` | **35** | **Elevated** | Causal trigger detected; elevated over simple definition |
| `"How has the disease progressed over the last decade?"` | **32** | **Elevated** | Temporal trigger detected; elevated over simple definition |
| `"Explain the connection between obesity and insulin resistance."` | **54** | **Elevated** | Multi-hop relational phrasing detected |
| `"Can you please explain to me what diabetes is in very simple terms?"` | **19** | **Lite** | High word count, low semantic complexity |

### Verified Guarantees
- Manual mode `mode="lite"` executes Lite and leaves `last_adaptive_decision=None`.
- Manual mode `mode="core"` executes Core and leaves `last_adaptive_decision=None`.
- Adaptive mode `mode="adaptive"` dynamically assigns Lite or Core based on score.

---

## 12. Invariants

The Phase 1 routing implementation strictly adheres to the following system invariants:
1. **Zero LLM Calls for Routing**: All complexity scoring is performed via local heuristic algorithms.
2. **OpenRouter is the Only LLM Provider**: Primary LLM operations strictly use OpenRouter (`nvidia/nemotron-3-ultra-550b-a55b:free`).
3. **Mistral is Embeddings-Only**: Mistral is exclusively used for embedding generation (`mistral-embed`).
4. **Embedding Dimensions Preserved**: Embedding vectors maintain their required 1024-dimension contract.
5. **No LLM Fallbacks**: No OpenRouter $\rightarrow$ Mistral LLM fallback paths exist.
6. **No Full Dataset Execution**: Validation was performed using isolated, controlled unit test cases.

---

## 13. Limitations

1. **Heuristic Entity Extraction**: Entity counts are estimated via regex, capitalization, and stopword patterns rather than a full statistical NER parser.
2. **Domain-Specific Vocabulary**: Uncapitalized medical or domain-specific terminology may not be recognized as distinct entities without quotes.
3. **Configurable Threshold**: The default threshold of `60` is an empirical reference baseline, not a scientifically optimized value for all datasets.
4. **Complexity $\ne$ Retrieval Sufficiency**: High structural simplicity does not guarantee that Lite retrieval will find sufficient evidence in the database.
5. **No Retrospective Lite $\rightarrow$ Core Escalation in Phase 1**: Decisions are strictly made pre-retrieval; if Lite produces zero results, Phase 1 does not dynamically escalate to Core.
6. **No Answer Validation**: Phase 1 includes no self-evaluation or critique of generated responses.

---

## 14. Future Roadmap

The Adaptive Hyper-RAG roadmap consists of the following distinct phases:

### Phase 2: Retrieval Sufficiency & Lite $\rightarrow$ Core Escalation
- Post-retrieval inspection of retrieved contexts (item count, context length, entity coverage).
- Automatic escalation from Hyper-Lite to Hyper-Core if retrieved evidence is insufficient or empty.

### Phase 3: Answer Validation
- Quality and completeness checking of the synthesized response.
- Hallucination detection and citation verification.

### Phase 4: Self-Repair & Iterative Querying
- Re-querying and context replenishment for unfulfilled aspects.
- Feedback loops for answer refinement.

*(Note: Phases 2, 3, and 4 represent future architecture and are not part of the Phase 1 routing layer).*

---

## 15. Documentation Quality & Maintainer Guidance

- **Code Symbol Alignment**: All class, method, and variable names in this document match the codebase implementation.
- **Reproducibility**: Router behavior can be verified at any time by running:
  ```bash
  python test_adaptive_router.py
  ```
- **Extensibility**: Custom feature extractors or scoring formulas can be added by implementing subclasses of `BaseComplexityScorer` in `hyperrag/adaptive_router.py`.
