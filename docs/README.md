# Hyper-RAG Documentation System

Welcome to the documentation suite for **Hyper-RAG** and **Adaptive Hyper-RAG**.

Hyper-RAG is a state-of-the-art Retrieval-Augmented Generation (RAG) framework developed by [iMoon-Lab](http://moon-lab.tech/), Tsinghua University, published in *Nature Communications* (2026). It combines hypergraph-driven knowledge structures with high-order relational reasoning to combat Large Language Model hallucinations.

---

## 1. Documentation Index & Navigation Matrix

| Document | Primary Audience | Purpose |
|---|---|---|
| [**USER_MANUAL.md**](USER_MANUAL.md) | Beginners, End Users, Developers | **Master User Guide & Complete Runbook**: Step-by-step from initial clone to advanced operations, Web UI, API, testing, and troubleshooting. |
| [**GETTING_STARTED.md**](GETTING_STARTED.md) | New Developers & Users | **5-Minute Quick Start**: Instant installation, environment setup, and first query. |
| [**WEB_UI_GUIDE.md**](WEB_UI_GUIDE.md) | Users & Front-End Developers | **Web Console Guide**: Complete walkthrough of Chat, DB Explorer, Graph Vis, File Upload, Swagger Docs, and Settings. |
| [**API_REFERENCE.md**](API_REFERENCE.md) | Developers & API Consumers | **REST & Python SDK Reference**: Signatures, schemas, endpoints, and examples for both `service_api.py` and `web-ui/backend/main.py`. |
| [**ADAPTIVE_HYPERRAG.md**](ADAPTIVE_HYPERRAG.md) | Researchers & AI Engineers | **Adaptive RAG Specification**: In-depth analysis of Phase 1 (Complexity), Phase 2 (Sufficiency), Phase 2.1 (Density), and Phase 3 (Validation). |
| [**ARCHITECTURE.md**](ARCHITECTURE.md) | Software Architects & Engineers | **System Architecture & Data Flows**: Knowledge representation, storage engines, and Mermaid sequence diagrams for all query pipelines. |
| [**CONFIGURATION.md**](CONFIGURATION.md) | DevOps & System Administrators | **Configuration Reference**: Comprehensive guide to all environment variables, `.env.example`, provider keys, and thresholds. |
| [**TESTING.md**](TESTING.md) | QA & Contributors | **Testing Guide**: Pytest unit test suite (67 passed, 0 warnings), internal provider smoke checks, and benchmarks. |
| [**DEVELOPER_GUIDE.md**](DEVELOPER_GUIDE.md) | Open-Source Contributors | **Contributor Guide**: Codebase map, extension points, coding standards, and documentation maintenance workflows. |
| [**TROUBLESHOOTING.md**](TROUBLESHOOTING.md) | Everyone | **Diagnostic Runbook**: Symptom-to-solution guides for environment, network, port, provider, and routing issues. |
| [**VERIFICATION_AND_OUTCOMES.md**](VERIFICATION_AND_OUTCOMES.md) | Researchers & Maintainers | **Verified Outcomes**: Empirical test matrix (32 pipeline checks, 67 unit tests, 0 warnings) and historical defect resolutions. |
| [**APPENDICES.md**](APPENDICES.md) | Everyone | **Reference Appendices**: Verification tables, routing weights, validation formulas, test command sheet, glossary, and FAQ. |
| [**DOCUMENTATION_CHANGELOG.md**](DOCUMENTATION_CHANGELOG.md) | Everyone | **Documentation Release Log**: Record of documentation files created, updated, and verified. |

---

## 2. Reading Recommendations by Role

- **"I am completely new to Hyper-RAG and want to try it out"**:
  1. Start with [**GETTING_STARTED.md**](GETTING_STARTED.md) to set up and launch the application.
  2. Follow the detailed step-by-step walkthrough in [**USER_MANUAL.md**](USER_MANUAL.md).
  3. Explore interactive features with [**WEB_UI_GUIDE.md**](WEB_UI_GUIDE.md).

- **"I am a developer integrating Hyper-RAG into my application"**:
  1. Inspect [**API_REFERENCE.md**](API_REFERENCE.md) for REST endpoints and Python SDK signatures.
  2. Review [**CONFIGURATION.md**](CONFIGURATION.md) to configure your `.env`.
  3. Check [**ARCHITECTURE.md**](ARCHITECTURE.md) to understand request and streaming lifecycles.

- **"I am a researcher evaluating or reproducing Adaptive Hyper-RAG"**:
  1. Read [**ADAPTIVE_HYPERRAG.md**](ADAPTIVE_HYPERRAG.md) for exact formulas, weights, and decision boundaries.
  2. Inspect [**VERIFICATION_AND_OUTCOMES.md**](VERIFICATION_AND_OUTCOMES.md) for empirical test metrics.
  3. Run the benchmarks detailed in [**TESTING.md**](TESTING.md).

- **"I am an open-source contributor wanting to submit a pull request"**:
  1. Read [**DEVELOPER_GUIDE.md**](DEVELOPER_GUIDE.md) for extension points and coding standards.
  2. Run the test suite via [**TESTING.md**](TESTING.md).
  3. Consult [**TROUBLESHOOTING.md**](TROUBLESHOOTING.md) if you encounter any unexpected environment issues.
