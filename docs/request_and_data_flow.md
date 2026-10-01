# Request and Data Flow Reference

> [!NOTE]
> The comprehensive, updated system architecture and end-to-end Mermaid sequence diagrams are maintained in [**`docs/ARCHITECTURE.md`**](ARCHITECTURE.md).

---

## 1. Indexing Pipeline Summary
Raw documents are chunked into ~1200 token passages, embedded with Mistral (1024-dim), processed by the OpenRouter LLM to extract entities and multi-entity relationships, and committed into `KVStorage`, `BaseVectorStorage`, and `ChunkEntityRelationHypergraph`.

For detailed architecture diagrams, see [**Ingestion Pipeline in `docs/ARCHITECTURE.md`**](ARCHITECTURE.md#51-ingestion--indexing-pipeline-offline).

---

## 2. Online Query Execution Flow Summary
1. Client issues `POST /query` or calls `rag.aquery(..., param=QueryParam(mode="adaptive"))`.
2. **Phase 1 & 2.1 Complexity Router** scores query ($0-100$). Score $\ge 60$ routes to **Hyper-Core**; $<60$ routes to **Hyper-Lite**.
3. If Hyper-Lite: executes keyword and entity search, then passes retrieved context to **Phase 2 Sufficiency Evaluator**.
   - If Sufficiency Score $\ge 60$: proceeds to Lite LLM reasoning.
   - If Sufficiency Score $< 60$: aborts Lite reasoning and **escalates to Hyper-Core**.
4. LLM synthesizes answer using assembled context.
5. **Phase 3 Response Validator** checks completeness, evidence support, and relevance.
6. Validated answer and structured decision metadata return to client.

For the complete interactive sequence diagram, see [**Query Lifecycle in `docs/ARCHITECTURE.md`**](ARCHITECTURE.md#52-online-query-lifecycle-adaptive-routing-with-sufficiency--escalation).
