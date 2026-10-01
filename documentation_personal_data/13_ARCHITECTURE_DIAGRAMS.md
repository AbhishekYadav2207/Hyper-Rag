# Document 13: Architecture & Dataflow Diagrams

This document collects architectural and operational diagrams representing Hyper-RAG's data ingestion, storage, retrieval, and verification pipelines.

---

## 1. Generic Custom Dataset → Hyper-RAG End-to-End Flow

```mermaid
flowchart TD
    A[Raw Source Data<br/>JSON, CSV, Parquet, Relational] -->|Read-only stream| B[Local Schema Audit<br/>Profile types, nulls, keys]
    B -->|Deterministic Python| C[Canonical Normalization<br/>RecordNormalizer]
    C -->|Composite tuple rules| D[Deduplicated Entities<br/>& Provenance Trace]
    D -->|Semantic grouping| E[Context Perspectives<br/>3 to 6 micro-documents]
    E -->|Preflight check| F[Dry-Run Estimation<br/>Zero API calls]
    F -->|Hardcoded limit: max=1| G[Isolated HyperRAG.insert<br/>caches/dataset_test/]
    G --> H[(Vector DB & Hypergraph<br/>vdb_*.json + .hgdb)]
    H -->|Directory Junction| I[hyperrag_cache/dataset_test<br/>WebUI Discovery]
    I --> J[Adaptive RAG Retrieval<br/>FastAPI /hyperrag/query]
    J --> K[Web Console & Chat<br/>React Frontend]
```

---

## 2. TSBC Maritime Implementation Architecture

```mermaid
flowchart LR
    subgraph Source["Read-Only Source Corpus"]
        S1["D:\CAIR\TSBC-MaritimePipeline\outputs\maritime_corpus.jsonl<br/>(68,355 lines | 44,329 occurrences)"]
    end

    subgraph Pipeline["datasets/tsbc_maritime/pipeline.py"]
        P1["Occurrence 4 Selection<br/>(ANVOURGON, 1975)"]
        P2["Equipment Deduplication<br/>(Composite tuples)"]
        P3["5 Context Perspectives<br/>(Overview, Vessel, Env, Damage, Equip)"]
    end

    subgraph Storage["caches/tsbc_maritime_test/"]
        ST1["hypergraph_chunk_entity_relation.hgdb<br/>(22 vertices, 3 hyperedges)"]
        ST2["vdb_chunks.json (1024-dim)"]
        ST3["vdb_entities.json (1024-dim)"]
    end

    subgraph Serving["WebUI & Runtime"]
        SR1["hyperrag_cache/tsbc_maritime_test<br/>(Windows Junction)"]
        SR2["FastAPI Backend (Port 8000)"]
        SR3["React Web Console (/#/Hyper/chat)"]
    end

    S1 --> P1
    P1 --> P2
    P2 --> P3
    P3 --> ST1
    P3 --> ST2
    P3 --> ST3
    Storage -.->|mklink /J| SR1
    SR1 --> SR2
    SR2 --> SR3
```

---

## 3. Hyper-RAG Dual Indexing Pipeline

```mermaid
flowchart TD
    Doc[Combined Perspective Text] --> Chunker[Text Chunker<br/>1200 char token window, 100 overlap]
    
    Chunker -->|Chunk texts| Emb1[Mistral Embeddings<br/>mistral-embed 1024-dim]
    Emb1 --> VDB1[(vdb_chunks.json)]
    
    Chunker -->|Prompt + Chunk| LLM1[OpenRouter LLM<br/>Entity & Relation Extraction]
    LLM1 -->|Discovered Entities| Emb2[Entity Embeddings<br/>1024-dim]
    Emb2 --> VDB2[(vdb_entities.json)]
    
    LLM1 -->|Discovered Relations| Emb3[Relation Embeddings<br/>1024-dim]
    Emb3 --> VDB3[(vdb_relationships.json)]
    
    LLM1 -->|Vertex & Edge tuples| HG[Hypergraph DB Engine]
    HG --> HGDB[(hypergraph_chunk_entity_relation.hgdb<br/>Adjacency & Hyperedges)]
```

---

## 4. Adaptive RAG 3-Phase Query & Retrieval Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as React Web Console
    participant API as FastAPI (/hyperrag/query)
    participant Router as AdaptiveRouter (operate.py)
    participant Store as Vector & Hypergraph DB
    participant LLM as OpenRouter Generator

    User->>UI: Submit Question
    UI->>UI: Display "Thinking..." Badge
    UI->>API: POST /hyperrag/query (query, mode, db)
    API->>Router: Execute Adaptive Query Pipeline
    
    rect rgb(240, 248, 255)
    Note over Router: Phase 1: Complexity Scoring
    Router->>Router: Evaluate syntax, heuristics, Phase 2.1 short query density
    end

    alt Complexity < 60 (Lite Route)
        Router->>Store: Vector Similarity Search (vdb_chunks.json)
        Store-->>Router: Retrieved Chunks
        rect rgb(255, 250, 240)
        Note over Router: Phase 2: Retrieval Sufficiency
        Router->>Router: Sufficiency Score < 60? ➔ Escalate to Core!
        end
    else Complexity >= 60 (Core Route)
        Router->>Store: Vector Search + Hypergraph Multi-Hop Traversal
        Store-->>Router: Chunks + Entity Vertices + Incident Hyperedges
    end

    Router->>LLM: Synthesize Grounded Answer (Prompt + Context)
    LLM-->>Router: Raw Generated Answer

    rect rgb(245, 255, 245)
    Note over Router: Phase 3: Response Validation
    Router->>Router: Calculate Completeness & Evidence Grounding Score
    end

    Router-->>API: Package Response + Entities + Metadata
    API-->>UI: HTTP 200 {response, answer, entities, hyperedges}
    UI->>UI: Clear "Thinking..." ➔ Render Answer Prose & Badges
    UI-->>User: Display Final Response
```

---

## 5. WebUI & Discovery Architecture

```mermaid
flowchart TD
    subgraph Filesystem
        C1["caches/tsbc_maritime_test/"]
        C2["caches/financial_sec_test/"]
        HC["hyperrag_cache/"]
        J1["hyperrag_cache/tsbc_maritime_test"]
        J2["hyperrag_cache/financial_sec_test"]
        
        C1 -.->|Junction| J1
        C2 -.->|Junction| J2
        J1 --- HC
        J2 --- HC
    end

    subgraph Backend["web-ui/backend/"]
        DBM["DatabaseManager.list_databases()<br/>Scans hyperrag_cache/"]
        EP["GET /databases"]
        QP["POST /hyperrag/query"]
    end

    subgraph Frontend["web-ui/frontend/"]
        SEL["Header Select Dropdown<br/>(tsbc_maritime_test, financial_sec_test)"]
        CHAT["Chat View (Home/index.tsx)<br/>updateLastMessage(content, extraData)"]
    end

    HC --> DBM
    DBM --> EP
    EP --> SEL
    SEL -->|Active Database Header| QP
    QP --> CHAT
```

---

## 6. API Quota-Safe 10-Level Workflow

```mermaid
flowchart TD
    L0["Level 0: Quarantine & Audit<br/>(0 API calls)"] --> L1["Level 1: Normalization & Deduplication<br/>(0 API calls)"]
    L1 --> L2["Level 2: Context Perspective Design<br/>(0 API calls)"]
    L2 --> L3["Level 3: Preflight Dry-Run Check<br/>(0 API calls)"]
    L3 -->|Pass preflight checks| L4["Level 4: Isolated 1-Record Index<br/>(Strictly bounded ~5 embeddings, ~5 LLM)"]
    L4 --> L5["Level 5: Direct Python Retrieval Tests<br/>(Known facts + Negative unrecorded facts)"]
    L5 --> L6["Level 6: WebUI Junction Link & Sanity Check<br/>(FastAPI discovery)"]
    L6 --> L7["Level 7: Automated Browser Test<br/>(Playwright headless test)"]
    L7 --> L8["Level 8: Controlled 3-Record Expansion<br/>(Multi-entity benchmark)"]
    L8 --> L9["Level 9: Full Production-Scale Scaling<br/>(Checkpointed batches)"]
```

---

## 7. Troubleshooting Decision Tree

```mermaid
flowchart TD
    Start[Encountered Issue] --> Q1{Where does failure occur?}
    
    Q1 -->|Startup Crash| S1{Traceback message?}
    S1 -->|ModuleNotFoundError: No module named 'db'| F1[Fix: Use relative import from .db import ... in main.py]
    S1 -->|UnicodeEncodeError| F2[Fix: Set sys.stdout UTF-8 stream reconfigure]

    Q1 -->|WebUI Query Hang| S2{Backend logs show HTTP 200?}
    S2 -->|YES: Backend finished| F3[Fix: updateLastMessage in Home/index.tsx neglected content param]
    S2 -->|NO: Backend hung/crashed| F4[Check OpenRouter API key & Mistral embeddings]

    Q1 -->|Vector Dimension Error| S3{1024 vs 1536 mismatch?}
    S3 -->|YES| F5[Fix: Normalize settings.json and backend to mistral-embed 1024]

    Q1 -->|Hallucinated Answer| S4{Field exists in raw record?}
    S4 -->|NO: Field was null| F6[Fix: Explicitly state 'Field X is not recorded' in context]
    S4 -->|YES: Field was omitted| F7[Fix: Review normalization mapping]
```
