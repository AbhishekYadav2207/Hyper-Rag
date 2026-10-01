# Personal & Custom Data Integration Guide for Hyper-RAG

Welcome to the permanent engineering reference and procedural manual for onboarding custom, domain-specific, or personal datasets into the **Hyper-RAG** knowledge engine.

---

## START HERE (Under 2 Minutes)

If you are about to integrate a new personal or enterprise dataset into Hyper-RAG, here is what you need to know immediately:

1. **What is this directory?**  
   `documentation_personal_data/` is the permanent engineering manual explaining how to take raw, messy personal datasets (JSON, JSONL, CSV, Parquet, relational records, or documents), normalize them, design high-signal Hyper-RAG contexts, index them safely into isolated caches, query them through Adaptive RAG, and serve them via the WebUI.
2. **Why does it exist?**  
   It records the hard-won engineering decisions, bug fixes, and methodologies from our production integration of the **Transportation Safety Board of Canada (TSBC) Maritime Corpus**, turning that specific success into a universal, 10-level quota-safe workflow for **any future dataset**.
3. **What happened with TSBC?**  
   We audited 68,355 raw JSON lines (44,329 occurrences), performed deterministic 1-record representative selection (Occurrence ID: 4, vessel *ANVOURGON*), deduplicated nested equipment, decomposed records into 5 contextual perspectives, built an isolated 1024-dimensional Mistral vector and hypergraph index (`caches/tsbc_maritime_test`), resolved 3 critical bugs (package imports, UI `Thinking...` hang, and 1024 vs 1536 embedding mismatches), and verified end-to-end querying via Playwright browser automation with 0 hallucinations.
4. **Which document should I read first?**  
   - If you want the proven step-by-step recipe for *your* dataset: Read [02_GENERAL_PERSONAL_DATA_TO_HYPERRAG_WORKFLOW.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/02_GENERAL_PERSONAL_DATA_TO_HYPERRAG_WORKFLOW.md).
   - If you want to understand the historical debugging and what worked for TSBC: Read [01_COMPLETE_TSBC_INTEGRATION_HISTORY.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/01_COMPLETE_TSBC_INTEGRATION_HISTORY.md).
   - If you are ready to code right now: Copy [11_DATASET_ADAPTATION_CHECKLIST.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/11_DATASET_ADAPTATION_CHECKLIST.md) and start checking boxes.

---

## 5-Minute Technical Overview

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   YOUR CUSTOM RAW DATASET                              │
│   (JSON, JSONL, CSV, Database Export, API Responses, Mixed Docs)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Level 0: Quarantine & Schema Audit
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               LOCAL NORMALIZATION & DEDUPLICATION                      │
│   (Deterministic Python logic, Deduplicate Nested Keys, Provenance)    │
│   ZERO EXTERNAL API CALLS | ZERO LLM TOKEN CONSUMPTION                 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Level 1 & 2: Context Decomposition
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               FOCUSED HYPER-RAG PERSPECTIVE CONTEXTS                   │
│   (Semantic grouping: overview, profiles, environment, telemetry)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Level 3: Preflight Dry-Run Check
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               PREFLIGHT DRY-RUN ESTIMATION REPORT                      │
│   (Calculate chunks, token limits, verify embedding model & dim)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Level 4: Isolated 1-Record Indexing
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               ISOLATED HYPER-RAG KNOWLEDGE BASE                        │
│   caches/<dataset_name>_test/ (vdb_chunks, vdb_entities, .hgdb)        │
│   hyperrag_cache/<dataset_name>_test (Directory Junction for WebUI)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Level 5 to 7: Three-Tier Validation
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               RETRIEVAL & WEBUI VERIFICATION                           │
│   1. Direct Python API tests (Direct Fact, Multi-field, Negative test) │
│   2. FastAPI backend (/databases, /hyperrag/query)                     │
│   3. Interactive Web Console & Automated Browser Verification          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Level 8 & 9: Controlled Expansion
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               CONTROLLED 3-RECORD EXPANSION & SCALE-UP                 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Documentation Index

| File | Title & Scope | Primary Audience |
|---|---|---|
| [README.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/README.md) | **System Entry Point**: Overview, quickstart, roadmap, warnings | All developers & users |
| [CHANGELOG.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/CHANGELOG.md) | **Documentation Changelog**: History of revisions and maintenance rules | Maintainers |
| [01_COMPLETE_TSBC_INTEGRATION_HISTORY.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/01_COMPLETE_TSBC_INTEGRATION_HISTORY.md) | **TSBC Case Study**: Chronological account of the maritime corpus integration, audits, errors, and fixes | Deep technical study |
| [02_GENERAL_PERSONAL_DATA_TO_HYPERRAG_WORKFLOW.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/02_GENERAL_PERSONAL_DATA_TO_HYPERRAG_WORKFLOW.md) | **Universal Ingestion Lifecycle**: 10-level staged workflow for any personal dataset | Core architecture |
| [03_DATASET_INSPECTION_AND_NORMALIZATION.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/03_DATASET_INSPECTION_AND_NORMALIZATION.md) | **Data Cleaning & Schema Profiling**: Converting raw files into canonical structures | Data engineers |
| [04_DESIGNING_HYPERRAG_CONTEXTS.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/04_DESIGNING_HYPERRAG_CONTEXTS.md) | **Context Decomposition**: Slicing dense records into high-signal perspectives | Knowledge designers |
| [05_HYPERRAG_INDEXING_AND_EMBEDDINGS.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/05_HYPERRAG_INDEXING_AND_EMBEDDINGS.md) | **Vector Stores & Hypergraphs**: Embedding models, dimension matching, hypergraph DB | ML / Search engineers |
| [06_RETRIEVAL_AND_QUERY_FLOW.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/06_RETRIEVAL_AND_QUERY_FLOW.md) | **Query & Adaptive RAG Pipeline**: Phase 1 routing, Phase 2 sufficiency, Phase 3 validation | RAG developers |
| [07_WEBUI_INTEGRATION_AND_VERIFICATION.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/07_WEBUI_INTEGRATION_AND_VERIFICATION.md) | **Web Console Integration**: Database discovery, junctions, state management, browser testing | Frontend / Full-stack |
| [08_API_QUOTA_AND_COST_CONTROL.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/08_API_QUOTA_AND_COST_CONTROL.md) | **Cost & Quota Protection**: Strict guardrails, dry-run estimates, budget bounding | Operations / Tech leads |
| [09_TESTING_AND_VALIDATION.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/09_TESTING_AND_VALIDATION.md) | **Comprehensive Verification Suite**: Offline unit tests, negative anti-hallucination queries | QA / Validation |
| [10_EDGE_CASES_AND_TROUBLESHOOTING.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/10_EDGE_CASES_AND_TROUBLESHOOTING.md) | **Troubleshooting Field Guide**: Root causes, symptoms, and exact verified resolutions | Support / Debugging |
| [11_DATASET_ADAPTATION_CHECKLIST.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/11_DATASET_ADAPTATION_CHECKLIST.md) | **Adaptation Checklist**: Printable milestone tracker for new dataset onboarding | Project managers / devs |
| [12_REUSABLE_COMMAND_REFERENCE.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/12_REUSABLE_COMMAND_REFERENCE.md) | **Command Cheat Sheet**: Verified PowerShell & Bash execution strings | Everyday CLI use |
| [13_ARCHITECTURE_DIAGRAMS.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/13_ARCHITECTURE_DIAGRAMS.md) | **Architectural Blueprints**: Mermaid sequence diagrams, dataflows, and decision trees | System architects |
| [templates/](file:///d:/Rag/Hyper-RAG/documentation_personal_data/templates/) | **Reusable Markdown Templates**: Analysis, Mapping, Checklist, and Integration Report | Reusable deliverables |

---

## Critical Warnings & Guardrails

> [!CAUTION]
> **1. NEVER Index an Untested Raw Dataset in Bulk**  
> Hyper-RAG performs LLM entity extraction and text chunk embedding. Ingesting 10,000 unnormalized records without preflight bounding can exhaust API quotas in minutes and cost hundreds of dollars. Always enforce `max_records = 1` during initial onboarding.

> [!WARNING]
> **2. Embedding Dimensions MUST Match the Vector Store**  
> Hyper-RAG stores vectors in `vdb_chunks.json`, `vdb_entities.json`, and `vdb_relationships.json`. If your indexing used `mistral-embed` (1024 dimensions) and your runtime query uses `text-embedding-3-small` (1536 dimensions), vector cosine scoring will throw dimensional mismatch errors or silently produce invalid distance metrics. Verify [05_HYPERRAG_INDEXING_AND_EMBEDDINGS.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/05_HYPERRAG_INDEXING_AND_EMBEDDINGS.md) before building any index.

> [!IMPORTANT]
> **3. Always Use Isolated Caches (`caches/<dataset>_test`)**  
> Never write directly to `caches/default` or overwrite existing knowledge bases like `mock`. Build your knowledge base in an isolated folder and connect it to `hyperrag_cache/` using a filesystem junction so the WebUI auto-discovers it.

> [!TIP]
> **4. Mandatory Anti-Hallucination Testing**  
> A RAG system is only as good as its restraint. When validating your dataset, query for attributes that you *know* are absent from your source records. If your system invents an answer instead of stating "Not available / Not recorded", your prompt or context representation is broken.

---

## Distinguishing Dataset-Specific vs. Reusable Components

To ensure you never confuse TSBC-specific maritime artifacts with universal Hyper-RAG mechanics:

| Component / Layer | TSBC Maritime Implementation (Case Study) | Generic / Universal Standard (Any Dataset) |
|---|---|---|
| **Raw Input Schema** | `occurrence_id`, `OccNo`, `VesselName`, `lsa_equipment`, `navigation_equipment` | Arbitrary keys: `entity_id`, `user_id`, `timestamp`, `narrative`, `metadata` |
| **Normalization Script** | [datasets/tsbc_maritime/pipeline.py](file:///d:/Rag/Hyper-RAG/datasets/tsbc_maritime/pipeline.py) | [templates/DATASET_MAPPING_TEMPLATE.md](file:///d:/Rag/Hyper-RAG/documentation_personal_data/templates/DATASET_MAPPING_TEMPLATE.md) implemented in local Python |
| **Context Perspectives** | 5 maritime views: `occurrence_overview`, `vessel_profile`, `environmental_conditions`, `damage_and_safety`, `equipment_profile` | Domain views: e.g. financial (filing, metrics, risks), medical (patient, symptoms, lab, treatment) |
| **Representative Test Case** | Occurrence ID: 4 (*ANVOURGON*, explosion in engine room, major damage, 0 casualties) | A single deterministic record scoring highest on completeness and multi-perspective depth |
| **Cache Directory** | `caches/tsbc_maritime_test/` linked to `hyperrag_cache/tsbc_maritime_test/` | `caches/<dataset_name>_test/` linked to `hyperrag_cache/<dataset_name>_test/` |
| **Hyper-RAG Core Engine** | `HyperRAG.insert()`, `HypergraphDB`, `vdb_chunks.json`, `vdb_entities.json` | Identical for all datasets; 100% reusable engine |
| **Adaptive RAG Router** | Phase 1 complexity, Phase 2 sufficiency, Phase 3 validation | Identical for all datasets; auto-escalates Lite $\to$ Core |
| **Web Console UI** | Selects `tsbc_maritime_test` from header dropdown | Auto-discovers any folder inside `hyperrag_cache/` |
