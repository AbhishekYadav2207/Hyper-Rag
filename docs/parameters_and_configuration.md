# Parameters and Configuration Guide

This guide provides a comprehensive reference for all configuration parameters, environment variables, initialization options, and query parameters across Hyper-RAG.

---

## 1. Environment Variables & `.env`

Hyper-RAG reads configuration values from environment variables or a root `.env` file via `my_config.py`.

### Adaptive RAG Configuration

| Variable Name | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `ADAPTIVE_RAG_ENABLED` | `bool` | `true` | Master toggle for adaptive routing. If `false`, falls back directly to `hyper` (Core). |
| `ADAPTIVE_RAG_MODE` | `str` | `adaptive` | Default mode when client does not supply one (`adaptive`, `core`, `lite`). |
| `ADAPTIVE_CORE_THRESHOLD` | `int` | `60` | Pre-retrieval complexity threshold ($0-100$). Score $\ge 60$ routes to Core; $< 60$ routes to Lite. |
| `ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED`| `bool` | `true` | Enables Phase 2 post-retrieval sufficiency evaluation on Lite retrieval. |
| `ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD` | `float` | `60.0` | Sufficiency threshold ($0-100$). If Lite retrieval score $< 60.0$, escalates to Core. |
| `ADAPTIVE_LOG_DECISIONS` | `bool` | `true` | Logs detailed decision, scoring, and escalation diagnostics to the console and logger. |

### LLM Provider (OpenRouter ONLY)

| Variable Name | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `OPENROUTER_API_KEYS` | `str` | *None* | Comma-separated list of OpenRouter API keys used for round-robin rotation. |
| `OPENROUTER_API_KEY` | `str` | *None* | Single fallback key if `OPENROUTER_API_KEYS` is omitted. |
| `OPENROUTER_BASE_URL` | `str` | `https://openrouter.ai/api/v1` | OpenRouter OpenAI-compatible endpoint. |
| `OPENROUTER_MODEL` | `str` | `nvidia/nemotron-3-ultra-550b-a55b:free` | Model identifier for non-streaming and streaming generation. |

### Embedding Provider (Mistral Embeddings ONLY)

| Variable Name | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `MISTRAL_API_KEYS` | `str` | *None* | Comma-separated list of Mistral API keys for rotation. |
| `MISTRAL_API_KEY` | `str` | *None* | Single fallback key if `MISTRAL_API_KEYS` is omitted. |
| `MISTRAL_BASE_URL` | `str` | `https://api.mistral.ai/v1` | Mistral API endpoint. |
| `MISTRAL_EMBEDDING_MODEL` | `str` | `mistral-embed` | Official Mistral embedding model. |
| `EMBEDDING_DIM` | `int` | `1024` | Required output embedding dimension for `mistral-embed`. |

### Server & Operational Parameters

| Variable Name | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `HOST` | `str` | `0.0.0.0` | Bind host for `service_api.py`. |
| `PORT` | `int` | `8002` | Bind port for `service_api.py`. |
| `WORKING_DIR` | `str` | `./hyper_rag_cache` | Filesystem cache path storing KV data, vector indices, and graph DBs. |
| `API_KEY` | `str` | *Optional* | If set, enforces client authentication via `X-API-Key` HTTP header. |
| `MAX_QPS` | `float` | `10.0` | Maximum queries per second per client IP address. |

---

## 2. `HyperRAG` Class Parameters

The primary interface class is instantiated in `hyperrag/hyperrag.py`:

```python
from hyperrag import HyperRAG
from hyperrag.utils import EmbeddingFunc

rag = HyperRAG(
    working_dir="./cache",
    llm_model_func=llm_func,
    llm_model_stream_func=llm_stream_func,
    embedding_func=EmbeddingFunc(
        embedding_dim=1024,
        max_token_size=8192,
        func=embed_func
    ),
    chunk_token_size=1200,
    chunk_overlap_token_size=100,
)
```

| Parameter | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `working_dir` | `str` | `./hyper_rag_cache` | Path for saving and loading indexed hypergraph and vector databases. |
| `llm_model_func` | `Callable` | *Required* | Asynchronous function taking prompts and returning complete string completions. |
| `llm_model_stream_func` | `Callable` | *Optional* | Asynchronous generator yielding streaming tokens. |
| `embedding_func` | `EmbeddingFunc` | *Required* | Wrapper specifying embedding dimension, maximum token size, and async batch embedding function. |
| `chunk_token_size` | `int` | `1200` | Target token length when chunking raw input text files. |
| `chunk_overlap_token_size`| `int` | `100` | Token overlap between consecutive chunks to preserve contextual boundaries. |
| `entity_extract_max_gleaning`| `int` | `1` | Number of gleaning extraction passes over chunks for missed entities. |
| `entity_summary_to_max_tokens`| `int` | `500` | Token limit when summarizing descriptions of individual entities. |

---

## 3. `QueryParam` Parameters

Defined in [`hyperrag/base.py`](file:///d:/Rag/Hyper-RAG/hyperrag/base.py#L15), `QueryParam` controls execution behavior for `rag.query()` and `rag.aquery()`:

```python
from hyperrag import QueryParam

param = QueryParam(
    mode="adaptive",
    top_k=60,
    response_type="Multiple Paragraphs"
)
```

| Field Name | Type | Default | Permitted Values / Description |
| :--- | :---: | :---: | :--- |
| `mode` | `str` | `"adaptive"` | Execution mode: `"adaptive"`, `"core"`, `"hyper"`, `"lite"`, `"hyper-lite"`, `"naive"`, `"llm"`. |
| `only_need_context` | `bool` | `False` | If `True`, returns the assembled context without executing LLM generation. |
| `response_type` | `str` | `"Multiple Paragraphs"` | Prompt instruction specifying formatting (e.g. `"Multiple Paragraphs"`, `"Bullet Points"`). |
| `top_k` | `int` | `60` | Number of top vector entities / hyperedges retrieved during search. |
| `max_token_for_text_unit` | `int` | `1600` | Maximum token budget allocated to retrieved passage chunks. |
| `max_token_for_entity_context`| `int` | `300` | Maximum token budget allocated to entity description context. |
| `max_token_for_relation_context`| `int` | `1600` | Maximum token budget allocated to hyperedge/relationship context. |
| `return_type` | `str` | `"text"` | Format of returned response (`"text"` or `"json"`). |
| `adaptive_decision` | `Any` | `None` | Automatically populated with the `AdaptiveDecision` object during adaptive queries. |

---

## 4. `AdaptiveRouter` & `ComplexityWeights`

Defined in [`hyperrag/adaptive_router.py`](file:///d:/Rag/Hyper-RAG/hyperrag/adaptive_router.py#L28):

```python
from hyperrag import AdaptiveRouter, ComplexityWeights

custom_weights = ComplexityWeights(
    core_threshold=55,
    comparison_weight=25,
    causal_weight=20
)
router = AdaptiveRouter(weights=custom_weights)
```

| Weight Field | Default | Description |
| :--- | :---: | :--- |
| `core_threshold` | `60` | Integer cutoff ($0-100$) between Hyper-Lite and Hyper-Core. |
| `comparison_weight` | `20` | Points added when comparative phrasing is detected. |
| `causal_weight` | `15` | Points added for causal and mechanism-seeking phrasing. |
| `temporal_weight` | `15` | Points added for chronological or evolutionary queries. |
| `multi_hop_weight` | `15` | Points added for relationship pathway queries. |
| `aggregation_weight`| `15` | Points added for synthesis and exhaustive enumeration demands. |
| `depth_weight` | `12` | Points added for explicit depth triggers (`detailed`, `step by step`). |
| `relational_reasoning_weight`| `10` | Points added when multiple entities and relational verbs co-occur. |

---

## 5. `RetrievalSufficiencyEvaluator` & `SufficiencyWeights`

Defined in [`hyperrag/retrieval_sufficiency.py`](file:///d:/Rag/Hyper-RAG/hyperrag/retrieval_sufficiency.py#L50):

```python
from hyperrag import RetrievalSufficiencyEvaluator, SufficiencyWeights

weights = SufficiencyWeights(
    threshold=60.0,
    missing_relationship_penalty=25.0
)
evaluator = RetrievalSufficiencyEvaluator(weights=weights)
```

| Parameter | Default | Description |
| :--- | :---: | :--- |
| `threshold` | `60.0` | Minimum score required to pass sufficiency evaluation without escalation. |
| `volume_weight` | `0.25` | Weight for retrieved item count score. |
| `unique_entities_weight` | `0.20` | Weight for distinct entity diversity score. |
| `context_length_weight` | `0.25` | Weight for total context character volume. |
| `query_coverage_weight` | `0.30` | Weight for query entity / keyword lexical overlap. |
| `max_duplicate_penalty` | `20.0` | Maximum points deducted when chunks exhibit high redundancy. |
| `missing_relationship_penalty` | `25.0` | Points deducted if a multi-hop or causal query lacks hyperedges. |
