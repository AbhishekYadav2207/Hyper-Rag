# Document 02: General Personal Data → Hyper-RAG Workflow

This is the central operational manual of the documentation system. It translates our historical TSBC maritime experience into a **reusable, 10-level quota-safe lifecycle** for taking **ANY custom or personal dataset** and integrating it into Hyper-RAG with zero hallucinations, minimal cost, and full WebUI support.

---

## 1. High-Level Ingestion Lifecycle

```text
  [Raw Custom Dataset]
          │
          ▼  Level 0: Quarantine & Offline Audit (0 API calls)
  [Schema Profile & Discovered Data Types]
          │
          ▼  Level 1: Canonical Normalization & Deduplication (0 API calls)
  [Clean Canonical Records with Provenance]
          │
          ▼  Level 2: Semantic Context Decomposition (0 API calls)
  [High-Signal Context Micro-Documents]
          │
          ▼  Level 3: Deterministic 1-Record Selection & Dry-Run (0 API calls)
  [Preflight Cost & Token Estimate Report]
          │
          ▼  Level 4: Isolated 1-Record Hyper-RAG Indexing (Bounded API calls)
  [Isolated Knowledge Base: caches/<dataset>_test/]
          │
          ▼  Level 5: Direct Python API Retrieval & Negative Testing
  [Grounded Fact & Anti-Hallucination Sign-off]
          │
          ▼  Level 6: Directory Junction Link & WebUI Verification
  [Active Custom Database in Web Console]
          │
          ▼  Level 7: Automated Browser Validation (Playwright)
  [Verified UI Rendering & Clean Console]
          │
          ▼  Level 8: Controlled 3-Record Expansion
  [Multi-Entity Relational Benchmark]
          │
          ▼  Level 9: Full Production-Scale Ingestion
  [Scaled Knowledge Base]
```

---

## 2. Stage-by-Stage Detailed Engineering Specification

---

### Level 0: Quarantine & Offline Schema Audit

- **Purpose**: Understand the exact format, field types, nested hierarchies, record counts, and edge cases of the raw dataset without modifying it.
- **Inputs**: Raw source file (JSON, JSONL, CSV, Parquet, SQLite dump).
- **Outputs**: Audit report document (`reports/audit_report.json`), record counts, list of unique keys, identified primary keys.
- **API Calls Required**: **NO (0 external API calls)**.
- **What Can Go Wrong**:
  - Script attempts to load a 10 GB file directly into memory using `json.load()` and crashes with `MemoryError`.
  - Non-UTF-8 character encodings (e.g. CP1252, Latin-1) cause decoding crashes.
  - Inconsistent schemas where 10% of lines have missing top-level keys.
- **Verification Before Proceeding**:
  - [ ] 100% of rows parse as valid syntax without crashes.
  - [ ] Total lines and unique record IDs are documented.
  - [ ] Source file permissions are verified as strictly read-only.

---

### Level 1: Canonical Normalization & Deduplication

- **Purpose**: Convert raw, irregular, or multi-perspective source records into a clean canonical Python dictionary. Deduplicate redundant nested entities (e.g. repeated equipment, redundant contact objects).
- **Inputs**: Raw records grouped by canonical primary identifier (`occurrence_id`, `patient_id`, `transaction_id`, `case_id`).
- **Outputs**: `normalized/<dataset_name>_normalized.json` containing standardized records.
- **API Calls Required**: **NO (0 external API calls)**.
- **What Can Go Wrong**:
  - LLM is used unnecessarily for formatting, burning API budget and introducing synthetic hallucinations.
  - Primary keys are not unique, causing accidental overwriting of distinct entities.
  - Deduplication logic uses loose string matching, merging distinct records.
- **Verification Before Proceeding**:
  - [ ] Deduplication executed deterministically via composite key tuples.
  - [ ] Exact provenance metadata (original source file, original row numbers, perspective IDs) is attached to every normalized record.
  - [ ] Unit tests pass offline (`pytest`).

---

### Level 2: Semantic Context Decomposition

- **Purpose**: Deconstruct a dense record into 3 to 6 focused, semantic prose perspectives instead of dumping one giant JSON blob or single long paragraph into the chunker.
- **Inputs**: Normalized record dictionary.
- **Outputs**: `contexts/<dataset_name>_contexts.json` containing a list of context objects, each with `context_type`, `entity_id`, and `text`.
- **API Calls Required**: **NO (0 external API calls)**.
- **What Can Go Wrong**:
  - Perspectives are too small (<30 words), causing fragmental chunking.
  - Perspectives are too long (>1000 words), causing embedding dilution.
  - Absent/null fields are filled with guessed text instead of stating "Not available / Not recorded".
- **Verification Before Proceeding**:
  - [ ] Each perspective has a clear semantic purpose (e.g. Overview, Profile, Telemetry, Safety).
  - [ ] Every context contains explicit anchor entities (names, IDs) so Hyper-RAG's entity extractor links them.
  - [ ] Missing values are explicitly represented as "Not recorded" to prime negative-query handling.

---

### Level 3: Deterministic 1-Record Selection & Preflight Dry-Run

- **Purpose**: Select the single most complete, multi-perspective record in the dataset as your initial test case. Calculate text lengths, chunk estimates, embedding operations, and LLM extraction costs *before* issuing any network requests.
- **Inputs**: Extracted 1-record raw slice (`raw_reference/<dataset_name>_test_1.jsonl`).
- **Outputs**: Preflight estimation report (`reports/<dataset_name>_dry_run_report.json`).
- **API Calls Required**: **NO (0 external API calls)**.
- **What Can Go Wrong**:
  - Developer skips dry-run and triggers an unconstrained batch run on 50,000 records.
  - Incompatible embedding model or dimension in config goes unnoticed until the run fails halfway.
- **Verification Before Proceeding**:
  - [ ] `estimated_text_chunks` is under 10.
  - [ ] `embedding_dimension` matches current project config (`1024` for Mistral).
  - [ ] `external_api_calls_made == 0` is confirmed in report.

---

### Level 4: Isolated 1-Record Hyper-RAG Indexing

- **Purpose**: Index the 1-record test dataset into an isolated working directory. Build the chunk vectors, entity vectors, relationship vectors, and hypergraph database.
- **Inputs**: 1-record context texts, configured embedding function (`mistral-embed`), configured LLM function (`nemotron`).
- **Outputs**:
  - `caches/<dataset_name>_test/hypergraph_chunk_entity_relation.hgdb`
  - `caches/<dataset_name>_test/vdb_chunks.json`
  - `caches/<dataset_name>_test/vdb_entities.json`
  - `caches/<dataset_name>_test/vdb_relationships.json`
- **API Calls Required**: **YES (Strictly bounded: ~3-6 embedding calls, ~5-10 LLM extraction calls)**.
- **What Can Go Wrong**:
  - Indexing executes against `caches/default` and pollutes the primary knowledge base.
  - Embedding dimensions mismatch (1024 vs 1536).
  - Safety guard fails to stop multi-record ingestion.
- **Verification Before Proceeding**:
  - [ ] Safety guard `max_records=1` successfully enforced.
  - [ ] Hypergraph `.hgdb` file exists and has >0 vertices and >0 hyperedges.
  - [ ] All vector files exist and contain 1024-dimensional vectors.

---

### Level 5: Direct Python API Retrieval & Negative Testing

- **Purpose**: Validate that the indexing created accessible, grounded knowledge before involving any frontend UI. Test both positive facts and negative (unrecorded) facts.
- **Inputs**: Local Python test script, queries targeting the test record.
- **Outputs**: Retrieved text units, hyperedges, and synthesized LLM answers.
- **API Calls Required**: **YES (~1 embedding call + 1 LLM call per test query)**.
- **What Can Go Wrong**:
  - Retrieval returns empty text units because vector distance threshold is too strict.
  - Model hallucinates answers for unrecorded fields instead of admitting absence.
- **Verification Before Proceeding**:
  - [ ] Direct query returns exact factual details (e.g. Vessel name, incident date).
  - [ ] Multi-field query correctly combines facts across multiple perspectives.
  - [ ] Negative query (asking for an unrecorded field) correctly returns "Not available / Not recorded".

---

### Level 6: Directory Junction Link & WebUI Integration

- **Purpose**: Make the newly indexed knowledge base discoverable by the FastAPI server and selectable in the Web Console.
- **Inputs**: Isolated cache directory `caches/<dataset_name>_test`.
- **Outputs**: Windows directory junction or symlink at `hyperrag_cache/<dataset_name>_test`.
- **API Calls Required**: **NO (0 external API calls)**.
- **What Can Go Wrong**:
  - The WebUI cannot find the database because it was created in `caches/` without being linked in `hyperrag_cache/`.
  - Directory junction fails due to filesystem permissions.
- **Verification Before Proceeding**:
  - [ ] `GET http://127.0.0.1:8000/databases` lists `<dataset_name>_test`.
  - [ ] WebUI header dropdown displays `<dataset_name>_test`.

---

### Level 7: Interactive & Automated Browser Verification

- **Purpose**: Verify that real user interactions work seamlessly through the React frontend without UI hangs, console crashes, or formatting bugs.
- **Inputs**: Headless Playwright script (`scratch/verify_<dataset>_browser.py`) or manual browser session.
- **Outputs**: Screenshots (`thinking_state.png`, `answered_state.png`), network logs, console logs.
- **API Calls Required**: **YES (1 call per submitted browser query)**.
- **What Can Go Wrong**:
  - Frontend message state drops content, permanently sticking on `"Thinking..."`.
  - Backend response key mismatch (`response` vs `answer`) causes empty bubbles.
  - Console shows unhandled promise rejections or CORS errors.
- **Verification Before Proceeding**:
  - [ ] "Thinking..." badge appears on submit and clears when the response arrives.
  - [ ] Full prose answer renders cleanly in the chat view.
  - [ ] Browser console has 0 errors and 0 warnings.

---

### Level 8: Controlled 3-Record Expansion

- **Purpose**: Prove that Hyper-RAG scales from a single entity to multiple distinct entities without cross-contamination or relational collisions.
- **Inputs**: 3-record raw dataset (`raw_reference/<dataset_name>_test_3.jsonl`).
- **Outputs**: Expanded index with multiple distinct entities and hyperedges.
- **API Calls Required**: **YES (Bounded: ~15-30 embedding calls, ~20-30 LLM calls)**.
- **What Can Go Wrong**:
  - Entities from Record A bleed into answers for Record B.
  - Token consumption exceeds expectations due to explosive cross-referencing.
- **Verification Before Proceeding**:
  - [ ] Comparative queries correctly distinguish between the 3 records.
  - [ ] Queries for Record A do not mention entities unique to Record B.
  - [ ] Pytest and browser verification suites pass with 3 records.

---

### Level 9: Production-Scale Ingestion

- **Purpose**: Ingest large-scale production datasets in budgeted, checkpointed batches.
- **Inputs**: Full dataset or large designated partition.
- **Outputs**: Production knowledge base.
- **API Calls Required**: **YES (High volume; requires budget limits and checkpointing)**.
- **What Can Go Wrong**:
  - API rate limits (HTTP 429) crash an un-checkpointed 10-hour run at 90%.
  - Cost runaway due to uncapped context sizes.
- **Verification Before Proceeding**:
  - [ ] Batch size is locked (e.g. 50-100 records per batch).
  - [ ] Checkpoint store is enabled so completed batches are never re-indexed.
  - [ ] Multi-key rotation or exponential backoff is active in `my_config.py`.

---

## 3. "How to Integrate My Next Dataset" Quickstart (22 Steps)

Follow this exact sequence when onboarding any new dataset tomorrow:

1. **Verify Environment**: Run `python -c "import hyperrag; print('HyperRAG OK')"` from repo root.
2. **Quarantine Source File**: Place raw source file in a designated read-only location.
3. **Audit Format & Syntax**: Run an offline parsing script to check 100% of lines/rows.
4. **Profile Schema**: Identify top-level keys, nested arrays, data types, and primary identifiers.
5. **Identify Unique Record ID**: Choose or construct a deterministic primary key (`record_id`).
6. **Identify Entities & Relationships**: Note names, places, organizations, or codes to track.
7. **Write Local Normalizer**: Implement pure Python class `RecordNormalizer` (0 API calls).
8. **Deduplicate Nested Objects**: Write tuple-based deduplication for arrays and child lists.
9. **Preserve Provenance**: Carry `source_file`, `source_row`, and `original_ids` into output dictionary.
10. **Design Context Perspectives**: Define 3-6 semantic perspectives (Overview, Details, Telemetry, etc.).
11. **Write Context Generator**: Convert normalized dictionaries into clear, factual paragraphs.
12. **Select 1 Representative Record**: Deterministically pick the most complete record in the corpus.
13. **Extract 1-Record Test File**: Save to `raw_reference/<dataset>_test_1.jsonl`.
14. **Run Dry-Run Estimation**: Run pipeline with `--dry-run`; inspect generated report.
15. **Verify Embedding Dimensions**: Confirm `EMB_DIM=1024` and `EMB_MODEL=mistral-embed`.
16. **Build Isolated 1-Record Index**: Run pipeline with `--index` targeting `caches/<dataset>_test/`.
17. **Verify Storage Files**: Confirm `.hgdb`, `vdb_chunks.json`, `vdb_entities.json` exist.
18. **Create Directory Junction**: Ensure `hyperrag_cache/<dataset>_test` links to `caches/<dataset>_test`.
19. **Run Offline Pytest Suite**: Execute unit tests verifying normalization, deduplication, and safety limits.
20. **Test Positive & Negative Queries**: Run direct Python queries for known facts and unrecorded facts.
21. **Verify in Web Console**: Start FastAPI backend, open `http://127.0.0.1:8000`, select database, query in UI.
22. **Automated Browser Sign-off**: Run Playwright script to verify clean console, thinking state, and prose response.

---

## 4. Practical Engineering Lessons Learned

1. **Inspect Data Before Writing Ingestion Code**: You cannot design clean contexts if you do not understand the shape and noise of your source records.
2. **Never Use an LLM for Preprocessing**: Normalization, deduplication, and filtering must be deterministic Python code. Using an LLM to clean data is slow, expensive, and introduces ungrounded artifacts.
3. **Start with Exactly 1 Record**: Indexing 1 record tests 100% of your architectural plumbing (chunking, embeddings, hypergraph, storage, API endpoints, WebUI) for pennies.
4. **Preserve Strict Provenance**: If an answer in the WebUI looks strange, you must be able to trace it back to the exact source row and perspective that generated it.
5. **Use Strictly Isolated Caches**: Never point a new dataset at `caches/default` or `caches/mock`. Always create a fresh, dedicated cache folder.
6. **Verify Embedding Dimensions Before Indexing**: Mismatched dimensions (e.g. 1024 index vs 1536 query) cause catastrophic runtime failures.
7. **Always Test Unknown Questions**: A model that cannot say "I do not know" or "This information is not recorded" cannot be trusted in production.
8. **Do Not Trust HTTP 200 Alone**: In our WebUI debugging, the backend returned HTTP 200 with the full answer, but the UI was permanently frozen on "Thinking..." due to a frontend state bug. Always test the full user journey.
9. **Use Backend Logs and Browser DevTools Concurrently**: Diagnostic visibility requires monitoring Uvicorn terminal logs, the browser Console tab, and the Network tab simultaneously.
10. **Enforce Hard Limits in Code**: Hardcode `max_records = 1` as the default argument in your pipeline CLI to prevent accidental ingestion disasters.
