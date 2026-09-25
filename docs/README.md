# Hyper-RAG Documentation

Welcome to the comprehensive technical documentation for **Hyper-RAG** and **Adaptive Hyper-RAG**.

Hyper-RAG is a state-of-the-art Retrieval-Augmented Generation (RAG) framework developed by [iMoon-Lab](http://moon-lab.tech/), Tsinghua University, published in *Nature Communications* (2026). It combines hypergraph-driven knowledge structures with high-order relational reasoning to combat Large Language Model hallucinations.

This documentation suite covers the system architecture, configuration parameters, execution pipelines, data/request flows, and the adaptive routing and escalation subsystem.

---

## Documentation Structure

```text
docs/
├── README.md                          # Documentation index and navigational guide (this file)
├── architecture.md                    # Core architecture, hypergraph foundations & system design
├── parameters_and_configuration.md    # Configuration parameters, environment variables & QueryParam
├── request_and_data_flow.md           # End-to-end request lifecycle, data pipelines & sequence flows
├── adaptive_hyperrag.md               # Adaptive Hyper-RAG (Phase 1 Complexity Routing & Phase 2 Escalation)
└── api_reference.md                   # Public Python API and FastAPI endpoint reference
```

---

## Document Summaries

### 1. [System Architecture](file:///d:/Rag/Hyper-RAG/docs/architecture.md)
Detailed architectural breakdown of:
- **Knowledge Representation**: Documents $\rightarrow$ Chunks $\rightarrow$ Entities $\rightarrow$ Hyperedges (Hypergraph DB).
- **Dual Execution Engines**: Hyper-Lite (entity-focused lightweight vector search) vs. Hyper-Core (high-order hypergraph structure and relational diffusion).
- **Adaptive Layer**: Query complexity analyzer, heuristic scoring, and post-retrieval sufficiency escalation.
- **Provider Infrastructure**: OpenRouter (LLM reasoning) and Mistral (1024-dim embedding generation).

### 2. [Parameters & Configuration Guide](file:///d:/Rag/Hyper-RAG/docs/parameters_and_configuration.md)
Full parameter specification including:
- `HyperRAG` initialization parameters (`working_dir`, `llm_model_func`, `embedding_func`, storage backends).
- `QueryParam` execution parameters (`mode`, `top_k`, `max_token_for_text_unit`, `response_type`, etc.).
- Environment variables (`ADAPTIVE_RAG_ENABLED`, `ADAPTIVE_CORE_THRESHOLD`, `ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD`, API keys).
- Heuristic scoring weights and threshold calibrations.

### 3. [Request & Data Flow](file:///d:/Rag/Hyper-RAG/docs/request_and_data_flow.md)
Step-by-step tracing of data and execution paths:
- Indexing Pipeline: Document ingestion, chunking, entity extraction, hyperedge extraction, and vector index generation.
- Query Pipeline: FastAPI `/query` endpoint $\rightarrow$ `HyperRAG.aquery` $\rightarrow$ Adaptive Router $\rightarrow$ Retrieval $\rightarrow$ Sufficiency Check $\rightarrow$ Escalation $\rightarrow$ Prompt Construction $\rightarrow$ LLM Reasoning $\rightarrow$ Stream/Response.
- ASCII and sequence diagrams illustrating happy-path and escalation scenarios.

### 4. [Adaptive Hyper-RAG](file:///d:/Rag/Hyper-RAG/docs/adaptive_hyperrag.md)
Complete specification of the multi-phase adaptive subsystem:
- **Phase 1: Deterministic Complexity Routing**: 12 signals, 8 feature groups, additive scoring ($0-100$), zero LLM cost.
- **Phase 2: Retrieval Sufficiency & Lite $\rightarrow$ Core Escalation**: Concrete retrieval signals, relational checks, and zero-wasted-LLM early escalation.
- Configuration, logging diagnostics, and regression test suites.

### 5. [API Reference](file:///d:/Rag/Hyper-RAG/docs/api_reference.md)
Comprehensive code signatures and usage reference for:
- Python classes: `HyperRAG`, `QueryParam`, `AdaptiveRouter`, `RetrievalSufficiencyEvaluator`.
- Low-level functions: `hyper_retrieve_lite`, `hyper_query_lite_reasoning`, `hyper_query`.
- REST API: `/query`, `/query_stream`, `/healthz`.

---

## Quick Navigation Links

- [System Architecture](file:///d:/Rag/Hyper-RAG/docs/architecture.md)
- [Parameters & Configuration](file:///d:/Rag/Hyper-RAG/docs/parameters_and_configuration.md)
- [Request & Data Flow](file:///d:/Rag/Hyper-RAG/docs/request_and_data_flow.md)
- [Adaptive Hyper-RAG Details](file:///d:/Rag/Hyper-RAG/docs/adaptive_hyperrag.md)
- [API Reference](file:///d:/Rag/Hyper-RAG/docs/api_reference.md)
