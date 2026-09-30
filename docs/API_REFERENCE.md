# Hyper-RAG Complete API Reference

This document provides complete reference documentation for both the **Python SDK** and the **HTTP REST APIs** across Hyper-RAG.

---

## 1. Python Public API

### 1.1 `HyperRAG` Class
Defined in [`hyperrag/hyperrag.py`](file:///d:/Rag/Hyper-RAG/hyperrag/hyperrag.py#L32).

#### Constructor
```python
from hyperrag import HyperRAG
from hyperrag.utils import EmbeddingFunc

rag = HyperRAG(
    working_dir: str = "./hyper_rag_cache",
    llm_model_func: Callable = None,
    llm_model_stream_func: Optional[Callable] = None,
    embedding_func: Optional[EmbeddingFunc] = None,
    chunk_token_size: int = 1200,
    chunk_overlap_token_size: int = 100,
    entity_extract_max_gleaning: int = 1,
    entity_summary_to_max_tokens: int = 500,
    **kwargs
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `working_dir` | `str` | `"./hyper_rag_cache"` | Directory storing KV caches, vector indices, and hypergraph DB. |
| `llm_model_func` | `Callable` | *Required* | Asynchronous function taking prompts and returning complete string completions. |
| `llm_model_stream_func`| `Callable` | *Optional* | Asynchronous generator yielding streaming tokens. |
| `embedding_func` | `EmbeddingFunc` | *Required* | Wrapper specifying embedding dimension (1024), max tokens (8192), and async batch embed function. |
| `chunk_token_size` | `int` | `1200` | Target token length for text passage chunks. |
| `chunk_overlap_token_size` | `int` | `100` | Token overlap between consecutive chunks. |

#### Methods

##### `aquery(query: str, param: QueryParam = QueryParam()) -> str`
Asynchronous primary query entrypoint.
- **Parameters**:
  - `query` (*str*): Natural language question.
  - `param` (*QueryParam*): Query parameters (defaults to `mode="adaptive"`).
- **Returns**: Formatted answer string.

##### `astream_query(query: str, param: QueryParam = QueryParam()) -> AsyncGenerator[str, None]`
Asynchronous generator streaming answer tokens in real time.

##### `query(query: str, param: QueryParam = QueryParam()) -> str`
Synchronous convenience wrapper around `aquery`.

##### `ainsert(string_or_strings: Union[str, List[str]]) -> None`
Asynchronous document ingestion. Chunks text, extracts entities and hyperedges, computes embeddings, and commits to storage.

##### `insert(string_or_strings: Union[str, List[str]]) -> None`
Synchronous convenience wrapper around `ainsert`.

#### Lifecycle Attributes
- `rag.last_adaptive_decision`: Contains the [`AdaptiveDecision`](#13-adaptivedecision-schema) object from the latest query, or `None` if non-adaptive mode was used.
- `rag.last_validation_result`: Contains the [`ValidationResult`](#15-validationresult-schema) object from Phase 3 response validation.
- `rag.last_language_result`: Contains language guard compliance results.

---

### 1.2 `QueryParam` Dataclass
Defined in [`hyperrag/base.py`](file:///d:/Rag/Hyper-RAG/hyperrag/base.py#L15).

```python
from hyperrag import QueryParam

param = QueryParam(
    mode="adaptive",
    response_type="Multiple Paragraphs",
    top_k=60
)
```

| Field | Type | Default | Permitted Values / Description |
|---|---|---|---|
| `mode` | `str` | `"adaptive"` | `"adaptive"`, `"hyper"`, `"core"`, `"hyper-lite"`, `"lite"`, `"naive"`, `"llm"` |
| `only_need_context` | `bool` | `False` | If `True`, returns assembled context without calling LLM reasoning. |
| `response_type` | `str` | `"Multiple Paragraphs"` | Prompt formatting directive (e.g., `"Multiple Paragraphs"`, `"Bullet Points"`). |
| `top_k` | `int` | `60` | Number of top vector matches retrieved. |
| `max_token_for_text_unit` | `int` | `1600` | Maximum token budget for passage chunks. |
| `max_token_for_entity_context` | `int` | `300` | Maximum token budget for entity descriptions. |
| `max_token_for_relation_context`| `int` | `1600` | Maximum token budget for hyperedges. |
| `return_type` | `str` | `"text"` | `"text"` returns raw answer; `"json"` returns answer with metadata dict. |

---

### 1.3 `AdaptiveDecision` Schema
Defined in [`hyperrag/adaptive_router.py`](file:///d:/Rag/Hyper-RAG/hyperrag/adaptive_router.py#L37).

```python
@dataclass
class AdaptiveDecision:
    mode: str                          # Effective execution mode ("lite" or "core")
    score: int                         # Final complexity score (0-100)
    threshold: int                     # Target threshold (default: 60)
    confidence: float                  # Bounded confidence metric (0.0 - 1.0)
    features: Dict[str, Any]           # Extracted signals (comparison, causal, entities)
    reasons: List[str]                 # Human-readable decision reasons
    initial_mode: Optional[str]        # Mode assigned in Phase 1
    initial_complexity_score: Optional[int] # Score before retrieval
    retrieval_sufficiency_score: Optional[float] # Phase 2 sufficiency score
    retrieval_sufficient: Optional[bool] # True if Lite retrieval met threshold
    final_mode: Optional[str]          # Final mode after escalation evaluation
    escalated: bool = False            # True if escalated from Lite to Core
    escalation_reason: Optional[str]   # Explanation of why escalation occurred
    retrieval_metrics: Optional[Dict[str, Any]] # Raw retrieval statistics
```

---

### 1.4 `AdaptiveRouter` Class
Defined in [`hyperrag/adaptive_router.py`](file:///d:/Rag/Hyper-RAG/hyperrag/adaptive_router.py#L248).

```python
from hyperrag import AdaptiveRouter, ComplexityWeights

router = AdaptiveRouter(
    weights=ComplexityWeights(core_threshold=60),
    core_threshold=60,
    log_decisions=True
)

decision = router.route("Compare Fred and Scrooge")
print(decision.mode)  # "core"
```

---

### 1.5 `ValidationResult` Schema
Defined in [`hyperrag/response_validator.py`](file:///d:/Rag/Hyper-RAG/hyperrag/response_validator.py).

```python
@dataclass
class ValidationResult:
    valid: bool                        # True if overall score >= threshold & no hard failures
    score: float                       # Weighted overall score (0.0 - 100.0)
    completeness_score: float          # Dimension 1 score (0.0 - 100.0)
    evidence_score: float              # Dimension 2 score (0.0 - 100.0)
    relevance_score: float             # Dimension 3 score (0.0 - 100.0)
    missing_aspects: List[str]         # Identified unanswered query dimensions
    unsupported_claims: List[str]      # Claims lacking grounding in retrieved context
    reasons: List[str]                 # Explanatory diagnosis notes
    metrics: Dict[str, Any]            # Claim counts, overlap stats
```

---

## 2. Standalone Service REST API (`service_api.py`)

A production-ready microservice server listening by default on port `8002`.

### `GET /healthz`
Health check and deployment status.
- **Request**: `GET http://127.0.0.1:8002/healthz`
- **Response**: `200 OK`
```json
{
  "status": "ok",
  "data_name": "pathology",
  "mode": "hyper",
  "working_dir": "d:\\Rag\\Hyper-RAG\\caches\\pathology",
  "api_key_required": false
}
```

---

### `POST /query`
Executes a synchronous query and returns the answer with full adaptive decision and validation metadata.

- **Request**: `POST http://127.0.0.1:8002/query`
- **Headers**:
  - `Content-Type: application/json`
  - `X-API-Key: <secret>` *(Optional; required if `HYPERRAG_API_KEY` is configured)*
- **Body**:
```json
{
  "question": "What is diabetes?",
  "mode": "adaptive"
}
```
- **Response**: `200 OK`
```json
{
  "answer": "Diabetes is a chronic metabolic disease characterized by elevated levels of blood glucose...",
  "mode": "adaptive",
  "latency_ms": 1240,
  "adaptive_decision": {
    "mode": "lite",
    "score": 6,
    "threshold": 60,
    "confidence": 0.06,
    "initial_mode": "lite",
    "initial_complexity_score": 6,
    "retrieval_sufficiency_score": 65.0,
    "retrieval_sufficient": true,
    "final_mode": "lite",
    "escalated": false,
    "escalation_reason": null,
    "features": {
      "has_comparison": false,
      "has_causal": false,
      "has_multi_hop": false,
      "entity_count": 1
    },
    "retrieval_metrics": {
      "num_items": 3,
      "num_unique_entities": 1,
      "context_length": 820,
      "query_entity_coverage": 1.0,
      "duplicate_ratio": 0.0,
      "num_hyperedges": 0
    }
  },
  "validation": {
    "valid": true,
    "score": 88.0,
    "completeness_score": 90.0,
    "evidence_score": 85.0,
    "relevance_score": 90.0,
    "missing_aspects": [],
    "unsupported_claims": [],
    "reasons": ["All requested aspects addressed", "Major claims supported by retrieved context"]
  },
  "language_guard": {
    "passed": true,
    "contains_non_latin": false,
    "script": "latin"
  }
}
```

---

### `POST /query_stream`
Streams answer tokens in real time via Server-Sent Events (SSE).

- **Request**: `POST http://127.0.0.1:8002/query_stream`
- **Body**: Identical to `/query`.
- **Response**: `200 OK` (`Content-Type: text/plain; charset=utf-8`)
```text
Diabetes is a chronic disease...
```

---

## 3. Web UI Backend REST API (`web-ui/backend/main.py`)

Full-stack backend server listening by default on port `8000`.

### Summary Endpoint Table

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Root health check and system information |
| `GET` | `/databases` | List all available knowledge hypergraph databases |
| `GET` | `/settings` | Retrieve active model configurations and parameters |
| `POST` | `/settings` | Update runtime model configurations |
| `POST` | `/test-api` | Test upstream OpenRouter API connectivity |
| `POST` | `/test-database` | Test hypergraph database connectivity |
| `POST` | `/process_message` | Main chat conversation endpoint with Adaptive RAG |
| `POST` | `/hyperrag/query` | Direct query endpoint |
| `POST` | `/hyperrag/query_stream` | Direct streaming query endpoint |
| `POST` | `/hyperrag/insert` | Ingest raw text directly into knowledge base |
| `GET` | `/hyperrag/status` | Engine availability status (`{"available": true}`) |
| `DELETE`| `/hyperrag/reset` | Wipe active database cache |
| `GET` | `/files` | List uploaded documents and embedding status |
| `POST` | `/files/upload` | Multipart file upload (`.txt`, `.pdf`, `.docx`, `.md`) |
| `DELETE`| `/files/{file_id}` | Remove an uploaded document |
| `POST` | `/files/embed` | Trigger document ingestion and hypergraph building |
| `POST` | `/files/embed-with-progress`| Ingestion with real-time WebSocket progress |
| `WS` | `/ws` | WebSocket connection for real-time progress events |
| `GET` | `/db` | Summary stats of vertices and hyperedges |
| `GET` | `/db/vertices` | Paginated list of vertices (entities) |
| `GET` | `/db/hyperedges` | Paginated list of high-order hyperedges |
| `GET` | `/db/vertices/{id}` | Inspect specific vertex by ID |
| `GET` | `/db/hyperedges/{id}` | Inspect specific hyperedge by ID |
| `GET` | `/db/vertices_neighbor/{id}` | Immediate neighbor vertices of an entity |
| `GET` | `/db/hyperedge_neighbor/{id}` | Hyperedges incident to an entity |

---

### Key Web UI Endpoints in Detail

#### `POST /process_message`
Primary chat endpoint utilized by the Web UI Chat view (`/#/Chat`).
- **Body**:
```json
{
  "message": "Compare Scrooge and Fred",
  "database": "default",
  "mode": "adaptive",
  "stream": false
}
```
- **Response**: `200 OK`
```json
{
  "response": "Ebenezer Scrooge and his nephew Fred embody contrasting attitudes...",
  "citations": ["Scrooge & Marley Counting House", "Christmas Carol Stave 1"],
  "adaptive_decision": {
    "mode": "core",
    "score": 66,
    "threshold": 60,
    "final_mode": "core",
    "escalated": false
  },
  "validation": {
    "valid": true,
    "score": 86.4
  }
}
```

#### `POST /files/upload`
Uploads documents for knowledge base construction.
- **Request**: `multipart/form-data` with `file` payload.
- **Response**: `200 OK`
```json
{
  "file_id": "doc_1790791467",
  "filename": "clinical_guidelines.pdf",
  "size": 245800,
  "status": "uploaded"
}
```

#### `WebSocket /ws`
Establishes a WebSocket connection for receiving live embedding and extraction progress:
```javascript
const ws = new WebSocket("ws://localhost:8000/ws");
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.progress}% - ${data.message}`);
};
```
