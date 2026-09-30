# Hyper-RAG System Architecture & Data Flow

## 1. High-Level Architectural Overview

Hyper-RAG is a state-of-the-art Retrieval-Augmented Generation (RAG) system built around high-order **hypergraph** modeling of knowledge corpora. 

Unlike traditional Graph RAG frameworks that represent facts strictly as pairwise edges $(u, v)$ between two nodes, Hyper-RAG models complex, beyond-pairwise multi-entity relationships using **hyperedges** $e = \{v_1, v_2, \dots, v_k\}$. 

To combine deep high-order reasoning with low computational cost and ultra-low latency, the system implements a dynamic, multi-layered architecture:

```text
                                  +---------------------------------------+
                                  |              User Query               |
                                  +---------------------------------------+
                                                       |
                                                       v
                                  +---------------------------------------+
                                  |     Adaptive Hyper-RAG Router         |
                                  |   (Phase 1 & 2.1 Deterministic)       |
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
                                       |
                                       v
                         +----------------------------+
                         | Phase 3 Response Validator |
                         | (Completeness, Evidence,   |
                         |        Relevance)          |
                         +----------------------------+
                                       |
                                       v
                         +----------------------------+
                         |  Validated Answer Response |
                         +----------------------------+
```

---

## 2. Knowledge Representation & Storage Subsystem

Hyper-RAG organizes document knowledge across three complementary storage layers:

```text
Document (Raw Text)
   ├── Chunks (Text Units: ~1200 tokens each)
   │     ├── Stored in KVStorage (JsonKVStorage)
   │     └── Vectorized in chunks_vdb (Mistral 1024-dim dense vectors)
   │
   ├── Entities (Vertices in Hypergraph)
   │     ├── Named entities, concepts, categorical types, descriptions
   │     ├── Extracted via LLM schema prompting
   │     └── Vectorized in entities_vdb (Mistral 1024-dim)
   │
   ├── Relationships & Hyperedges (High-Order Edges)
   │     ├── Hyperedges connecting arbitrary subsets of entities {v1, v2, ..., vk}
   │     ├── Stored in ChunkEntityRelationHypergraph DB
   │     └── Vectorized in relationships_vdb (Mistral 1024-dim)
   │
   └── Communities & Hierarchies
         └── Clustered higher-order semantic communities for global synthesis
```

### Storage Backends
1. **`KVStorage` (`JsonKVStorage`)**: Key-value store persisting raw document text, passage chunk maps, entity metadata, and relation mappings on disk.
2. **`BaseVectorStorage` (`NanoVectorDBStorage`)**: Nearest-neighbor cosine similarity index over 1024-dimensional Mistral embeddings for:
   - `entities_vdb`: Entity names and descriptive summaries.
   - `relationships_vdb`: Hyperedge descriptions and relational summaries.
   - `chunks_vdb`: Raw text passage chunks.
3. **`ChunkEntityRelationHypergraph`**: The core hypergraph data structure tracking entity node incidence, vertex degree matrices, and multi-way edge associations.

---

## 3. Dual Execution Engines

### Hyper-Lite Pipeline (`hyper_retrieve_lite` & `hyper_query_lite_reasoning`)
- **Target Workload**: Definitional, single-entity, direct factual queries (e.g., *"What is diabetes?"*).
- **Execution Mechanism**:
  1. Extracts high-level keywords using lexical patterns.
  2. Queries `entities_vdb` for top-$k$ nearest entity embeddings.
  3. Pulls original passage chunks directly linked to matched entities.
  4. Synthesizes an answer using entity descriptions and passage chunks.
- **Latency & Compute**: Extremely fast ($<100$ ms retrieval overhead); skips hypergraph diffusion entirely.

### Hyper-Core Pipeline (`hyper_query`)
- **Target Workload**: Multi-entity, comparative, causal, temporal, and multi-hop queries (e.g., *"Compare diabetes and hypertension causes, mechanisms, and treatments"*).
- **Execution Mechanism**:
  1. Executes dual vector retrieval across both `entities_vdb` and `relationships_vdb`.
  2. Traverses the `ChunkEntityRelationHypergraph` using information diffusion across incident hyperedges.
  3. Aggregates multi-hop relational pathways and community context.
  4. Synthesizes a comprehensive answer grounded in structural hypergraph connections.
- **Latency & Compute**: Rich, high-order context preventing hallucinations on complex relational questions.

---

## 4. Multi-Phase Adaptive Subsystem

The adaptive layer dynamically coordinates execution across four deterministic phases without adding secondary LLM judge overhead:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ADAPTIVE HYPER-RAG PHASES                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 1:   Pre-Retrieval Query Complexity Scoring (0-100 score, 8 categories)│
│ Phase 2:   Post-Retrieval Sufficiency Evaluation (Evaluates retrieved context)│
│ Phase 2.1: Short-Query Semantic Density Refinement (+15 bonus for dense queries)│
│ Phase 3:   Post-Reasoning Deterministic Response Validation (Completeness,   │
│            Evidence Support, Relevance)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. End-to-End Sequence & Data Flows

### 5.1 Ingestion & Indexing Pipeline (Offline)

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant RAG as HyperRAG
    participant Chunker as TextChunker
    participant LLM as OpenRouter LLM
    participant Embedder as Mistral Embeddings
    participant DB as HypergraphDB & VectorDB

    Admin->>RAG: insert(document_text)
    RAG->>Chunker: chunk(text, size=1200, overlap=100)
    Chunker-->>RAG: text_chunks
    RAG->>Embedder: embed(text_chunks)
    Embedder-->>DB: store chunks_vdb (1024-dim)
    
    RAG->>LLM: extract_entities_and_relations(text_chunks)
    LLM-->>RAG: entities & multi-way hyperedge relations
    
    RAG->>Embedder: embed(entity_summaries & relation_summaries)
    Embedder-->>DB: store entities_vdb & relationships_vdb
    RAG->>DB: commit hypergraph incidence & KVStorage
    DB-->>RAG: index committed
    RAG-->>Admin: Ingestion complete
```

### 5.2 Online Query Lifecycle (Adaptive Routing with Sufficiency & Escalation)

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI Server
    participant RAG as HyperRAG Orchestrator
    participant Router as AdaptiveRouter (Phase 1 & 2.1)
    participant Lite as Hyper-Lite Pipeline
    participant Suff as SufficiencyEvaluator (Phase 2)
    participant Core as Hyper-Core Pipeline
    participant LLM as OpenRouter LLM
    participant Val as ResponseValidator (Phase 3)

    Client->>API: POST /query {"question": "...", "mode": "adaptive"}
    API->>RAG: aquery(question, QueryParam(mode="adaptive"))
    RAG->>Router: route(question)
    Router-->>RAG: AdaptiveDecision (score, initial_mode, features)

    alt Initial Mode is CORE (Score >= 60)
        RAG->>Core: hyper_query(question)
        Core->>LLM: generate_answer(core_prompt)
        LLM-->>Core: answer_text
        Core-->>RAG: answer_text
    else Initial Mode is LITE (Score < 60)
        RAG->>Lite: hyper_retrieve_lite(question)
        Lite-->>RAG: (entity_context, passage_chunks)
        RAG->>Suff: evaluate(question, entity_context, features)
        Suff-->>RAG: RetrievalSufficiency (score, sufficient)

        alt Evidence is Sufficient (Score >= 60.0)
            RAG->>Lite: hyper_query_lite_reasoning(entity_context)
            Lite->>LLM: generate_answer(lite_prompt)
            LLM-->>Lite: answer_text
            Lite-->>RAG: answer_text
        else Evidence is Insufficient (Score < 60.0)
            Note over RAG,Core: Early Escalation: Abort Lite LLM Reasoning
            RAG->>Core: hyper_query(question)
            Core->>LLM: generate_answer(core_prompt)
            LLM-->>Core: answer_text
            Core-->>RAG: answer_text
        end
    end

    RAG->>Val: validate(question, answer_text, context, decision)
    Val-->>RAG: ValidationResult (score, valid, missing, unsupported)
    RAG-->>API: (answer_text, decision, validation_result)
    API-->>Client: QueryResponse JSON
```

### 5.3 Streaming Sequence Flow (Token-by-Token SSE)

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI (/query_stream)
    participant RAG as HyperRAG.astream_query()
    participant Core as Retrieval & Diffusion
    participant LLM as OpenRouter Streaming Client

    Client->>API: POST /query_stream {"question": "...", "mode": "adaptive"}
    API->>RAG: astream_query(question)
    RAG->>Core: retrieve_and_assemble_context(question)
    Core-->>RAG: assembled_prompt
    RAG->>LLM: openrouter_mistral_stream(assembled_prompt)
    loop Stream Tokens
        LLM-->>RAG: token chunk
        RAG-->>API: yield token
        API-->>Client: data: {"token": "..."}
    end
    API-->>Client: data: [DONE]
```

---

## 6. Provider Topology & Invariants

Hyper-RAG maintains strict separation between external providers:

```text
+--------------------------------------------------------------------------+
|                        EXTERNAL PROVIDER TOPOLOGY                        |
+--------------------------------------------------------------------------+
|                                                                          |
|   1. LLM Reasoning Engine (Primary & ONLY Reasoning Provider):           |
|      - Provider: OpenRouter (https://openrouter.ai/api/v1)              |
|      - Model: nvidia/nemotron-3-ultra-550b-a55b:free                    |
|      - Support: Non-streaming JSON & Server-Sent Events (SSE) streaming  |
|      - Fault-Tolerance: KeyPool multi-key round-robin & 429 backoff      |
|                                                                          |
|   2. Dense Embedding Engine (Embeddings ONLY):                           |
|      - Provider: Mistral AI (https://api.mistral.ai/v1)                 |
|      - Model: mistral-embed                                             |
|      - Vector Dimensions: 1024 fixed output dimensions                  |
|      - Invariant: Never used as an LLM reasoning fallback               |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 7. Configuration Flow

1. `.env` file is read at application startup via `python-dotenv` into `my_config.py`.
2. `my_config.py` normalizes API keys, strips whitespace, parses fallback aliases (`MISTRAL_API_KEY` $\rightarrow$ `EMB_API_KEY`), and verifies configuration invariants.
3. Fast unit tests in `tests/unit/test_config.py` assert that all configuration boundaries and validation weight sums are satisfied.
4. If configuration is invalid, `validate_config()` prints clear error diagnostics without exposing secret API keys.
