# Template: Integration Checklist

A blank, printable checklist for tracking custom dataset onboarding into Hyper-RAG.

---

## Dataset: `[Insert Dataset Identifier]`
**Date Started**: `[YYYY-MM-DD]`  
**Lead Engineer**: `[Name]`  
**Source Path**: `[Path to raw data]`  

---

### Phase 1: Pre-Ingestion Setup & Discovery
- [ ] Source corpus quarantined in read-only path.
- [ ] Offline syntax audit completed (0 malformed lines).
- [ ] Schema profiling report created (`reports/audit_report.json`).
- [ ] Primary key and unique record count confirmed.
- [ ] Environment verified: `python -c "import hyperrag; print('OK')"`.
- [ ] Model verified: `mistral-embed` (1024-dim) in `my_config.py`.

### Phase 2: Normalization & Context Design
- [ ] `RecordNormalizer` implemented in pure Python (0 API calls).
- [ ] Composite tuple deduplication implemented for child arrays.
- [ ] Full provenance dictionary preserved on each record.
- [ ] 3–6 semantic perspectives defined.
- [ ] Explicit negative statements added for null fields.
- [ ] Deterministic 1-record test case selected and saved to `raw_reference/`.

### Phase 3: Dry-Run & Offline Testing
- [ ] Offline unit test suite created (`tests/test_<dataset>.py`).
- [ ] Unit tests pass: `pytest tests/test_<dataset>.py -v`.
- [ ] Hardcoded safety limits verified (`max_records = 1`, `max_contexts = 5`).
- [ ] Dry-run executed: `python -m datasets.<dataset>.pipeline --dry-run`.
- [ ] Preflight report verified: `external_api_calls_made == 0`.

### Phase 4: Isolated Indexing & Verification
- [ ] Isolated cache targeted (`caches/<dataset>_test/`).
- [ ] Indexing executed: `python -m datasets.<dataset>.pipeline --index`.
- [ ] Verified `.hgdb` exists with vertices > 0 and hyperedges > 0.
- [ ] Verified `vdb_chunks.json` contains 1024-dimensional vectors.
- [ ] Directory junction created at `hyperrag_cache/<dataset>_test`.

### Phase 5: Query & WebUI Sign-Off
- [ ] Direct Python test query 1 (known fact) returns expected entity.
- [ ] Direct Python test query 2 (multi-field) returns combined facts.
- [ ] Direct Python test query 3 (negative fact) refuses hallucination.
- [ ] FastAPI backend started on port 8000.
- [ ] WebUI header dropdown discovers and selects database.
- [ ] Automated Playwright test verifies clean console and thinking state.
- [ ] Integration report filled out and archived.
