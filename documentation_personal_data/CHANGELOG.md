# Documentation Changelog

This changelog records all updates, enhancements, and architectural modifications made to the `documentation_personal_data/` system.

---

## Maintenance Guidelines for Maintainers

1. **Keep in Sync with Repository Code**: Whenever changes are made to `hyperrag/`, `datasets/`, `web-ui/backend/`, or `my_config.py`, check this documentation system to ensure commands, configuration keys, and workflows remain 100% accurate.
2. **Never Commit Secrets**: Ensure placeholder formats (`<OPENROUTER_API_KEY>`, `<MISTRAL_API_KEY>`) are maintained.
3. **Verify Git Tracking**: Ensure `.gitignore` continues to track `documentation_personal_data/` and does not silently ignore templates or markdown files.
4. **Log Changes Promptly**: Add an entry below whenever a document is modified or a new dataset case study is added.

---

## [1.0.0] - 2026-10-01

### Added
- **Initial Release of Personal Data Documentation System**:
  - `README.md`: Entry point, under 2-minute summary, 5-minute overview, documentation index, and distinction table between dataset-specific and generic mechanics.
  - `01_COMPLETE_TSBC_INTEGRATION_HISTORY.md`: Chronological reconstruction of the TSBC maritime integration across 9 phases, covering schema audit, deterministic selection of Occurrence 4, normalization, context decomposition, isolated indexing, and detailed debugging history of 3 critical bugs (`ModuleNotFoundError: No module named 'db'`, WebUI `Thinking...` hang, and 1024 vs 1536 embedding dimension mismatch).
  - `02_GENERAL_PERSONAL_DATA_TO_HYPERRAG_WORKFLOW.md`: Universal 10-level ingestion lifecycle for onboarding any personal or domain dataset safely.
  - `03_DATASET_INSPECTION_AND_NORMALIZATION.md`: Practical guide to format parsing (JSON, JSONL, CSV, Parquet), schema discovery, null handling, nested deduplication, and provenance preservation.
  - `04_DESIGNING_HYPERRAG_CONTEXTS.md`: Semantic context decomposition methodology, showing how to slice complex domain records into high-signal perspectives across maritime, finance, healthcare, legal, and engineering domains.
  - `05_HYPERRAG_INDEXING_AND_EMBEDDINGS.md`: Hyper-RAG indexing engine breakdown (`vdb_chunks.json`, `vdb_entities.json`, `vdb_relationships.json`, `.hgdb`), embedding model configuration (`mistral-embed`, 1024 dimensions), and dimensional alignment rules.
  - `06_RETRIEVAL_AND_QUERY_FLOW.md`: Complete query execution lifecycle, FastAPI `/hyperrag/query` interface, Adaptive RAG 3-phase execution (complexity routing, retrieval sufficiency, response validation), and retrieval failure diagnosis.
  - `07_WEBUI_INTEGRATION_AND_VERIFICATION.md`: Web console integration, database discovery via directory junctions, API contract harmonization (`data.response` vs `data.answer`), and Playwright browser verification workflows.
  - `08_API_QUOTA_AND_COST_CONTROL.md`: Staged quota protection guide, dry-run cost calculations, strict safety parameters (`max_records=1`, `max_contexts=5`), and the "NEVER DO THIS" operational rules.
  - `09_TESTING_AND_VALIDATION.md`: Multi-layer validation framework covering data edge cases, transformation fidelity, index integrity, negative anti-hallucination queries, and automated browser testing.
  - `10_EDGE_CASES_AND_TROUBLESHOOTING.md`: Systematic troubleshooting field guide detailing symptoms, root causes, confirmation steps, and verified fixes for all encountered errors.
  - `11_DATASET_ADAPTATION_CHECKLIST.md`: Printable, actionable checklist for engineering teams onboarding new datasets.
  - `12_REUSABLE_COMMAND_REFERENCE.md`: Verified CLI execution strings for Windows PowerShell and Linux Bash.
  - `13_ARCHITECTURE_DIAGRAMS.md`: Mermaid sequence diagrams, data flows, and diagnostic decision trees.
  - `templates/DATASET_ANALYSIS_TEMPLATE.md`: Reusable audit template for new incoming raw datasets.
  - `templates/DATASET_MAPPING_TEMPLATE.md`: Reusable field-to-context mapping template.
  - `templates/INTEGRATION_CHECKLIST_TEMPLATE.md`: Blank printable checklist for integration milestones.
  - `templates/DATASET_INTEGRATION_REPORT_TEMPLATE.md`: Standard engineering sign-off report template.
