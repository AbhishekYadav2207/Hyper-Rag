# API Reference

This document provides complete reference documentation for Hyper-RAG's public Python classes, functions, and REST API endpoints.

---

## 1. Python Public API

### `HyperRAG` Class
Defined in [`hyperrag/hyperrag.py`](file:///d:/Rag/Hyper-RAG/hyperrag/hyperrag.py#L32).

#### Constructor
```python
HyperRAG(
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

#### Core Methods
```python
def query(self, query: str, param: QueryParam = QueryParam()) -> str:
    """Synchronous entrypoint for querying HyperRAG."""

async def aquery(self, query: str, param: QueryParam = QueryParam()) -> str:
    """Asynchronous entrypoint for querying HyperRAG."""

async def astream_query(self, query: str, param: QueryParam = QueryParam()) -> AsyncGenerator[str, None]:
    """Asynchronous generator yielding streamed answer tokens."""

def insert(self, string_or_strings: Union[str, List[str]]) -> None:
    """Synchronous document ingestion."""

async def ainsert(self, string_or_strings: Union[str, List[str]]) -> None:
    """Asynchronous document ingestion."""
```

#### Key Attributes
- `last_adaptive_decision`: Holds the [`AdaptiveDecision`](file:///d:/Rag/Hyper-RAG/hyperrag/adaptive_router.py#L37) object from the most recent adaptive query, or `None` if manual mode was used.

---

### `QueryParam` Dataclass
Defined in [`hyperrag/base.py`](file:///d:/Rag/Hyper-RAG/hyperrag/base.py#L15).

```python
@dataclass
class QueryParam:
    mode: Literal[
        "adaptive", "hyper", "core", "hyper-lite", "lite", "graph", "naive", "llm", "hyper-query"
    ] = "adaptive"
    only_need_context: bool = False
    response_type: str = "Multiple Paragraphs"
    top_k: int = 60
    max_token_for_text_unit: int = 1600
    max_token_for_entity_context: int = 300
    max_token_for_relation_context: int = 1600
    return_type: Literal["json", "text"] = "text"
    adaptive_decision: Optional[Any] = None
```

---

### `AdaptiveRouter` Class
Defined in [`hyperrag/adaptive_router.py`](file:///d:/Rag/Hyper-RAG/hyperrag/adaptive_router.py#L248).

```python
class AdaptiveRouter:
    def __init__(
        self,
        weights: Optional[ComplexityWeights] = None,
        core_threshold: int = 60,
        log_decisions: bool = True
    )

    def route(self, query: str) -> AdaptiveDecision:
        """Evaluates complexity and returns an AdaptiveDecision."""

    def inspect_query(self, query: str) -> str:
        """Returns a formatted human-readable diagnostic report."""
```

---

### `RetrievalSufficiencyEvaluator` Class
Defined in [`hyperrag/retrieval_sufficiency.py`](file:///d:/Rag/Hyper-RAG/hyperrag/retrieval_sufficiency.py#L65).

```python
class RetrievalSufficiencyEvaluator:
    def __init__(
        self,
        weights: Optional[SufficiencyWeights] = None,
        threshold: float = 60.0,
        log_evaluations: bool = True
    )

    def evaluate(
        self,
        query: str,
        retrieval_context: Union[str, Dict[str, Any]],
        features: Optional[Dict[str, Any]] = None,
        complexity_score: int = 0
    ) -> RetrievalSufficiency:
        """Assesses retrieval evidence and produces a sufficiency verdict."""
```

---

### Low-Level Pipeline Functions
Defined in [`hyperrag/operate.py`](file:///d:/Rag/Hyper-RAG/hyperrag/operate.py).

```python
async def hyper_retrieve_lite(
    query: str,
    chunk_entity_relation_graph: ChunkEntityRelationHypergraph,
    entities_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    global_config: dict
) -> Tuple[str, List[str]]:
    """Performs keyword extraction and entity retrieval without LLM reasoning."""

async def hyper_query_lite_reasoning(
    query: str,
    context: str,
    query_param: QueryParam,
    global_config: dict
) -> str:
    """Executes LLM answer reasoning using pre-retrieved context."""

async def hyper_query(
    query: str,
    chunk_entity_relation_graph: ChunkEntityRelationHypergraph,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    global_config: dict
) -> str:
    """Executes high-order hypergraph traversal, diffusion, and LLM reasoning."""
```

---

## 2. REST API Reference (FastAPI)

Defined in [`service_api.py`](file:///d:/Rag/Hyper-RAG/service_api.py).

### `POST /query`
Performs a standard (non-streaming) query.

#### Request Body (`QueryRequest`)
```json
{
  "question": "What is diabetes?",
  "mode": "adaptive"
}
```
- `question` (*string, required*): Query string (1 to 6000 characters).
- `mode` (*string, optional*): Override mode (`adaptive`, `core`, `lite`, `naive`, `llm`). Defaults to server configuration.

#### Response Body (`QueryResponse`)
```json
{
  "answer": "Diabetes is a chronic metabolic disease...",
  "mode": "adaptive",
  "latency_ms": 1420,
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
    "features": { ... },
    "retrieval_metrics": { ... }
  }
}
```

---

### `POST /query_stream`
Streams answer tokens using Server-Sent Events (SSE).

#### Request Body
Identical to `POST /query`.

#### Response
Content-Type: `text/event-stream`

```text
data: {"token": "Diabetes"}

data: {"token": " is"}

data: {"token": " a"}

data: [DONE]
```

---

### `GET /healthz`
Health check and deployment status.

#### Response
```json
{
  "status": "ok",
  "data_name": "default",
  "mode": "adaptive",
  "working_dir": "./hyper_rag_cache",
  "api_key_required": false
}
```
