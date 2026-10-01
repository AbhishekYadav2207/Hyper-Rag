# Document 05: Hyper-RAG Indexing & Embeddings

This guide details the internal mechanics of Hyper-RAG's indexing pipeline, vector storage, hypergraph construction, embedding models, and vector dimensional alignment.

---

## 1. The Hyper-RAG Indexing Architecture

When you call `HyperRAG.insert(document_text)`, the system executes a multi-stage indexing workflow that constructs both vector spaces and higher-order topological hypergraphs:

```text
┌────────────────────────────────────────────────────────┐
│           Combined Perspective Document Text           │
│   (Concatenated perspectives separated by '\n\n---\n\n') │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                   Text Chunking                        │
│   (token_size = 1200, overlap = 100 in hyperrag/operate)│
└─────────────────────┬──────────────────┬───────────────┘
                      │                  │
                      ▼                  ▼
┌───────────────────────────┐    ┌───────────────────────────────┐
│     Chunk Embedding       │    │     LLM Entity Extraction     │
│   (openai_embedding)      │    │   (openrouter_mistral_...)    │
│   dim = 1024 (Mistral)    │    │   Extract entities & relations│
└─────────────┬─────────────┘    └───────────────┬───────────────┘
              │                                  │
              ▼                                  ▼
┌───────────────────────────┐    ┌───────────────────────────────┐
│     Vector DB: Chunks     │    │   Entity & Relation Embedding │
│     vdb_chunks.json       │    │   vdb_entities / vdb_relations│
└───────────────────────────┘    └───────────────┬───────────────┘
                                                 │
                                                 ▼
                                 ┌───────────────────────────────┐
                                 │      Hypergraph DB (.hgdb)    │
                                 │   Construct multi-way edges   │
                                 │   hypergraph_chunk_entity_... │
                                 └───────────────────────────────┘
```

---

## 2. Storage Layer Artifacts Explained

An indexed Hyper-RAG knowledge base (e.g. `caches/tsbc_maritime_test/`) contains exactly the following persistent files:

| Storage File | Technology | Purpose & Contents | Size / Scope in TSBC Case Study |
|---|---|---|---|
| `hypergraph_chunk_entity_relation.hgdb` | `HypergraphDB` | Adjacency store of entity vertices and multi-way hyperedges connecting chunks to concepts | **22 vertices, 3 hyperedges** |
| `vdb_chunks.json` | JSON Vector DB | 1024-dimensional vectors for raw text passages | 5 passage vectors |
| `vdb_entities.json` | JSON Vector DB | 1024-dimensional vectors for extracted domain entities (*ANVOURGON*, *Halifax*, etc.) | 22 entity vectors |
| `vdb_relationships.json` | JSON Vector DB | 1024-dimensional vectors for semantic relation summaries | Multi-entity relation vectors |
| `kv_store_text_chunks.json` | Key-Value Store | Raw text strings of chunks mapped by chunk ID hash | Full passage texts |
| `kv_store_full_docs.json` | Key-Value Store | Full unchunked source document representation | Root context document |
| `kv_store_llm_response_cache.json` | Key-Value Store | Cached LLM entity extraction prompts and responses | Protects against duplicate LLM billing |

---

## 3. The Embedding Dimension Alignment Rule

> [!CRITICAL]
> **Vector Dimension Invariant**: The embedding dimension used to build the index **MUST BE IDENTICAL** to the embedding dimension used by runtime query functions.

```text
[FAILURE MODE: Embedding Dimension Mismatch]
Stored Vector (vdb_chunks.json):      [0.021, -0.054, ... 1024 floats]
Query Vector (text-embedding-3-small): [0.112,  0.832, ... 1536 floats]
                                            │
                                            ▼
                     COSINE SIMILARITY / DOT PRODUCT CRASH
               ValueError: shapes (1024,) and (1536,) not aligned!
```

### The Historical TSBC Debugging Case Study
During initial testing:
1. `caches/tsbc_maritime_test/` was indexed using `mistral-embed` with `EMB_DIM=1024`.
2. When testing via the WebUI, the backend fallback in `web-ui/backend/main.py` defaulted to `text-embedding-3-small` with `embeddingDim=1536`.
3. When the user submitted a query, the backend generated a 1536-dimensional vector to query the 1024-dimensional vector database.
4. Cosine similarity calculations either threw internal dimension mismatch exceptions or failed to retrieve any matching text units.

### How We Permanently Solved This
In `web-ui/backend/main.py` and `my_config.py`:
1. Standardized `EMB_MODEL = "mistral-embed"` and `EMB_DIM = 1024`.
2. Implemented active normalization in `get_effective_settings()`:
   ```python
   # Normalize legacy text-embedding-3-small or 1536 entries to canonical Mistral
   if saved.get("embeddingModel") in ("text-embedding-3-small", None) or saved.get("embeddingDim") in (1536, None):
       saved["embeddingModel"] = "mistral-embed"
       saved["embeddingDim"] = 1024
       saved["embeddingBaseUrl"] = "https://api.mistral.ai/v1"
   ```
3. In `get_hyperrag_embedding_func()`, enforced `EMB_API_KEY` and Mistral endpoints.

---

## 4. Current Project Configuration Reference

The following settings represent the verified production baseline across the repository:

```python
# From my_config.py
EMB_BASE_URL = "https://api.mistral.ai/v1"
EMB_MODEL = "mistral-embed"
EMB_DIM = 1024
EMB_API_KEY = "<MISTRAL_API_KEY>"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
OPENROUTER_API_KEY = "<OPENROUTER_API_KEY>"
```

*(Note: These values are current project defaults and should be adjusted if your organization adopts a different embedding provider such as OpenAI `text-embedding-3-large` or local HuggingFace `bge-m3`)*.

---

## 5. Cache Rebuild Policy: When to Rebuild vs. When to Preserve

| Scenario | Rebuild Required? | Action Required |
|---|---|---|
| **Changing Embedding Model or Dimension** | **YES (MANDATORY)** | Delete `caches/<dataset>/` and re-index. Old vectors cannot be compared with vectors from a new model. |
| **Changing Chunk Size or Overlap** | **YES** | Delete `caches/<dataset>/` and re-index. Chunk IDs and boundaries will shift. |
| **Updating Source Normalization Logic** | **YES** | Delete `caches/<dataset>/` and re-index to reflect cleaned facts. |
| **Switching LLM Generator** | **NO** | Keep cache intact. The hypergraph and vector index remain valid regardless of what LLM synthesizes answers. |
| **Switching Adaptive RAG Routing Thresholds** | **NO** | Keep cache intact. Adaptive routing thresholds operate at query time. |
| **Adding New Independent Dataset** | **NO** | Build in a new isolated folder `caches/<new_dataset>/`. Never touch existing caches. |
