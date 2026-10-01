# Document 06: Retrieval & Query Flow

This guide details the end-to-end query lifecycle in Hyper-RAG, explaining how questions move from the user interface through the FastAPI backend, the three-phase Adaptive RAG engine, vector and hypergraph retrieval, LLM synthesis, and response validation.

---

## 1. End-to-End Query Lifecycle

```text
User Question (Browser Web Console)
        │
        ▼ HTTP POST /hyperrag/query {"query": "...", "mode": "adaptive", "database": "tsbc_maritime_test"}
FastAPI Router (web-ui/backend/main.py)
        │
        ▼ Load / retrieve database instance from db_manager
Adaptive RAG Pipeline (hyperrag/operate.py)
        │
        ├─► Phase 1: Complexity Scoring (0 to 100)
        │     - Short-query semantic density evaluation (Phase 2.1)
        │     - Syntax heuristics & multi-entity relational triggers
        │     - Decision: Lite (Vector-Only) vs. Core (Hypergraph + Vector)
        │
        ├─► Retrieval Stage
        │     - Lite Mode: Top-k vector similarity on vdb_chunks.json
        │     - Core Mode: Vector search + Hypergraph vertex traversal + incident hyperedges
        │
        ├─► Phase 2: Retrieval Sufficiency Evaluation
        │     - Measures token volume, entity co-occurrence, and context density
        │     - If Sufficiency < Threshold (60) in Lite: Auto-escalate Lite ➔ Core
        │
        ├─► Context Assembly & Prompt Synthesis
        │     - Assembles retrieved text units, entity descriptions, and hyperedges
        │     - Injects into system prompt with grounding instructions
        │
        ├─► LLM Generation (OpenRouter / Nemotron)
        │     - Synthesizes grounded answer
        │
        └─► Phase 3: Response Validation
              - Evaluates Completeness, Relevance, and Evidence Support Score
              - Flags ungrounded claims and missing aspects
        │
        ▼ JSON Response: {"success": true, "response": "...", "answer": "...", "entities": [...], "hyperedges": [...]}
Frontend Rendering (React Chat View)
        │
        ▼ Render prose answer, metadata badges, and expandable decision trace
User Displays Answer
```

---

## 2. Adaptive RAG Modes: Lite vs. Core

In Hyper-RAG, retrieval is governed by `AdaptiveRouter` (`hyperrag/operate.py`):

| Characteristic | Lite Mode (Vector-Only) | Core Mode (Hypergraph + Vector) |
|---|---|---|
| **Best For** | Direct single-hop fact retrieval (e.g. "What year was Occurrence 4?", "What flag did ANVOURGON fly?") | Multi-hop reasoning, relational comparisons, cross-entity impact analysis (e.g. "Compare damage across occurrences", "How did sea state affect rescue?") |
| **Retrieval Sources** | `vdb_chunks.json` (vector cosine similarity) | `vdb_chunks.json` + `vdb_entities.json` + `vdb_relationships.json` + `hypergraph_chunk_entity_relation.hgdb` |
| **Context Overhead** | Low (~300–600 tokens) | High (~1200–2500 tokens) |
| **Average Latency** | **Fast** (~40–80 ms local retrieval) | **Thorough** (~120–250 ms local retrieval) |
| **Escalation Path** | Automatically upgrades to Core if Phase 2 sufficiency score $< 60$ | Terminal mode (does not downgrade) |

---

## 3. The Three Verification Phases Explained

### Phase 1: Complexity Scoring
Before making any database queries, the router analyzes the query text:
- **Heuristic Triggers**: Words indicating comparison ("compare", "versus", "difference"), causality ("why", "cause", "lead to"), or aggregation ("all", "list every") add complexity points.
- **Phase 2.1 Short-Query Density**: Queries with $\le 6$ words that contain high-density proper nouns (e.g. *"ANVOURGON Rivière-au-Renard"*) receive a density bonus to ensure they are not erroneously routed to Lite.
- **Route Selection**: Score $\ge 60$ routes to Core; Score $< 60$ routes to Lite.

### Phase 2: Retrieval Sufficiency Evaluation
After initial retrieval, the engine inspects the retrieved text units:
- Checks if the retrieved passages actually contain the semantic density required to answer the query.
- If a query started in Lite mode but retrieved insufficient passages (Score $< 60$), the router triggers an **automatic escalation to Core**, fetching the incident hypergraph vertices and neighboring hyperedges.

### Phase 3: Response Validation
After the LLM generates the answer, a validation step scores the output:
- **Completeness**: Did the answer address all sub-questions?
- **Evidence Support Score**: Are factual claims in the answer grounded in the retrieved text passages?
- **Ungrounded Claims**: Any statements not supported by retrieved context are flagged.

---

## 4. Diagnosing Retrieval Failures

When queries fail or produce weak answers, follow this systematic diagnostic tree:

```text
                               Query Produced Poor Answer
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
          Response is Hallucinated                     Response is Empty / Error
                    │                                             │
      ┌─────────────┴─────────────┐                 ┌─────────────┴─────────────┐
      ▼                           ▼                 ▼                           ▼
[Weak Context]             [Missing Facts]    [Wrong Database]          [Dimension Error]
Text units retrieved       Target field was   Request sent to 'mock'    Stored dim = 1024
contain irrelevant info.   null in raw data;  instead of                Query dim = 1536.
Fix: Check query embedding context lacked     '<dataset>_test'.         Fix: Check settings.json
and chunk overlap.         negative statement.Fix: Check header select. and normalize in backend.
```

### 1. Empty Context / Zero Entities Retrieved
- **Check**: Open the browser Network tab, look at `POST /hyperrag/query` response. Are `"text_units"`, `"entities"`, and `"hyperedges"` empty arrays?
- **Cause**: Either the query has zero vector overlap with the stored chunks, or the wrong database was queried.
- **Fix**: Verify that the selected database header matches your intended index, and test with query keywords known to exist verbatim in the text.

### 2. Weak Context Dilution
- **Check**: Look at the retrieved `text_units` in the backend log.
- **Cause**: The context perspectives were created too long (>800 words), causing vector similarity scores to fall below the retrieval threshold.
- **Fix**: Re-decompose source records into tighter, more focused 150-300 word perspectives.

### 3. OpenRouter / LLM Returns Null Choices
- **Check**: Uvicorn logs show `HTTP 429 Rate Limit` or OpenRouter response with empty `choices`.
- **Cause**: Free-tier model rate limit or missing API key.
- **Fix**: Check `OPENROUTER_API_KEY` in `.env` or rotate to a secondary key.
