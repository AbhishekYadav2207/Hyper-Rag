# Hyper-RAG Documentation Changelog

## Documentation System Release 3.1 (October 2026)

This release introduces the complete, professional, beginner-to-advanced documentation system for Hyper-RAG and Adaptive Hyper-RAG.

---

### 1. Documents Created
- **`docs/USER_MANUAL.md`**: Complete 36-section beginner-to-advanced manual and single master runbook covering installation, Web UI, API, Adaptive RAG, testing, benchmarks, and troubleshooting.
- **`docs/GETTING_STARTED.md`**: 5-minute onboarding guide taking new developers from clone to their first successful query.
- **`docs/WEB_UI_GUIDE.md`**: Dedicated interface guide covering all 6 views of the Web Console (Chat, DB Explorer, Graph Vis, File Upload, Swagger Docs, Settings) and Adaptive RAG integration.
- **`docs/TESTING.md`**: Full testing guide explaining fast unit tests, live provider smoke checks, Web UI verification, benchmark evaluations, and verified baselines.
- **`docs/DEVELOPER_GUIDE.md`**: Comprehensive contributor guide covering repository architecture, core extension points, coding standards, and documentation maintenance workflows.
- **`docs/TROUBLESHOOTING.md`**: Problem-solving runbook with symptom identification and verified recovery steps for environment, API key, server, and adaptive routing issues.
- **`docs/VERIFICATION_AND_OUTCOMES.md`**: Empirical record of the 32-check pipeline verification baseline, 67 passed unit tests (0 warnings), and historical resolution of issues UI_002, UI_003, UI_004, Pydantic V2 modernization, `combine_contexts`, and `FileHandler` lifecycle management.
- **`docs/APPENDICES.md`**: Comprehensive reference appendices including Verification Outcomes (Appendix A), Routing Weights (Appendix B), Response Validation (Appendix C), Configuration Quick Reference (Appendix D), Test Commands (Appendix E), Repository File Map (Appendix F), Glossary (Appendix G), and FAQ (Appendix H).
- **`docs/DOCUMENTATION_CHANGELOG.md`**: This changelog.

---

### 2. Documents Modernized & Updated
- **`README.md`**: Transformed into a clean, modern, professional landing page with Quick Start, Architecture overview, Adaptive Hyper-RAG summary, Web UI & API usage, verified test status, and deep cross-links into `docs/`.
- **`docs/README.md`**: Restructured as a comprehensive documentation directory index with an audience navigation matrix.
- **`docs/ARCHITECTURE.md`**: Expanded with knowledge representation details (Hypergraph DB, KV, NanoVectorDB), dual execution engines (Lite vs Core), and Mermaid sequence diagrams for Ingestion, Online Querying, Escalation, and Token Streaming.
- **`docs/ADAPTIVE_HYPERRAG.md`**: Complete specification of Phase 1 (Complexity Routing), Phase 2 (Retrieval Sufficiency), Phase 2.1 (Short-Query Density Bonus), and Phase 3 (Response Validation), with exact point allocations and decision boundaries.
- **`docs/API_REFERENCE.md`**: Comprehensive reference covering Python SDK classes (`HyperRAG`, `QueryParam`, `AdaptiveRouter`, `ValidationResult`) and all REST endpoints across `service_api.py` (port 8002) and `web-ui/backend/main.py` (port 8000).
- **`docs/CONFIGURATION.md`**: Comprehensive guide to all environment variables, `.env.example`, provider constraints (OpenRouter LLM only, Mistral Embeddings only), and configuration validation invariants.
- **`ADAPTIVE_ROUTING.md`**: Aligned with Phase 1 through Phase 3 architecture, short-query density refinement, and verified test metrics.

---

### 3. Verified Baseline Outcomes Recorded
- **Pipeline Automated Checks**: 32 passed, 0 failed.
- **Pytest Unit Tests**: 67 passed, 0 failed, 0 warnings.
- **Web UI Views**: 6 passed, 0 failed.
- **FastAPI Endpoints**: 4 passed, 0 failed.
- **Benchmark Evaluations**: 2 passed, 0 failed.
- **Security & Boundary Checks**: 3 passed, 0 failed.
- **Runtime Warnings**: 0.
- **Runtime Errors**: 0.

---

### 4. Verified Commands
The following operational commands were verified against the repository implementation:
- `python -m pytest tests/unit -v` (67 passed in ~3.36s, 0 warnings)
- `python -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000` (Web UI backend)
- `python -m uvicorn service_api:app --host 0.0.0.0 --port 8002` (Production service API)
- `cd web-ui/frontend && npm run build` (Clean Vite 6.4.3 production bundle)
- `cd web-ui/frontend && npm run dev` (Vite development server on port 5173)
- `python pilot_benchmark.py` (Pilot benchmark execution)
- `python run_full_benchmark.py` (Comprehensive 39-query benchmark suite)

---

### 5. Architectural Boundaries & Known Invariants
- **Evidence-Supported $\neq$ Fact-Checked**: Response validation verifies grounding against locally retrieved passages only.
- **Phase 4 Boundary**: Self-repair, automatic answer rewriting, and regeneration loops are not implemented.
- **Provider Roles**: OpenRouter is strictly the LLM reasoning provider; Mistral is strictly the 1024-dimensional embedding provider.
