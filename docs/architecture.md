# System Architecture

## 1. Architectural Overview

Hyper-RAG is structured around high-order hypergraph modeling of text corpora. Unlike traditional Graph RAG systems that rely exclusively on pairwise edges between two nodes $(u, v)$, Hyper-RAG models higher-order multi-entity interactions using **hyperedges** $e = \{v_1, v_2, \dots, v_k\}$.

To maximize efficiency and cost-effectiveness across diverse query types, the system implements a layered architecture:

```text
                                  +---------------------------------------+
                                  |              User Query               |
                                  +---------------------------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |     Adaptive Hyper-RAG Router         |
                                  |     (Phase 1 Complexity Scoring)      |
                                  +---------------------------------------+
                                                      |
                         +----------------------------+----------------------------+
                         |                                                         |
                         v                                                         v
             [Initial Mode: Hyper-Lite]                                [Initial Mode: Hyper-Core]
                         |                                                         |
                         v                                                         |
         +--------------------------------+                                        |
         |   Lite Keyword & Entity Search |                                        |
         |     (hyper_retrieve_lite)      |                                        |
         +--------------------------------+                                        |
                         |                                                         |
                         v                                                         |
         +--------------------------------+                                        |
         | Retrieval Sufficiency Evaluator|                                        |
         |    (Phase 2 Deterministic)     |                                        |
         +--------------------------------+                                        |
                         |                                                         |
                Is Evidence Sufficient?                                            |
                /                     \                                            |
         YES (Score >= 60)       NO (Score < 60)                                   |
              |                        |                                           |
              |                        +------------------+                        |
              |                                           |                        |
              v                                           v                        v
+-------------------------------+             +---------------------------------------------+
|    Lite Context Assembly &    |             | Hyper-Core Retrieval & Hypergraph Diffusion |
|         LLM Reasoning         |             |                 (hyper_query)               |
+-------------------------------+             +---------------------------------------------+
              |                                                     |
              |                                                     v
              |                                       +-----------------------------+
              |                                       |   High-Order Reasoning &    |
              |                                       |      Prompt Synthesis       |
              |                                       +-----------------------------+
              |                                                     |
              +-----------------------+-----------------------------+
                                      |
                                      v
                        +----------------------------+
                        |       Final Answer         |
                        +----------------------------+
```

---

## 2. Knowledge Representation & Storage Subsystem

Hyper-RAG maintains a multi-faceted persistent storage architecture:

```text
Document (Raw Text)
   ├── Chunks (Text Units: ~1200 tokens each)
   │     ├── Stored in KVStorage (JSON / NanoVectorDB)
   │     └── Vectorized for Chunk-level semantic retrieval
   │
   ├── Entities (Nodes in Hypergraph)
   │     ├── Named Entities, Topics, Concepts
   │     ├── Extracted via LLM schema prompts
   │     └── Vectorized in entities_vdb (Mistral 1024-dim)
   │
   ├── Relationships & Hyperedges (High-Order Edges)
   │     ├── Hyperedges connecting arbitrary subsets of entities
   │     ├── Stored in ChunkEntityRelationHypergraph DB
   │     └── Vectorized in relationships_vdb
   │
   └── Communities & Hierarchies
         └── Clustered higher-order semantic communities for global queries
```

### Storage Backends
1. **`KVStorage`**: Stores raw document content, chunk maps, entity metadata, and relation mappings (`JsonKVStorage`).
2. **`BaseVectorStorage` / `NanoVectorDBStorage`**: Performs nearest-neighbor cosine similarity lookups over:
   - `entities_vdb`: Entity names and descriptions.
   - `relationships_vdb`: Hyperedge descriptions and relational summaries.
   - `chunks_vdb`: Raw passage chunks.
3. **`ChunkEntityRelationHypergraph`**: The high-order graph data structure maintaining entity node incidence, degree matrices, and multi-way edge associations.

---

## 3. Dual Execution Pipelines

### Hyper-Lite Pipeline
- **Target Queries**: Definitional, single-entity, direct factual questions (e.g., *"What is diabetes?"*).
- **Retrieval Mechanism**:
  1. Extracts high-level query keywords using regex and linguistic heuristics.
  2. Queries `entities_vdb` for top-$k$ nearest entity matches.
  3. Pulls original passage chunks linked to those matched entities.
- **Cost & Latency**: Extremely low latency; bypasses hypergraph diffusion and relational edge expansions.

### Hyper-Core Pipeline
- **Target Queries**: Comparative, causal, temporal, multi-hop, and multi-entity questions (e.g., *"Compare diabetes and hypertension in terms of causes and treatment"*).
- **Retrieval Mechanism**:
  1. Multi-vector similarity retrieval across both entities and relational hyperedges.
  2. One- or multi-layer hypergraph information diffusion across neighbor nodes and incident hyperedges.
  3. Community-aware contextual synthesis combining high-order relational paths with primary text units.
- **Cost & Latency**: Produces richer structural context with comprehensive relational coverage.

---

## 4. The Adaptive Hyper-RAG Subsystem

The adaptive layer sits between incoming queries and the execution pipelines, consisting of two deterministic phases:

### Phase 1: Pre-Retrieval Complexity Routing
- Analyzes the raw query using [`QueryFeatureExtractor`](file:///d:/Rag/Hyper-RAG/hyperrag/adaptive_router.py#L86).
- Computes an additive $0-100$ score via [`HeuristicComplexityScorer`](file:///d:/Rag/Hyper-RAG/hyperrag/adaptive_router.py#L209).
- Directly assigns `initial_mode`:
  - Score $< 60 \rightarrow$ `Hyper-Lite`
  - Score $\ge 60 \rightarrow$ `Hyper-Core`
- Operates entirely locally with **0 LLM calls**.

### Phase 2: Post-Retrieval Sufficiency Evaluation & Early Escalation
- Evaluates the concrete context assembled by `hyper_retrieve_lite`.
- Inspects item volume, unique entities, context length, query-context lexical overlap, redundancy, and relational evidence.
- If score $< 60$ (insufficient evidence or missing hyperedge paths for relational queries):
  - **Aborts Lite reasoning** before calling the LLM.
  - Automatically escalates to `Hyper-Core`.
  - Ensures at most **one** escalation per query.

---

## 5. Model & Provider Infrastructure

Hyper-RAG enforces a strict separation of concerns for external AI providers:

```text
+--------------------------------------------------------------------------+
|                        External Provider Topology                        |
+--------------------------------------------------------------------------+
|                                                                          |
|   1. LLM Reasoning (Primary & ONLY Provider):                           |
|      - Provider: OpenRouter (https://openrouter.ai/api/v1)              |
|      - Model: nvidia/nemotron-3-ultra-550b-a55b:free                    |
|      - Supported: Streaming (SSE) and Non-Streaming generation           |
|      - Key Rotation: Multi-key pool with automated cooldown             |
|                                                                          |
|   2. Embeddings (Embeddings ONLY):                                       |
|      - Provider: Mistral AI (https://api.mistral.ai/v1)                 |
|      - Model: mistral-embed                                             |
|      - Vector Dimension: 1024 fixed dimensions                          |
|      - Constraint: Never used as an LLM reasoning fallback              |
|                                                                          |
+--------------------------------------------------------------------------+
```
