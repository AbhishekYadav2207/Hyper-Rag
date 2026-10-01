# Document 01: Complete TSBC Integration History & Case Study

This document records the chronological engineering history of integrating the **Transportation Safety Board of Canada (TSBC) Maritime Occurrence Corpus** into the Hyper-RAG system. It serves as the definitive reference for how real-world complex data was audited, normalized, indexed, debugged, and verified.

---

## Citations & Verification Baseline

The facts, metrics, schemas, and debugging logs documented below are drawn directly from the following project artifacts:
- Source Corpus: `D:\CAIR\TSBC-MaritimePipeline\outputs\maritime_corpus.jsonl`
- Pipeline Implementation: [datasets/tsbc_maritime/pipeline.py](file:///d:/Rag/Hyper-RAG/datasets/tsbc_maritime/pipeline.py)
- Source Audit Script: `scratch/audit_tsbc_corpus.py` and output `scratch/audit_results.json`
- Candidate Scoring Script: `scratch/find_deterministic_candidates.py` and output `scratch/scored_candidates.json`
- Unit Test Suite: [tests/test_tsbc_maritime.py](file:///d:/Rag/Hyper-RAG/tests/test_tsbc_maritime.py)
- Browser Verification Script: [scratch/verify_tsbc_browser.py](file:///d:/Rag/Hyper-RAG/scratch/verify_tsbc_browser.py)
- WebUI Backend: [web-ui/backend/main.py](file:///d:/Rag/Hyper-RAG/web-ui/backend/main.py) and [web-ui/backend/db.py](file:///d:/Rag/Hyper-RAG/web-ui/backend/db.py)
- WebUI Frontend: [web-ui/frontend/src/pages/Home/index.tsx](file:///d:/Rag/Hyper-RAG/web-ui/frontend/src/pages/Home/index.tsx)
- Historical Guide: [docs/TSBC_MARITIME_HYPERRAG_GUIDE.md](file:///d:/Rag/Hyper-RAG/docs/TSBC_MARITIME_HYPERRAG_GUIDE.md)

---

## Phase 0 — Starting State of Hyper-RAG

Prior to the maritime integration, Hyper-RAG operated with the following baseline components:
1. **Mock Knowledge Base**: Located at `caches/mock/` and symlinked to `hyperrag_cache/mock/`. It contained Dickensian literary mock data (*A Christmas Carol*, Ebenezer Scrooge, Bob Cratchit) used for core algorithmic benchmarking.
2. **Adaptive RAG Engine**: A three-phase routing and sufficiency subsystem (`hyperrag/operate.py`):
   - **Phase 1**: Complexity scoring and Lite (vector-only) vs. Core (hypergraph + vector) routing.
   - **Phase 2**: Retrieval sufficiency evaluation with short-query semantic density bonuses (Phase 2.1) and automatic Lite $\to$ Core escalation.
   - **Phase 3**: Response validation checking completeness, relevance, and evidence grounding against retrieved passages.
3. **Embeddings & LLM Configuration**:
   - Embedding Model: `mistral-embed` (1024 dimensions, hosted at `https://api.mistral.ai/v1`) via `my_config.py`.
   - LLM: `nvidia/nemotron-3-ultra-550b-a55b:free` via OpenRouter (`https://openrouter.ai/api/v1`).
4. **Web Console**: A React + Vite single-page application served by a FastAPI backend (`web-ui/backend/main.py` on port 8000), offering Chat, Graph Visualization, DB Explorer, and File Management.

*Challenge*: We needed to ingest real, messy Canadian maritime incident records without corrupting existing mock data, without exhausting external API quotas, and while ensuring seamless selection within the existing WebUI.

---

## Phase 1 — Source Corpus Audit

### Location & Immutability
- **Corpus File**: `D:\CAIR\TSBC-MaritimePipeline\outputs\maritime_corpus.jsonl`
- **Integrity Rule**: The source corpus was strictly treated as read-only. No script was permitted to write, format, or truncate this file.

### Local Audit Execution
Before writing any ingestion logic, we executed an offline audit script (`scratch/audit_tsbc_corpus.py`) to parse every line without sending a single byte to an external API.

### Verified Audit Metrics
- **Total Lines Parsed**: `68,355` lines
- **JSON Validity**: 100% valid JSON (0 malformed lines, 0 syntax crashes)
- **Unique Occurrences (`occurrence_id`)**: `44,329`
- **Perspective Distribution**:
  - `occurrence_summary`: 40,510 records
  - `vessel_consolidated_narrative`: 27,845 records
- **Multi-Perspective Records**: Many occurrence IDs appeared twice—once summarizing the incident event, and once detailing vessel operations.

---

## Phase 2 — Schema Discovery

The audit exposed the deep nested structure of each JSON line:

```json
{
  "occurrence_id": 4,
  "document": "CREW RESCUED VESSEL TOWED TO HALIFAX AFTER FIRE IN ENGINE ROOM.",
  "provenance": {
    "perspective": "occurrence_summary",
    "pattern_id": "raw_tsb_summary",
    "spans": [{"rendered_span": "CREW RESCUED", "category": "narrative"}]
  },
  "structured": {
    "occurrence_id": 4,
    "occurrence": {
      "OccID": 4,
      "OccNo": "4",
      "OccClassDisplayEng": "FACT-FINDING",
      "OccDate": "1975-01-08 00:00:00.0000000",
      "OccTime": "19:00:00",
      "TimeZoneDisplayEng": "UTC",
      "OccTypeDisplayEng": "Accident",
      "AccIncTypeDisplayEng": "EXPLOSION",
      "Summary": "CREW RESCUED VESSEL TOWED TO HALIFAX AFTER FIRE IN ENGINE ROOM.",
      "SearchAndRescueIND_DisplayEng": "Yes",
      "DamageIND_DisplayEng": "Yes",
      "NearestLocationDescription": "ST LAWRENCE-GULF OF-RIVIERE AU RENARD-PRET DE",
      "Latitude": 49.0,
      "LatEnum_Bearing_DisplayEng": "N",
      "Longitude": 64.16666667,
      "LongEnum_Bearing_DisplayEng": "W",
      "RegionOfOccurrenceDisplayEng": "LAURENTIAN REGION",
      "WeatherConditionDisplayEng": "CLEAR",
      "SeaStateDisplayEng": "CALM (GLASSY) - 0 meters",
      "TotalDeaths": 0,
      "TotalMinorInjuries": 0,
      "TotalSeriousInjuries": 0,
      "TotalMissingIndividuals": 0
    },
    "vessels": [
      {
        "VesselID": 5,
        "VesselName": "ANVOURGON",
        "OfficialNo": "4305",
        "VesselTypeDisplayEng": "CARGO - SOLID",
        "VesselSubTypeDisplayEng": "GENERAL CARGO",
        "VesselFlagDisplayEng": "GREECE",
        "PortOfRegistryDisplayEng": "Piraeus",
        "GrossTonnage": 7266.0,
        "PropulsionTypeDisplayEng": "PROPELLER",
        "HullMaterialDisplayEng": "STEEL",
        "DeparturePortDisplayEng": "QUEBEC",
        "DestinationPortDisplayEng": "QUEBEC",
        "VesselDamageLocationCategoryDisplayEng": "Hull",
        "VesselDamageLocationSubCategoryDisplayEng": "Engineering Spaces",
        "VesselDamageLocationDisplayEng": "Engine room",
        "VesselDamageDegreeDisplayEng": "MAJOR",
        "lsa_equipment": [
          {"LsApplianceDisplayEng": "Lifeboat", "UsedEnumDisplayEng": "No"}
        ],
        "navigation_equipment": [
          {"NavigationAidTypeDisplayEng": "Magnetic compass", "OnOffEnumDisplayEng": "On"}
        ]
      }
    ]
  }
}
```

### Why Schema Discovery Must Precede Ingestion
1. **Nested Array Redundancy**: Equipment arrays (`lsa_equipment`, `navigation_equipment`) contained duplicate objects across perspectives.
2. **Missing Key Sparsity**: Fields like builder, IMO, and MMSI were absent or null in 98%+ of records. Feeding raw nested nulls creates sparse, noisy vectors.
3. **Disjoint Perspectives**: A single occurrence's narrative was split across multiple lines. Concatenating raw lines blindly resulted in duplicated vessel metadata and conflicting narrative snippets.

---

## Phase 3 — Normalization & Deduplication

We created `TSBCRecordNormalizer` in [datasets/tsbc_maritime/pipeline.py](file:///d:/Rag/Hyper-RAG/datasets/tsbc_maritime/pipeline.py) to execute purely local normalization:
1. **Multi-Perspective Merging**: All raw lines sharing an `occurrence_id` were aggregated. Narratives from `occurrence_summary` and `vessel_consolidated_narrative` were merged into a unified narrative catalog.
2. **Composite Tuple Deduplication**:
   - Life-saving appliances were deduplicated by `(LsApplianceDisplayEng, UsedEnumDisplayEng, ApprovedEnumDisplayEng)`.
   - Navigation aids were deduplicated by `(NavigationAidTypeDisplayEng, NavigationAidSubTypeDisplayEng, OnOffEnumDisplayEng)`.
3. **Provenance Preservation**: Maintained exact trace metadata: source file name, occurrence ID, vessel name, and original perspective names.
4. **Handling Missing Fields**: Null or unrecorded values were explicitly noted or omitted from prose synthesis to prevent hallucinations.
5. **Zero API Consumption**: This entire pipeline executed locally in standard Python without external network calls.

---

## Phase 4 — Representative Test Record Selection

Rather than indexing thousands of records, we implemented a deterministic 9-factor scoring function (`scratch/find_deterministic_candidates.py`):
1. Complete occurrence metadata (dates, times, timezone, classification)
2. Complete vessel attributes (name, flag, port of registry, tonnage)
3. Coordinates and regional geographic description
4. Documented environmental and sea state conditions
5. Specific damage degrees and anatomical damage locations
6. Documented Search and Rescue (SAR) operations
7. Populated life-saving appliances (LSA)
8. Populated navigation equipment
9. Dual perspectives present in raw corpus

### The Chosen Record: Occurrence ID 4
- **Vessel Involved**: `ANVOURGON` (Official No: 4305, Flag: GREECE, Registry: Piraeus, 7,266 GT)
- **Incident Date/Time**: 1975-01-08 at 19:00 UTC (Laurentian Region, near Rivière-au-Renard)
- **Incident**: Explosion followed by a major fire in the engine room.
- **Casualties**: Exactly 0 fatalities, 0 serious injuries, 0 minor injuries, 0 missing individuals.
- **Rescue & Aftermath**: Crew rescued by Search & Rescue; vessel towed to Halifax.
- **Absent Fields**: Shipbuilder name, IMO number, MMSI. (Deliberately used for negative anti-hallucination verification).

*Note*: Occurrence 4 was saved to `datasets/tsbc_maritime/raw_reference/tsbc_maritime_test_1.jsonl`.

---

## Phase 5 — Context Perspective Design

Rather than dumping a single unstructured JSON blob into Hyper-RAG, we decomposed Occurrence 4 into **five semantically focused perspectives** (`TSBCContextGenerator`):

1. `occurrence_overview`: Chronology, incident type (Explosion/Fire), region, coordinates, and official classification.
2. `vessel_profile`: Vessel name (*ANVOURGON*), official number, flag, port of registry, tonnage, hull material, propulsion.
3. `environmental_conditions`: Clear weather, calm glassy sea (0 meters), wind conditions.
4. `damage_and_safety`: Major engine room damage, vessel towed to Halifax, SAR deployment, zero casualties.
5. `equipment_profile`: Operational magnetic compass, lifeboats on standby.

### Why Context Decomposition Succeeded
- **Targeted Embeddings**: Chunks matched specific queries (e.g. "What was the weather?" retrieved `environmental_conditions` directly without vessel spec noise).
- **Hypergraph Density**: Entities (*ANVOURGON*, *Laurentian Region*, *Halifax*, *Engine Room*) were linked cleanly across the 5 perspectives via shared hyperedges.
- **Bounded Size**: Each perspective generated ~120 to 250 words—the optimal token length for `mistral-embed`.

---

## Phase 6 — Isolated Hyper-RAG Index

### Directory Isolation
- Index Path: `caches/tsbc_maritime_test/`
- Directory Junction: `hyperrag_cache/tsbc_maritime_test`
- No contamination of `caches/mock` or `caches/default`.

### Indexing Execution
Command:
```powershell
python -m datasets.tsbc_maritime.pipeline --dataset tsbc_maritime_test_1 --index
```

### Verified Index Artifacts Built
- `caches/tsbc_maritime_test/hypergraph_chunk_entity_relation.hgdb`: **22 vertices, 3 hyperedges**
- `caches/tsbc_maritime_test/vdb_chunks.json`: Vector index for text chunks (1024-dim)
- `caches/tsbc_maritime_test/vdb_entities.json`: Vector index for extracted maritime entities
- `caches/tsbc_maritime_test/vdb_relationships.json`: Vector index for semantic relations
- `caches/tsbc_maritime_test/kv_store_full_docs.json`: Raw text storage
- `caches/tsbc_maritime_test/kv_store_text_chunks.json`: Chunk storage

### Verified Project Configuration
- **Embedding Model**: `mistral-embed`
- **Embedding Dimension**: `1024`
- **Embedding Base URL**: `https://api.mistral.ai/v1`
- **LLM**: `nvidia/nemotron-3-ultra-550b-a55b:free` via OpenRouter

---

## Phase 7 — WebUI Integration

1. **Discovery**: `web-ui/backend/db.py` implements `DatabaseManager.list_databases()`, which scans `hyperrag_cache/`. Because `hyperrag_cache/tsbc_maritime_test` was linked via Windows junction (`mklink /J`), it was instantly discovered.
2. **Selection**: The WebUI header dropdown exposed `tsbc_maritime_test`.
3. **Execution**: Frontend sends `POST /hyperrag/query` with payload `{"query": "...", "mode": "adaptive", "database": "tsbc_maritime_test"}`.
4. **Adaptive Routing**: Evaluated complexity and retrieved relevant hyperedges and entity vertices before synthesizing the answer.

---

## Phase 8 — Problems Encountered & Exact Fixes

During the integration, three critical defects were uncovered and resolved.

### Problem A: Backend Import Failure (`ModuleNotFoundError: No module named 'db'`)
- **Symptom**: Starting the FastAPI server via `uvicorn web-ui.backend.main:app` crashed on startup with:
  ```text
  ModuleNotFoundError: No module named 'db'
  ```
- **Cause**: In `web-ui/backend/main.py`, imports were written as top-level imports (`from db import ...`, `from file_manager import ...`). When executed as a package module (`web-ui.backend.main:app`), Python could not resolve `db` in the global namespace.
- **Diagnosis**: Checked `sys.path` and package structure. The files resided in `web-ui/backend/`.
- **Fix** (Commit `ec5dd47e`): Updated `web-ui/backend/main.py` lines 5-6 to use explicit relative package imports:
  ```python
  from .db import get_hypergraph, getFrequentVertices, ...
  from .file_manager import file_manager
  ```
- **Verification**: Uvicorn started cleanly on port 8000 without import errors.

---

### Problem B: WebUI Permanently Stuck on "Thinking..."
- **Symptom**: Submitting queries in the WebUI displayed the Adaptive Decision badge showing `"Thinking..."` indefinitely, even though backend logs confirmed `POST /hyperrag/query HTTP/1.1 200 OK` and returned the full answer.
- **Diagnosis & Root Cause** (Commit `453928c5`):
  1. *State Assignment Drop*: In `web-ui/frontend/src/pages/Home/index.tsx`, the `updateLastMessage(content, extraData)` function updated metadata (`entities`, `hyperedges`), but neglected to assign `content` into the updated message object. The message content remained initialized to the placeholder `'Thinking...'`.
  2. *Response Key Mismatch*: The backend returned `{"response": result.get("response")}`, but parts of the frontend expected `data.answer` or `data.response`.
  3. *Unprotected Loading Guard*: `setIsLoading(false)` was outside of a `try ... finally` block; any intermediate error left the spinner spinning forever.
- **Fix**:
  1. In `Home/index.tsx`:
     ```typescript
     content: content !== undefined && content !== null ? content : msg.content
     ```
  2. Supported fallback `data.response || data.answer || 'No response content'`.
  3. Wrapped queries in `try ... catch ... finally { setIsLoading(false) }`.
  4. In `web-ui/backend/main.py`, returned both keys:
     ```python
     return {"success": True, "response": resp, "answer": resp, ...}
     ```
  5. Rebuilt static assets (`npm run build`).
- **Verification**: Verified via Playwright in [scratch/verify_tsbc_browser.py](file:///d:/Rag/Hyper-RAG/scratch/verify_tsbc_browser.py). The "Thinking..." indicator vanished within ~5-10 seconds and rendered full prose.

---

### Problem C: Embedding Dimension Mismatch (Stored: 1024 vs. Query: 1536)
- **Symptom**: Queries crashed with vector cosine similarity dimension errors or silently failed to match any vectors.
- **Cause**: The index in `caches/tsbc_maritime_test/` was built with `mistral-embed` (1024 dimensions). However, `settings.json` and older backend fallbacks contained `text-embedding-3-small` (1536 dimensions). When querying, `get_hyperrag_embedding_func()` generated a 1536-dimensional vector to query a 1024-dimensional database.
- **Diagnosis**: Checked vector keys in `vdb_chunks.json` (length 1024) vs. runtime query vector length (1536).
- **Fix** (Commit `453928c5`):
  1. Standardized `settings.example.json` and `my_config.py` on `mistral-embed` with `EMB_DIM=1024`.
  2. Added runtime normalization in `web-ui/backend/main.py`:
     ```python
     if saved.get("embeddingModel") in ("text-embedding-3-small", None) or saved.get("embeddingDim") in (1536, None):
         saved["embeddingModel"] = "mistral-embed"
         saved["embeddingDim"] = 1024
         saved["embeddingBaseUrl"] = "https://api.mistral.ai/v1"
     ```
  3. In `get_hyperrag_embedding_func()`, enforced `EMB_API_KEY` and Mistral endpoints.
- **Verification**: Vector queries matched 1024-dimensional entries with zero dimension mismatch warnings.

---

## Phase 9 — Comprehensive Testing & Outcomes

Testing followed a rigorous offline-to-online progression:

### 1. Offline Pytest Suite (Zero API Calls)
Command:
```powershell
pytest tests/test_tsbc_maritime.py -v
```
**Result**: 8 tests passed in 0.42s:
- `test_normalization_basic`: PASS
- `test_deduplication_equipment`: PASS (duplicate lifeboats & compasses cleaned)
- `test_multi_perspective_merging`: PASS
- `test_generate_contexts`: PASS (5 distinct perspectives generated)
- `test_no_synthetic_facts`: PASS (no fabricated fields)
- `test_safety_guard_record_limit`: PASS (prevented multi-record ingestion)
- `test_dry_run_zero_api_calls`: PASS
- `test_data_edge_cases`: PASS (nulls, missing vessels, unicode French accents)

### 2. Live WebUI Automated Browser Verification
Automated via Playwright (`scratch/verify_tsbc_browser.py`) running headless Chrome:
- **Query 1 (Direct Retrieval)**:  
  *Question*: "What vessel was involved in maritime occurrence 4?"  
  *Result*: Confirmed **`ANVOURGON`** (Greek cargo vessel, 7,266 GT). Verified in `scratch/tsbc_query1_answered.png`.
- **Query 2 (Multi-Field Damage & Safety)**:  
  *Question*: "What damage was reported for maritime occurrence 4 and were there any casualties?"  
  *Result*: Confirmed major damage to Engine Room and vessel towed to Halifax; confirmed **0 fatalities, 0 injuries**. Verified in `scratch/tsbc_query2_answered.png`.
- **Query 3 (Anti-Hallucination Negative Fact)**:  
  *Question*: "Who was the builder of the vessel ANVOURGON?"  
  *Result*: Stated explicitly that builder information is **not recorded / unavailable** in TSBC records. Verified in `scratch/tsbc_query3_answered.png`.
- **Console & Network**: Clean console (0 errors, 0 warnings), HTTP 200 on all `/hyperrag/query` calls.
