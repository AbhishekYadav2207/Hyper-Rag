<h1 align="center">Hyper-RAG / Adaptive Hyper-RAG</h1>

<p align="center">
  <img alt="Github top language" src="https://img.shields.io/github/languages/top/iMoonLab/Hyper-RAG?color=purple">
  <img alt="License" src="https://img.shields.io/github/license/iMoonLab/Hyper-RAG?color=purple">
  <a href="https://www.nature.com/articles/s41467-026-71411-1"><img alt="Nature Communications" src="https://img.shields.io/badge/Nature%20Communications-2026-E63946?logo=nature&logoColor=white"></a>
  <a href="https://doi.org/10.1038/s41467-026-71411-1"><img alt="DOI" src="https://img.shields.io/badge/DOI-10.1038%2Fs41467--026--71411--1-1F6FEB"></a>
</p>

<p align="center">
  <a href="#about-the-project">About</a> &nbsp;|&nbsp;
  <a href="#key-features">Key Features</a> &nbsp;|&nbsp;
  <a href="#quick-start">Quick Start</a> &nbsp;|&nbsp;
  <a href="#adaptive-hyper-rag">Adaptive RAG</a> &nbsp;|&nbsp;
  <a href="#web-console">Web Console</a> &nbsp;|&nbsp;
  <a href="#documentation-system">Documentation</a> &nbsp;|&nbsp;
  <a href="#verification-status">Verification</a> &nbsp;|&nbsp;
  <a href="#citation">Citation</a>
</p>

---

## About the Project

**Hyper-RAG** is a state-of-the-art Retrieval-Augmented Generation (RAG) framework developed by [iMoon-Lab](http://moon-lab.tech/), Tsinghua University, and published in *Nature Communications* (2026). 

Traditional Graph RAG models relationships strictly as pairwise edges $(u, v)$ between two nodes, causing information loss when modeling complex, multi-entity facts. Hyper-RAG models higher-order multi-entity correlations using **hyperedges** $e = \{v_1, v_2, \dots, v_k\}$ within a native hypergraph database (<a href="https://github.com/iMoonLab/Hypergraph-DB">Hypergraph-DB</a>), drastically reducing Large Language Model hallucinations.

**Adaptive Hyper-RAG** introduces an intelligent multi-phase routing and validation engine above the retrieval pipelines, dynamically selecting between **Hyper-Lite** (lightweight entity-passage search) and **Hyper-Core** (full hypergraph diffusion) based on measured query complexity and retrieved evidence.

---

## Key Features

- :heavy_check_mark: **Beyond-Pairwise Hypergraph Modeling**: Connects arbitrary subsets of entities within unified hyperedges, capturing high-order relational knowledge without pairwise decomposition.
- :heavy_check_mark: **Deterministic Adaptive Routing (Phase 1 & 2.1)**: Evaluates query complexity across 8 categories ($0-100$ score) before retrieval with **0 LLM calls**. Compact, dense queries receive an automatic semantic density bonus.
- :heavy_check_mark: **Post-Retrieval Sufficiency Escalation (Phase 2)**: Checks retrieved evidence before reasoning. If Lite evidence is deficient, it **automatically escalates to Hyper-Core** with zero wasted LLM tokens.
- :heavy_check_mark: **Deterministic Response Validation (Phase 3)**: Post-reasoning validator scores generated answers across completeness ($40\%$), evidence support ($40\%$), and relevance ($20\%$).
- :heavy_check_mark: **Modern Full-Stack Web Console**: Interactive React 18 / Vite 6.4.3 interface featuring Chat, 2D/3D HyperGraph Visualizer, Database Explorer, Document Manager, and OpenAPI Swagger docs.
- :heavy_check_mark: **Strict Provider Architecture**: Clean separation between **OpenRouter** (LLM reasoning and token streaming) and **Mistral AI** (1024-dimensional dense embeddings).
- :heavy_check_mark: **Rigorous Test Baseline**: Fully verified against 67 unit tests and 32 automated pipeline checks with **0 warnings and 0 errors**.

---

## Quick Start

### 1. Clone & Set Up Python Environment
```bash
git clone https://github.com/AbhishekYadav2207/Hyper-Rag.git
cd Hyper-Rag

# Create and activate virtual environment
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Linux / macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r web-ui/backend/requirements.txt
```

### 2. Configure Environment (`.env`)
```bash
# Windows
Copy-Item .env.example .env
# Linux / macOS
cp .env.example .env
```
Add your API keys in `.env`:
```env
OPENROUTER_API_KEYS=your_openrouter_api_key_here
EMB_API_KEYS=your_mistral_api_key_here
```

### 3. Run Fast Local Tests
```bash
python -m pytest tests/unit -v
```
*(All 67 unit tests run completely locally with **0 warnings** and require zero API tokens).*

### 4. Launch the Web Console
In **Terminal 1** (Backend API):
```bash
python -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

In **Terminal 2** (Frontend Dev Server):
```bash
cd web-ui/frontend
npm install
npm run dev
```

Open your browser to: **`http://localhost:5173/`**

> [!TIP]
> For the complete, beginner-oriented, step-by-step walkthrough, see [**`docs/USER_MANUAL.md`**](file:///d:/Rag/Hyper-RAG/docs/USER_MANUAL.md).

---

## Adaptive Hyper-RAG Overview

```text
User Question
     │
     ▼
[Phase 1 & 2.1] Complexity Analyzer (0–100 Score)
     │
     ├─ Score < 60 ──► Hyper-Lite ──► Sufficiency Check ──┬─ Sufficient ──► Lite Answer
     │                                                    └─ Insufficient ─┐
     │                                                                     │
     └─ Score ≥ 60 ──► Hyper-Core (High-Order Hypergraph) ◄────────────────┘
                             │
                             ▼
                         Core Answer
                             │
                             ▼
                [Phase 3] Response Validation
                             │
                             ▼
                     User / API Client
```

- **Phase 1 (Complexity Scoring)**: Pre-retrieval scoring across 12 signals (comparison, causal, temporal, multi-hop, aggregation, entities).
- **Phase 2 (Sufficiency Check)**: Post-retrieval evidence evaluation. If score $<60$, triggers early escalation to Hyper-Core before LLM reasoning.
- **Phase 2.1 (Semantic Density)**: Queries with $\le 7$ words containing comparison/causal signals receive $+15$ bonus to route directly to Core.
- **Phase 3 (Response Validation)**: Weighted evaluation of Completeness ($0.40$), Evidence Support ($0.40$), and Relevance ($0.20$) against threshold $70.0$.
- **Boundary**: Evidence-supported $\neq$ globally fact-checked. Phase 4 self-repair is not implemented.

For the in-depth technical specification, see [**`docs/ADAPTIVE_HYPERRAG.md`**](file:///d:/Rag/Hyper-RAG/docs/ADAPTIVE_HYPERRAG.md).

---

## Web Console

The Web Console provides an intuitive graphical interface for all Hyper-RAG capabilities:
- **Chat (`/#/Chat`)**: Natural language question answering with real-time token streaming and transparent Adaptive decision badges.
- **Database Explorer (`/#/DB`)**: Tabular browser for vertices (entities) and hyperedges.
- **Visualization (`/#/Graph`)**: 2D and 3D force-directed canvas with hyperedge convex hulls and entity inspection.
- **File Ingestion (`/#/Files`)**: Drag-and-drop document upload (`.txt`, `.pdf`, `.docx`, `.md`) with live WebSocket progress.
- **Swagger Documentation (`/#/API`)**: Interactive OpenAPI specification.
- **Settings (`/#/Setting`)**: Model provider configuration with automatic API key masking.

For view-by-view details, see [**`docs/WEB_UI_GUIDE.md`**](file:///d:/Rag/Hyper-RAG/docs/WEB_UI_GUIDE.md).

---

## REST & Python APIs

### Python Usage
```python
from hyperrag import HyperRAG, QueryParam

rag = HyperRAG(...)
# Adaptive mode automatically selects Lite or Core, checking sufficiency:
answer = rag.query("Compare diabetes and hypertension causes", param=QueryParam(mode="adaptive"))
```

### Standalone REST API (`service_api.py`)
```bash
python -m uvicorn service_api:app --host 0.0.0.0 --port 8002
```

Query endpoint:
```bash
curl -X POST "http://127.0.0.1:8002/query" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is diabetes?", "mode": "adaptive"}'
```

For complete schemas and endpoints, see [**`docs/API_REFERENCE.md`**](file:///d:/Rag/Hyper-RAG/docs/API_REFERENCE.md).

---

## Documentation System

| Document | Description |
|---|---|
| [**USER_MANUAL.md**](file:///d:/Rag/Hyper-RAG/docs/USER_MANUAL.md) | **The Master User Guide**: 36-section comprehensive manual and complete runbook. |
| [**GETTING_STARTED.md**](file:///d:/Rag/Hyper-RAG/docs/GETTING_STARTED.md) | 5-minute quick start for developers. |
| [**WEB_UI_GUIDE.md**](file:///d:/Rag/Hyper-RAG/docs/WEB_UI_GUIDE.md) | Complete guide to all 6 Web Console views. |
| [**API_REFERENCE.md**](file:///d:/Rag/Hyper-RAG/docs/API_REFERENCE.md) | Python SDK and FastAPI endpoint reference. |
| [**ADAPTIVE_HYPERRAG.md**](file:///d:/Rag/Hyper-RAG/docs/ADAPTIVE_HYPERRAG.md) | Technical specification for Phases 1, 2, 2.1, and 3. |
| [**ARCHITECTURE.md**](file:///d:/Rag/Hyper-RAG/docs/ARCHITECTURE.md) | System architecture and Mermaid sequence flows. |
| [**CONFIGURATION.md**](file:///d:/Rag/Hyper-RAG/docs/CONFIGURATION.md) | Complete environment variable and `.env` guide. |
| [**TESTING.md**](file:///d:/Rag/Hyper-RAG/docs/TESTING.md) | Unit tests, internal diagnostics, and benchmark suite. |
| [**DEVELOPER_GUIDE.md**](file:///d:/Rag/Hyper-RAG/docs/DEVELOPER_GUIDE.md) | Codebase extension points and contributor workflows. |
| [**TROUBLESHOOTING.md**](file:///d:/Rag/Hyper-RAG/docs/TROUBLESHOOTING.md) | Diagnostic runbook for errors, ports, keys, and rate limits. |
| [**VERIFICATION_AND_OUTCOMES.md**](file:///d:/Rag/Hyper-RAG/docs/VERIFICATION_AND_OUTCOMES.md) | Empirical test baseline and historical defect fixes. |
| [**APPENDICES.md**](file:///d:/Rag/Hyper-RAG/docs/APPENDICES.md) | Reference tables, glossary, and FAQ. |

---

## Verification Status

Hyper-RAG is maintained with a strict zero-warning baseline:
- **Pipeline Automated Checks**: 32 / 32 PASS
- **Pytest Unit Tests**: 67 / 67 PASS
- **Web UI Views**: 6 / 6 PASS
- **FastAPI Endpoints**: 4 / 4 PASS
- **Benchmark Evaluations**: 2 / 2 PASS
- **Security & Boundary Checks**: 3 / 3 PASS
- **Runtime Warnings**: 0
- **Runtime Errors**: 0

For full verification traces and logs, see [**`docs/VERIFICATION_AND_OUTCOMES.md`**](file:///d:/Rag/Hyper-RAG/docs/VERIFICATION_AND_OUTCOMES.md).

---

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

Hyper-RAG is maintained by [iMoon-Lab](http://moon-lab.tech/), Tsinghua University.

---

## Citation

If you use Hyper-RAG or Adaptive Hyper-RAG in your research, please cite our *Nature Communications* paper:

```bibtex
@article{feng2026hyperrag,
  title   = {Hyper-RAG: combating LLM hallucinations using hypergraph-driven retrieval-augmented generation},
  author  = {Feng, Yifan and Hu, Hao and Ying, Shihui and Hou, Xingliang and Liu, Shiquan and Yang, Mingyuan and Li, Junchang and Du, Shaoyi and Zheng, Nanning and Hu, Han and Gao, Yue},
  journal = {Nature Communications},
  year    = {2026},
  doi     = {10.1038/s41467-026-71411-1},
  url     = {https://www.nature.com/articles/s41467-026-71411-1}
}
```
