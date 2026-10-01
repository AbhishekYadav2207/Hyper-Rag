# Template: Dataset Integration Sign-Off Report

Use this standardized template to document the engineering outcomes and sign-off metrics for each integrated dataset.

---

## 1. Executive Summary

- **Dataset Name**: `[e.g. TSBC Maritime Occurrence Corpus]`
- **Integration Date**: `[YYYY-MM-DD]`
- **Sign-Off Status**: `[PASS / CONDITIONAL / BLOCKED]`
- **Primary Deliverables**:
  - Raw Reference File: `datasets/<name>/raw_reference/<name>_test_1.jsonl`
  - Normalized Records: `datasets/<name>/normalized/<name>_normalized.json`
  - Context Perspectives: `datasets/<name>/contexts/<name>_contexts.json`
  - Isolated Cache: `caches/<name>_test/`
  - WebUI Junction: `hyperrag_cache/<name>_test/`

---

## 2. Source Corpus Metrics & Preprocessing

- **Source File Path**: `[Path]`
- **Total Lines / Records**: `[e.g. 68,355 lines]`
- **Unique Primary Entities**: `[e.g. 44,329 occurrences]`
- **Selected Representative Record ID**: `[e.g. Occurrence ID: 4]`
- **Selection Rationale**: `[e.g. High completeness score, multi-perspective coverage, clear damage and outcome fields]`
- **Deduplication Applied**: `[e.g. Composite tuple deduplication on nested equipment arrays]`
- **Provenance Maintained**: `[e.g. Source file name, row offsets, perspective IDs]`

---

## 3. Context Perspectives Generated

| Perspective Identifier | Word Count | Key Entities Included | Grounding Purpose |
|---|---|---|---|
| `[perspective_1]` | 210 words | `[Entities]` | `[e.g. Incident Overview]` |
| `[perspective_2]` | 185 words | `[Entities]` | `[e.g. Subject Profile]` |
| `[perspective_3]` | 140 words | `[Entities]` | `[e.g. Telemetry / Environment]` |
| `[perspective_4]` | 220 words | `[Entities]` | `[e.g. Damage & Outcomes]` |
| `[perspective_5]` | 115 words | `[Entities]` | `[e.g. Equipment Profile]` |

---

## 4. Indexing & Storage Metrics

- **Embedding Model**: `[e.g. mistral-embed]`
- **Vector Dimension**: `[e.g. 1024]`
- **LLM Generator**: `[e.g. nvidia/nemotron-3-ultra-550b-a55b:free]`
- **Hypergraph Vertices Count**: `[e.g. 22 vertices]`
- **Hyperedges Count**: `[e.g. 3 hyperedges]`
- **Vector Chunks Count**: `[e.g. 5 chunk vectors]`
- **Total Indexing Time**: `[e.g. 18.4 seconds]`

---

## 5. API Consumption & Quota Report

| Operation Type | Provider / Endpoint | Calls Made | Estimated Tokens | Cost (USD) |
|---|---|---|---|---|
| **Text Chunks Embedding** | Mistral (`api.mistral.ai`) | 5 | ~1,200 | < $0.001 |
| **LLM Entity Extraction** | OpenRouter (`openrouter.ai`) | 6 | ~7,500 | $0.000 (Free) |
| **Entity Embeddings** | Mistral (`api.mistral.ai`) | 22 | ~800 | < $0.001 |
| **Relation Embeddings** | Mistral (`api.mistral.ai`) | 3 | ~300 | < $0.001 |
| **Total Ingestion Budget** | — | **36 calls** | **~9,800 tokens** | **< $0.005** |

---

## 6. Verification & Test Outcomes

### Offline Pytest Unit Tests
- Total Passed: `[e.g. 8 / 8 passed (100%)]`
- Warnings: `0`
- Duration: `[e.g. 0.42s]`

### Retrieval & Anti-Hallucination Query Suite

| Query Description | User Query | Expected Grounded Fact | Actual Model Output | Status |
|---|---|---|---|---|
| **Direct Retrieval** | *"What vessel was involved in occurrence 4?"* | `ANVOURGON` | *"ANVOURGON, official number 4305..."* | **PASS** |
| **Multi-Field Synthesis**| *"What damage occurred and were there casualties?"* | Major damage; 0 casualties | *"Major damage to engine room; 0 deaths, 0 injuries..."* | **PASS** |
| **Negative / Unrecorded**| *"Who built the vessel ANVOURGON?"* | Not recorded | *"Shipbuilder information is not recorded in TSBC data..."* | **PASS** |

### Automated Browser Verification (Playwright)
- Target URL: `http://127.0.0.1:8000/#/Hyper/chat`
- Database Selected: `[e.g. tsbc_maritime_test]`
- "Thinking..." State Cleared: `[YES (within 6.2s)]`
- Browser Console Errors: `0`
- Network Failures: `0 (All HTTP 200)`
- Screenshot Artifacts: `[scratch/tsbc_db_selected.png, scratch/tsbc_query1_answered.png]`

---

## 7. Resolved Architectural Defects & Notes

1. **Defect 1**: `[e.g. Description of any bug encountered, root cause, and how it was fixed]`
2. **Defect 2**: `[e.g. Description of any bug encountered, root cause, and how it was fixed]`

---

## 8. Next Steps & Controlled Expansion Plan

- [ ] Complete 3-record dry-run (`test_3.jsonl`).
- [ ] Run 3-record indexing with multi-entity comparison queries.
- [ ] Plan batch size and rate-limit intervals for production partition.
