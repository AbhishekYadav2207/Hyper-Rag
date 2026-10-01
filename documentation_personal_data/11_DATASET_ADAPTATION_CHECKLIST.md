# Document 11: Dataset Adaptation Checklist

Print or duplicate this checklist for every new personal, custom, or enterprise dataset you onboard into Hyper-RAG. Complete every milestone sequentially to prevent API cost overruns and system bugs.

---

## Phase 0: Pre-Flight Audit & Environment Setup

- [ ] **0.1 Verify Clean Git Working Tree**: Run `git status` to ensure repository has no uncommitted broken states.
- [ ] **0.2 Verify Hyper-RAG Environment**: Run `python -c "import hyperrag; print('HyperRAG OK')"` without import errors.
- [ ] **0.3 Source Corpus Quarantine**: Place raw dataset into a dedicated read-only path. Verify write permissions are disabled.
- [ ] **0.4 Inspect API Keys in `.env`**: Confirm valid keys for `OPENROUTER_API_KEY` and `EMB_API_KEY` / `MISTRAL_API_KEY`.
- [ ] **0.5 Verify Embedding Dimensions**: Confirm `EMB_MODEL=mistral-embed` and `EMB_DIM=1024` in `my_config.py`.

---

## Phase 1: Local Data Audit & Schema Profiling (Zero API Calls)

- [ ] **1.1 Execute Offline Syntax Audit**: Parse 100% of rows/lines. Confirm zero malformed lines and zero syntax crashes.
- [ ] **1.2 Document Total Record Metrics**: Log total lines, total distinct occurrences/entities, and file size in MB.
- [ ] **1.3 Identify Primary Key(s)**: Establish deterministic primary identifier (e.g. `occurrence_id`, `patient_id`, `ticket_no`).
- [ ] **1.4 Profile Field Sparsity**: Identify fields with $>80\%$ null values (e.g. builder, secondary telephone, optional notes).
- [ ] **1.5 Check Character Encodings**: Test French, Spanish, German, or CJK text to ensure UTF-8 compliance without CP1252 crashes.

---

## Phase 2: Normalization & Deduplication Engineering (Zero API Calls)

- [ ] **2.1 Implement `RecordNormalizer`**: Write deterministic local Python class to map raw fields to canonical schemas.
- [ ] **2.2 Implement Nested Array Deduplication**: Use composite key tuples to deduplicate repeated child objects.
- [ ] **2.3 Multi-Perspective Merging**: If records span multiple lines/perspectives, aggregate narratives by primary ID.
- [ ] **2.4 Preserve Strict Provenance**: Attach `source_file`, `source_id`, and `extracted_timestamp` to every output.
- [ ] **2.5 Offline Unit Tests**: Write unit tests in `tests/test_<dataset>.py` testing nulls, duplicates, and edge cases. Run `pytest`.

---

## Phase 3: Context Perspective Design & Decomposition (Zero API Calls)

- [ ] **3.1 Define 3 to 6 Semantic Perspectives**: Design domain views (Overview, Profiles, Environment/Telemetry, Outcomes).
- [ ] **3.2 Implement `ContextGenerator`**: Transform canonical dictionaries into natural factual prose paragraphs (150–350 words).
- [ ] **3.3 Enforce Primary Entity Anchoring**: Ensure entity names/IDs appear in the opening sentence of *every* perspective.
- [ ] **3.4 Explicit Negative Grounding**: Explicitly state *"Attribute X is not recorded"* for absent fields to prevent hallucinations.
- [ ] **3.5 Select Deterministic 1-Record Test Case**: Pick the single most complete record in the dataset. Save to `raw_reference/`.

---

## Phase 4: Dry-Run Estimation & Safety Limits (Zero API Calls)

- [ ] **4.1 Enforce Hardcoded Safety Limits**: Ensure CLI defaults to `max_records = 1` and `max_contexts = 5`.
- [ ] **4.2 Run Dry-Run Preflight**: Execute `python -m datasets.<dataset>.pipeline --dry-run`.
- [ ] **4.3 Inspect Preflight Report**:
  - `external_api_calls_made == 0`
  - `occurrences_selected == 1`
  - `estimated_text_chunks <= 10`
  - `embedding_dimension == 1024`

---

## Phase 5: Isolated 1-Record Indexing (Bounded API Calls)

- [ ] **5.1 Target Isolated Directory**: Ensure working directory is strictly `caches/<dataset_name>_test/`.
- [ ] **5.2 Execute Isolated Index**: Run `python -m datasets.<dataset>.pipeline --dataset <dataset_name>_test_1 --index`.
- [ ] **5.3 Verify Storage Files Created**:
  - `caches/<dataset_name>_test/hypergraph_chunk_entity_relation.hgdb` (vertices > 0, hyperedges > 0)
  - `caches/<dataset_name>_test/vdb_chunks.json` (vector length == 1024)
  - `caches/<dataset_name>_test/vdb_entities.json`
  - `caches/<dataset_name>_test/vdb_relationships.json`
- [ ] **5.4 Establish WebUI Directory Junction**: Create junction `hyperrag_cache/<dataset_name>_test` pointing to cache.

---

## Phase 6: Direct Retrieval & Anti-Hallucination Testing

- [ ] **6.1 Direct Fact Retrieval**: Query known attribute; assert exact entity name in response.
- [ ] **6.2 Multi-Field Synthesis**: Query combining 2 distinct perspectives; assert both facts are present.
- [ ] **6.3 Anti-Hallucination Negative Test**: Query an unrecorded attribute; assert response states "Not available / Not recorded".

---

## Phase 7: WebUI & Automated Browser Sign-Off

- [ ] **7.1 Launch FastAPI Server**: Run `python -m uvicorn web-ui.backend.main:app --port 8000`.
- [ ] **7.2 Verify Database Discovery**: Query `http://127.0.0.1:8000/databases`; assert custom database appears.
- [ ] **7.3 Browser Interactive Test**: Open `http://127.0.0.1:8000/#/Hyper/chat`, select database, submit query.
- [ ] **7.4 Verify "Thinking..." Transition**: Verify loading badge appears and cleanly clears upon completion.
- [ ] **7.5 Run Playwright Verification Script**: Capture screenshots (`db_selected.png`, `answered.png`). Verify 0 console errors.

---

## Phase 8: Controlled 3-Record Expansion

- [ ] **8.1 Extract 3 Representative Records**: Save to `raw_reference/<dataset_name>_test_3.jsonl`.
- [ ] **8.2 Run 3-Record Dry-Run**: Verify chunk and cost estimates for 3 records.
- [ ] **8.3 Execute 3-Record Indexing**: Run with `--max-records 3 --index`.
- [ ] **8.4 Relational Multi-Entity Querying**: Test cross-entity comparison queries. Verify zero cross-record entity bleeding.
- [ ] **8.5 Final Engineering Sign-off**: Fill out `DATASET_INTEGRATION_REPORT.md` and archive.
