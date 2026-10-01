# Hyper-RAG & Adaptive Hyper-RAG: Complete User Manual
**A Comprehensive, Beginner-Friendly Guide from First Clone to Advanced Operations**

---

## Table of Contents

1. [What is Hyper-RAG?](#1-what-is-hyper-rag)
2. [What is Adaptive Hyper-RAG?](#2-what-is-adaptive-hyper-rag)
3. [What Can I Do with This Project?](#3-what-can-i-do-with-this-project)
4. [System Requirements](#4-system-requirements)
5. [Installation](#5-installation)
6. [Repository Structure](#6-repository-structure)
7. [Environment Configuration](#7-environment-configuration)
8. [API Key Setup & Provider Architecture](#8-api-key-setup--provider-architecture)
9. [Starting the Backend](#9-starting-the-backend)
10. [Starting the Web UI](#10-starting-the-web-ui)
11. [First Query Walkthrough](#11-first-query-walkthrough)
12. [Understanding Adaptive RAG](#12-understanding-adaptive-rag)
13. [Lite Mode (Hyper-Lite)](#13-lite-mode-hyper-lite)
14. [Core Mode (Hyper-Core)](#14-core-mode-hyper-core)
15. [Adaptive Mode (Default)](#15-adaptive-mode-default)
16. [Phase 2: Retrieval Sufficiency Evaluation](#16-phase-2-retrieval-sufficiency-evaluation)
17. [Lite → Core Automatic Escalation](#17-lite--core-automatic-escalation)
18. [Phase 3: Response Validation](#18-phase-3-response-validation)
19. [Token Streaming (SSE)](#19-token-streaming-sse)
20. [Working with Documents](#20-working-with-documents)
21. [HyperGraph Visualization](#21-hypergraph-visualization)
22. [HyperGraph Database Explorer](#22-hypergraph-database-explorer)
23. [File Management & Embedding](#23-file-management--embedding)
24. [Interactive API Documentation](#24-interactive-api-documentation)
25. [Settings and Model Configuration](#25-settings-and-model-configuration)
26. [Running the API Directly (cURL & Python)](#26-running-the-api-directly-curl--python)
27. [Running the Tests](#27-running-the-tests)
28. [Running the Benchmarks](#28-running-the-benchmarks)
29. [Reading Verification Logs](#29-reading-verification-logs)
30. [Running Everything: Single Master Runbook](#30-running-everything-single-master-runbook)
31. [Troubleshooting Guide](#31-troubleshooting-guide)
32. [Security and API Key Safety](#32-security-and-api-key-safety)
33. [Advanced Usage and Tuning](#33-advanced-usage-and-tuning)
34. [Developer Workflow](#34-developer-workflow)
35. [Reproducibility & Verification Invariants](#35-reproducibility--verification-invariants)
36. [Frequently Asked Questions (FAQ)](#36-frequently-asked-questions-faq)

---

## 1. What is Hyper-RAG?

### The Traditional RAG Challenge
Retrieval-Augmented Generation (RAG) is a technique that supplies Large Language Models (LLMs) with external reference texts before generating an answer. This helps LLMs answer questions about private documents or specialized domains.

However, traditional RAG systems suffer from a severe limitation:
- **Standard Vector RAG**: Slices documents into independent text passages ("chunks"). When a question spans multiple concepts or entities, standard vector search retrieves disconnected chunks, missing the relationships connecting them.
- **Traditional Graph RAG**: Models relationships as simple pairwise lines between two entities $(A \rightarrow B)$. But real-world facts often involve higher-order interactions: for example, a clinical trial involves a drug, a disease, a dosage, and patient outcomes simultaneously. Forcing multi-way interactions into pairs causes information loss and hallucinations.

### The Hypergraph Solution
**Hyper-RAG** solves this by organizing knowledge into a **hypergraph**. 
In mathematics, a hypergraph is an extension of a graph where an edge (called a **hyperedge**) can connect any arbitrary number of entities simultaneously:

```text
Traditional Graph Edge:        Hypergraph Hyperedge:
   (Entity A)                      (Entity A) ----+
       |                                          |
       |  (Pairwise only)            [Hyperedge]--+--- (Entity C)
       v                                          |
   (Entity B)                      (Entity B) ----+
```

Published in *Nature Communications* (2026) by [iMoon-Lab](http://moon-lab.tech/), Tsinghua University, Hyper-RAG captures both pairwise and beyond-pairwise correlations in domain-specific text corpora, drastically reducing LLM hallucinations.

---

## 2. What is Adaptive Hyper-RAG?

In real-world applications, not all questions need the heavy computational machinery of high-order hypergraphs:
- A simple question (*"What year was Scrooge's partner Marley born?"*) only needs a direct text passage lookup.
- A complex question (*"Compare Scrooge and Fred in their attitudes toward wealth and explain how Marley's fate warns Scrooge"*) requires tracing multi-entity relationships and causal pathways.

If a system always runs the full hypergraph pipeline, simple questions waste time and money. If it always runs a simple lookup, complex questions receive superficial or hallucinated answers.

**Adaptive Hyper-RAG** is an intelligent, multi-phase routing and validation engine:
1. **Phase 1 (Pre-Retrieval Complexity Scoring)**: Analyzes the question before fetching any data and assigns a score from $0$ to $100$. If the question is simple, it selects **Hyper-Lite**. If complex, it selects **Hyper-Core**.
2. **Phase 2 (Post-Retrieval Sufficiency Evaluation)**: If Hyper-Lite is chosen, it checks the retrieved text *before* asking the LLM to write an answer. If the retrieved text is empty, repetitive, or missing required relationships, it **automatically escalates to Hyper-Core**.
3. **Phase 2.1 (Short-Query Semantic-Density Refinement)**: Short questions that are semantically dense (e.g., *"Compare Fred vs Scrooge"*) receive a density bonus so they route directly to Hyper-Core without an unnecessary Lite step.
4. **Phase 3 (Deterministic Response Validation)**: After the final answer is generated, an in-process validator inspects the answer against the retrieved evidence for completeness, evidence support, and relevance.

```text
User Question
     ↓
Query Complexity Analysis (Phase 1 & 2.1)
     ↓
Decision: Lite or Core?
   ├── If Core ───────────────────────────────┐
   │                                          │
   └── If Lite                                │
         ↓                                    │
       Lite Retrieval                         │
         ↓                                    │
       Retrieval Sufficiency Check (Phase 2)  │
         ├── Sufficient ──> Lite Reasoning    │
         └── Insufficient ────────────────────┤
                                              ↓
                                       Core Retrieval
                                              ↓
                                       Core Reasoning
                                              ↓
                                        Final Answer
                                              ↓
                               Response Validation (Phase 3)
                                              ↓
                                        User / API
```

---

## 3. What Can I Do with This Project?

With this repository, you can:
- **Index Documents**: Ingest PDF, DOCX, and TXT files into a structured hypergraph database.
- **Ask Natural Language Questions**: Use the modern React Web UI to chat with your knowledge base.
- **Inspect Hypergraphs Visually**: Explore interactive 2D and 3D hypergraphs to see how entities and hyperedges connect.
- **Browse Database Tables**: Examine raw vertices (nodes), hyperedges, degree centrality, and incident connections.
- **Integrate via REST API**: Query the backend using standard FastAPI endpoints (`/query`, `/query_stream`) from Python, JavaScript, or any language.
- **Run Benchmark Evaluations**: Test query accuracy, routing efficiency, and latency across established datasets.
- **Reproduce Nature Communications Results**: Run step-by-step reproduction scripts.

---

## 4. System Requirements

### Hardware Requirements
- **CPU**: 4 cores minimum (8 cores recommended).
- **RAM**: 8 GB minimum (16 GB recommended for building large hypergraphs).
- **Disk Space**: At least 5 GB free disk space.
- **Network**: Internet access for calling the LLM (OpenRouter) and embedding (Mistral) APIs.

### Software Prerequisites
| Component | Required Version | Verification Command |
|---|---|---|
| **Python** | 3.10 or 3.11 | `python --version` |
| **Node.js** | 18.0.0 or higher | `node --version` |
| **npm** | 9.0.0 or higher | `npm --version` |
| **Git** | 2.30 or higher | `git --version` |

Supported Operating Systems:
- **Windows** (Windows 10, Windows 11, Windows Server) via PowerShell or CMD.
- **Linux** (Ubuntu 20.04+, Debian 11+, RHEL/CentOS 8+, Fedora).
- **macOS** (macOS 12 Monterey or higher, Apple Silicon M1/M2/M3 or Intel).

---

## 5. Installation

Follow these step-by-step instructions. Choose the commands matching your operating system.

### Step 5.1: Clone the Repository
Open your terminal (PowerShell on Windows, bash/zsh on Linux/macOS) and run:

```bash
git clone https://github.com/AbhishekYadav2207/Hyper-Rag.git
cd Hyper-Rag
```

### Step 5.2: Create and Activate a Python Virtual Environment

#### On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If you see an execution policy error in PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and try activating again).*

#### On Linux / macOS (bash/zsh):
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 5.3: Install Python Dependencies
Install the required packages for both the core library and the Web UI backend:

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install core Hyper-RAG dependencies
pip install -r requirements.txt

# Install Web UI backend dependencies
pip install -r web-ui/backend/requirements.txt
```

### Step 5.4: Install Web UI Frontend Dependencies
Navigate to the frontend folder and install npm packages:

```bash
cd web-ui/frontend
npm install
cd ../..
```

---

## 6. Repository Structure

Here is how the repository is structured:

```text
Hyper-Rag/
├── hyperrag/                     # Core Python library
│   ├── adaptive_router.py        # Phase 1: Query complexity analyzer & heuristic router
│   ├── retrieval_sufficiency.py  # Phase 2: Post-retrieval sufficiency evaluator
│   ├── response_validator.py     # Phase 3: In-process deterministic response validator
│   ├── language_guard.py         # Deterministic English-only Latin compliance filter
│   ├── key_pool.py               # API key rotation, cooldown, and backoff engine
│   ├── llm.py                    # OpenRouter LLM client & Mistral embedding client
│   ├── hyperrag.py               # HyperRAG engine coordinator and query entrypoints
│   ├── operate.py                # Low-level retrieval, diffusion, and prompt synthesis
│   └── utils.py                  # Logger management, embedding functions, hashing helpers
├── web-ui/                       # Full-Stack Web Application
│   ├── backend/                  # FastAPI backend server
│   │   ├── main.py               # Main Web UI backend application
│   │   ├── file_manager.py       # Document ingestion and storage manager
│   │   ├── db.py                 # Hypergraph database interface
│   │   └── requirements.txt      # Web UI Python dependencies
│   └── frontend/                 # React 18 + Vite frontend
│       ├── src/                  # React source files (Chat, Graph, DB, Files, Settings)
│       └── package.json          # Node.js dependencies (Vite 6.4.3)
├── docs/                         # Complete documentation system
│   ├── USER_MANUAL.md            # This beginner-to-advanced user manual
│   ├── GETTING_STARTED.md        # Quick developer setup and first-run guide
│   ├── ARCHITECTURE.md           # System architecture, knowledge representation, data flows
│   ├── ADAPTIVE_HYPERRAG.md      # In-depth Adaptive RAG specification (Phases 1, 2, 2.1, 3)
│   ├── WEB_UI_GUIDE.md           # Detailed guide to each Web UI view
│   ├── API_REFERENCE.md          # REST endpoints and Python class signatures
│   ├── CONFIGURATION.md          # Comprehensive environment variables guide
│   ├── TESTING.md                # Testing guide (pytest unit tests & diagnostics)
│   ├── DEVELOPER_GUIDE.md        # Contributor workflows, standards, extension points
│   ├── TROUBLESHOOTING.md        # Problem diagnosis and recovery runbooks
│   ├── VERIFICATION_AND_OUTCOMES.md # Verified test baselines and resolved issue logs
│   ├── APPENDICES.md             # Metrics, file maps, glossary, and FAQ
│   └── DOCUMENTATION_CHANGELOG.md # Documentation version and update logs
├── tests/                        # Automated test suites
│   ├── unit/                     # 67 isolated, fast, hermetic unit tests (0 warnings)
│   └── internal/                 # Upstream live provider smoke diagnostic scripts
├── examples/                     # Standalone runnable Python demo scripts
├── reproduce/                    # Nature Communications reproduction pipeline scripts
├── evaluate/                     # Scoring and selection-based assessment scripts
├── service_api.py                # Standalone production REST & streaming FastAPI server
├── my_config.py                  # Central configuration parser and validator
├── pytest.ini                    # Pytest configuration (defaults to tests/unit)
├── requirements.txt              # Core Python library requirements
└── .env.example                  # Environment configuration template
```

---

## 7. Environment Configuration

Hyper-RAG reads configuration variables from a `.env` file located in the root of the project.

### Step 7.1: Create Your `.env` File
Copy `.env.example` to create your active `.env`:

#### On Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

#### On Linux / macOS:
```bash
cp .env.example .env
```

### Step 7.2: Key Configuration Settings
Open `.env` in any text editor. The file is divided into clear sections:

```env
# ============================================================
# LLM PROVIDER: OpenRouter (Primary and ONLY LLM Provider)
# ============================================================
OPENROUTER_API_KEYS=your_openrouter_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free

# ============================================================
# EMBEDDING PROVIDER: Mistral AI (Embeddings ONLY)
# ============================================================
EMB_API_KEYS=your_mistral_api_key_here
EMB_BASE_URL=https://api.mistral.ai/v1
EMB_MODEL=mistral-embed
EMB_DIM=1024

# ============================================================
# ADAPTIVE HYPER-RAG ROUTING
# ============================================================
ADAPTIVE_RAG_ENABLED=true
ADAPTIVE_RAG_MODE=adaptive
ADAPTIVE_CORE_THRESHOLD=60
ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED=true
ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD=60
ADAPTIVE_LOG_DECISIONS=true
ADAPTIVE_SHORT_QUERY_MAX_WORDS=7
ADAPTIVE_SHORT_QUERY_DENSITY_BONUS=15.0

# ============================================================
# PHASE 3: RESPONSE VALIDATION
# ============================================================
ADAPTIVE_VALIDATION_ENABLED=true
ADAPTIVE_VALIDATION_THRESHOLD=70
ADAPTIVE_VALIDATION_LOG_DECISIONS=true
ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT=0.40
ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT=0.40
ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT=0.20
```

---

## 8. API Key Setup & Provider Architecture

Hyper-RAG enforces a strict, clean separation between two external providers:

```text
┌─────────────────────────────────────────────────────────────┐
│                 EXTERNAL PROVIDER TOPOLOGY                  │
├──────────────────────────────┬──────────────────────────────┤
│ 1. LLM Reasoning (ONLY):     │ 2. Embeddings (ONLY):        │
│    Provider: OpenRouter      │    Provider: Mistral AI      │
│    Model: nvidia/nemotron... │    Model: mistral-embed      │
│    Keys: OPENROUTER_API_KEYS │    Keys: EMB_API_KEYS        │
│    Purpose: Prompt reasoning │    Dimension: 1024 fixed     │
└──────────────────────────────┴──────────────────────────────┘
```

> [!IMPORTANT]
> **Strict Provider Roles**:
> - **OpenRouter** is used strictly for LLM text reasoning and token streaming.
> - **Mistral AI** is used strictly for 1024-dimensional dense embeddings.
> - Mistral is **never** used as an LLM reasoning fallback.

### Getting Your API Keys
1. **OpenRouter Key**: Create an account at [openrouter.ai](https://openrouter.ai/). Navigate to *Keys*, create a new key, and paste it into `OPENROUTER_API_KEYS`.
2. **Mistral AI Key**: Create an account at [console.mistral.ai](https://console.mistral.ai/). Navigate to *API Keys*, generate a key, and paste it into `EMB_API_KEYS`.

### Multi-Key Rotation Support
If you have multiple keys for higher throughput, list them separated by commas:
```env
OPENROUTER_API_KEYS=sk-or-v1-key1,sk-or-v1-key2,sk-or-v1-key3
EMB_API_KEYS=mistral-key1,mistral-key2
```
Hyper-RAG's internal `KeyPool` automatically rotates through keys in a round-robin schedule and places any key that receives an HTTP 429 rate limit into a temporary cooldown.

---

## 9. Starting the Backend

There are two backend options depending on whether you want the **Web UI Console** or the **Standalone Production API**.

### Option A: Web UI Backend (Recommended for Interactive Use)
The Web UI backend serves the full-stack database, file manager, graph visualization, and chat endpoints.

From the repository root with your virtual environment active:

#### Windows (PowerShell):
```powershell
python -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Linux / macOS:
```bash
python3 -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

You should see:
```text
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     HyperRAG Web-UI Backend initialized
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Option B: Standalone Production Service API (`service_api.py`)
If you only need a lightweight REST API for microservice integration without the Web UI:

```powershell
python -m uvicorn service_api:app --host 0.0.0.0 --port 8002
```

---

## 10. Starting the Web UI

In a **second terminal window**, navigate to the frontend directory and start the Vite development server:

```bash
cd web-ui/frontend
npm run dev
```

You will see:
```text
  VITE v6.4.3  ready in 350 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

Now open your web browser and visit:
```text
http://localhost:5173/
```

You will be greeted by the Hyper-RAG Web Console!

---

## 11. First Query Walkthrough

Let's test the system step-by-step using both the Web UI and a direct Python script.

### Using the Web UI
1. Open `http://localhost:5173/#/Chat`.
2. Notice the control bar at the top:
   - **RAG Mode** is pre-selected to **Adaptive RAG** by default.
   - **Database** shows your active knowledge base (default or uploaded).
3. Type a simple factual query into the chat input:
   ```text
   What is a counting-house?
   ```
4. Press **Enter** or click **Send**.
5. Observe the response:
   - The answer is generated using retrieved context.
   - The metadata badge displays `Mode: lite`, `Score: 6/100`, `Threshold: 60`.
6. Now type a complex comparative query:
   ```text
   Compare Ebenezer Scrooge and his nephew Fred in terms of their attitudes toward Christmas and wealth.
   ```
7. Press **Enter**:
   - The metadata badge displays `Mode: core`, `Score: 66/100`.
   - The system automatically invoked high-order hypergraph traversal to contrast both entities across multiple dimensions.

### Using Python Directly
Create a short script or run in the Python REPL:

```python
import asyncio
from hyperrag import HyperRAG, QueryParam
from hyperrag.utils import EmbeddingFunc
from reproduce.Step_3_response_question import llm_model_func, embedding_func
from my_config import EMB_DIM

async def main():
    rag = HyperRAG(
        working_dir="./caches/default",
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=EMB_DIM,
            max_token_size=8192,
            func=embedding_func
        )
    )

    # 1. Ask a question with default adaptive routing
    query = "What is Ebenezer Scrooge's profession?"
    answer = await rag.aquery(query, param=QueryParam(mode="adaptive"))
    print("Answer:\n", answer)

    # 2. Inspect the decision metadata
    decision = rag.last_adaptive_decision
    print(f"\nMode: {decision.final_mode} (Score: {decision.score}/{decision.threshold})")
    print(f"Escalated: {decision.escalated}")

asyncio.run(main())
```

---

## 12. Understanding Adaptive RAG

Traditional RAG systems treat all queries identically:

| Query Type | Query Example | Ideal Pipeline | Traditional Fixed RAG Problem |
|---|---|---|---|
| **Simple Factual** | *"Where did Marley die?"* | **Hyper-Lite** | Wastes 2–5 seconds doing multi-layer graph diffusion |
| **Complex Relational** | *"How did greed cause Marley's chains and warn Scrooge?"* | **Hyper-Core** | Truncates multi-hop connections, leading to hallucinations |

Adaptive Hyper-RAG eliminates this trade-off by dynamically sizing the retrieval pipeline to fit the query.

```text
                  Incoming User Query
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
   Factual / Single Entity      Multi-Entity / Causal / Comparative
      (Score < 60)                     (Score >= 60)
             │                                   │
             ▼                                   ▼
        Hyper-Lite                           Hyper-Core
   (Direct Vector Match)              (Hypergraph Diffusion)
             │                                   │
      Sufficiency Check                          │
      Score < 60? ───> Escalates to Core ────────┘
             │
             ▼
        Final Answer
             │
     Response Validation
```

---

## 13. Lite Mode (Hyper-Lite)

### How It Works
1. Normalizes the query and extracts key entity phrases.
2. Queries the `entities_vdb` vector database using cosine similarity against Mistral embeddings.
3. Retrieves passage chunks directly linked to the matched entities.
4. Synthesizes an answer using the retrieved passages without traversing hyperedges.

### Characteristics
- **Speed**: Very fast (often under 100 ms retrieval latency).
- **Cost**: Minimal token consumption.
- **Best For**: Definitions, single-entity facts, dates, direct quotes.

### Manual Usage
```python
# Force Lite mode directly (skips adaptive routing and escalation):
param = QueryParam(mode="lite")
response = await rag.aquery("Who is Bob Cratchit?", param=param)
```

---

## 14. Core Mode (Hyper-Core)

### How It Works
1. Performs dual vector retrieval across both entity concepts (`entities_vdb`) and high-order relations (`relationships_vdb`).
2. Traverses the `ChunkEntityRelationHypergraph` using information diffusion across incident hyperedges.
3. Assembles multi-hop relational pathways and community summaries.
4. Generates an in-depth answer grounded in high-order structural connections.

### Characteristics
- **Depth**: Traces multi-way relationships connecting 3 or more entities simultaneously.
- **Accuracy**: Eliminates hallucinations on comparative and multi-hop reasoning.
- **Best For**: Comparative analysis, root-cause mechanisms, chronological timelines, multi-entity synthesis.

### Manual Usage
```python
# Force Core mode directly:
param = QueryParam(mode="core")
response = await rag.aquery("Compare Scrooge and Marley", param=param)
```

---

## 15. Adaptive Mode (Default)

In Adaptive Mode (`param=QueryParam(mode="adaptive")`), Hyper-RAG executes:

### Phase 1: Query Complexity Routing
The query is scanned for 12 structural and semantic signals across 8 categories without calling any LLM:
- **Comparison Indicators** (`compare`, `versus`, `difference between`): $+20$ pts.
- **Causal Reasoning** (`why`, `how did`, `cause`, `mechanism`): $+15$ pts.
- **Temporal Reasoning** (`timeline`, `historically`, `evolution`): $+15$ pts.
- **Multi-Hop Traversal** (`relationship between`, `pathway`): $+15$ pts.
- **Aggregation** (`summarize all`, `list all`): $+15$ pts.
- **Requested Depth** (`detailed`, `in-depth`, `step by step`): $+12$ pts.
- **Entity Count**: 1 entity $= +5$, 2 entities $= +10$, 3 entities $= +15$, 4+ entities $= +20$.
- **Structural Length**: Up to $+10$ pts for word count, $+6$ pts for sentence count.

### Phase 2.1: Short-Query Density Bonus
If a query has 7 words or fewer (`ADAPTIVE_SHORT_QUERY_MAX_WORDS=7`) but contains high-order comparison or causal terms, it receives an observable $+15.0$ point density bonus (`ADAPTIVE_SHORT_QUERY_DENSITY_BONUS`).
- *"Compare Fred vs Scrooge"* (4 words) $\rightarrow$ Base: $51$ + Bonus: $15 = 66 \rightarrow$ **Core** upfront.
- *"What is Scrooge?"* (3 words, no relational terms) $\rightarrow$ Base: $6 \rightarrow$ **Lite**.

### Decision Boundary
- **Score $< 60$**: Initial mode is **Hyper-Lite**.
- **Score $\ge 60$**: Initial mode is **Hyper-Core**.

---

## 16. Phase 2: Retrieval Sufficiency Evaluation

### Why Phase 2 Exists
Syntactic complexity alone cannot reveal whether your database actually holds the required knowledge. A query may look simple, but Lite retrieval might return empty passages or unhelpful fragments.

Phase 2 inspects the retrieved context **before asking the LLM to generate an answer**.

### Concrete Metrics Evaluated
1. **Item Volume**: Number of retrieved text units and entities.
2. **Entity Diversity**: Count of unique entities found.
3. **Context Length**: Total character volume of context text.
4. **Query Entity Coverage**: Lexical and token overlap between query terms and retrieved text.
5. **Redundancy Penalty**: Deduction if chunks repeat the same text (Jaccard similarity).
6. **Relational Hyperedge Check**: If the query is causal or multi-hop, checks whether hyperedges were retrieved. If 0 hyperedges are present, a 25-point penalty is deducted.

### Sufficiency Formula
$$\text{Score} = (S_{\text{volume}} \times 0.25) + (S_{\text{entities}} \times 0.20) + (S_{\text{length}} \times 0.25) + (S_{\text{coverage}} \times 0.30) - P_{\text{redundancy}} - P_{\text{relational}}$$

- If **Sufficiency Score $\ge 60.0$**: Sufficient $\rightarrow$ proceeds to Lite LLM reasoning.
- If **Sufficiency Score $< 60.0$**: Insufficient $\rightarrow$ triggers **automatic escalation**.

---

## 17. Lite → Core Automatic Escalation

When retrieval sufficiency fails:
1. Lite reasoning is **aborted immediately** before any LLM prompt is sent. This guarantees zero wasted LLM tokens and zero wasted API latency.
2. The engine sets `decision.escalated = True` and sets `decision.final_mode = "core"`.
3. Hyper-Core executes hypergraph diffusion and completes high-order reasoning.
4. Exactly **one** escalation is permitted per query (no infinite escalation loops).

Example log when escalation occurs:
```text
[Adaptive RAG] Initial complexity score: 35 (threshold: 60) -> Initial mode: LITE
[Adaptive RAG] Retrieval sufficiency score: 32.5 (threshold: 60.0) -> INSUFFICIENT
[Adaptive RAG] Escalating LITE -> CORE. Reason: Missing relationship evidence for multi-hop / causal query
[Adaptive RAG] Executing Hyper-Core retrieval...
```

---

## 18. Phase 3: Response Validation

Phase 3 is an in-process deterministic validator that evaluates the generated answer across three primary dimensions:

### 1. Completeness ($0-100$)
Verifies that all entities, comparison pairs, causal relationships, and requested dimensions in the query are addressed in the answer.

### 2. Evidence Support ($0-100$)
Divides the answer into discrete claim sentences and checks lexical and entity grounding against the retrieved context passages. Unsupported numbers, dates, or foreign entities not found in context trigger deductions.

> [!NOTE]
> **Critical Invariant**: *"Evidence-supported"* means supported by the locally retrieved context. It does **NOT** mean globally fact-checked against world truth.

### 3. Relevance ($0-100$)
Measures query-to-answer topic alignment, penalizing off-topic drift.

### Weighted Formula & Threshold
$$\text{Validation Score} = (\text{Completeness} \times 0.40) + (\text{Evidence} \times 0.40) + (\text{Relevance} \times 0.20)$$

- Default Threshold: **70.0** / 100
- Hard Failures: Empty answer, evidence $< 30$, or relevance $< 30$ immediately marks the answer as `valid = False`.

### What Phase 3 Does NOT Do (Phase 4 Boundary)
Phase 3 is purely diagnostic and evaluative:
- Does NOT rewrite answers.
- Does NOT trigger regeneration loops.
- Does NOT make secondary LLM-as-a-judge calls (0 LLM overhead).
The generated response is returned intact alongside transparent validation metadata.

---

## 19. Token Streaming (SSE)

Hyper-RAG supports token-by-token streaming using Server-Sent Events (SSE).

### How Streaming Works
1. Pre-retrieval routing, retrieval, and sufficiency checks execute first in memory.
2. As soon as the LLM begins generating text, individual tokens are streamed across the HTTP connection in real time.
3. When complete, the stream emits `[DONE]`.

### Testing Streaming in Python
```python
import aiohttp
import asyncio

async def test_stream():
    url = "http://127.0.0.1:8000/hyperrag/query_stream"
    payload = {"query": "Explain how Scrooge changed throughout the story.", "mode": "adaptive"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            async for chunk in response.content.iter_any():
                print(chunk.decode("utf-8"), end="", flush=True)

asyncio.run(test_stream())
```

---

## 20. Working with Documents

Hyper-RAG allows you to build custom knowledge hypergraphs from your own files:
- **Supported File Types**: `.txt`, `.pdf`, `.docx`, `.md`.
- **Automatic Ingestion**: Files are automatically chunked into ~1200 token passages, embedded with Mistral, scanned for entities, and connected into hyperedges.

### Adding Documents via Python
```python
with open("my_document.txt", "r", encoding="utf-8") as f:
    content = f.read()

# Synchronous
rag.insert(content)

# Asynchronous
await rag.ainsert(content)
```

### Adding Documents via Web UI
1. Open `http://localhost:5173/#/Files`.
2. Drag and drop your files into the upload dropzone.
3. Click **Embed** to trigger hypergraph construction with live progress feedback.

---

## 21. HyperGraph Visualization

Navigate to `http://localhost:5173/#/Graph` to open the interactive HyperGraph Visualizer.

### Key Controls
- **2D / 3D Toggle**: Switch between flat 2D layout and 3D spatial orbit view.
- **Node Size**: Reflects entity degree (the number of hyperedges incident to that entity).
- **Hyperedge Convex Hulls**: Visual groupings highlighting entities bound within the same high-order hyperedge.
- **Entity Details Panel**: Click any node to view:
  - Entity Name & Category.
  - Entity Description extracted from text.
  - Incident Hyperedges and connected neighbor entities.

---

## 22. HyperGraph Database Explorer

Navigate to `http://localhost:5173/#/DB` to inspect raw hypergraph storage tables:
- **Vertices Tab**: Displays entity IDs, entity names, categories, and descriptions.
- **Hyperedges Tab**: Displays hyperedge IDs, member entity sets, relationship summaries, and creation timestamps.
- **Search & Filter**: Search entities by keyword or filter by degree centrality.

---

## 23. File Management & Embedding

Under `http://localhost:5173/#/Files`:
- **Document List**: View all uploaded files, file sizes, upload timestamps, and embedding status.
- **Delete Files**: Remove documents from the knowledge repository.
- **Real-Time Progress**: The WebSocket connection (`ws://localhost:8000/ws`) streams chunking, entity extraction, and embedding progress updates.

---

## 24. Interactive API Documentation

FastAPI provides an automatic, interactive Swagger UI:
- **Web UI Backend Docs**: Visit `http://localhost:8000/docs`
- **Standalone API Docs**: Visit `http://localhost:8002/docs`
- **Embedded in UI**: Open `http://localhost:5173/#/API` directly in the Web Console.

You can execute queries, inspect JSON schemas, and test endpoints interactively from your browser without writing code.

---

## 25. Settings and Model Configuration

Under `http://localhost:5173/#/Setting`:
- **LLM Settings**: View the active OpenRouter model (`nvidia/nemotron-3-ultra-550b-a55b:free`) and base URL.
- **Embedding Settings**: View the Mistral embedding model (`mistral-embed`, 1024 dimensions).
- **API Key Masking**: Real keys are strictly protected. The UI displays masked values (e.g. `sk-or-***`) so credentials are never leaked in screenshots or video recordings.

---

## 26. Running the API Directly (cURL & Python)

### Using cURL (Command Line)
```bash
curl -X POST "http://127.0.0.1:8000/hyperrag/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What is diabetes?",
       "mode": "adaptive"
     }'
```

### Using Python `requests`
```python
import requests

url = "http://127.0.0.1:8000/hyperrag/query"
payload = {
    "query": "What is diabetes?",
    "mode": "adaptive"
}
response = requests.post(url, json=payload)
data = response.json()

print("Answer:", data["answer"])
print("Mode Used:", data["mode"])
print("Decision Score:", data["adaptive_decision"]["score"])
```

---

## 27. Running the Tests

Hyper-RAG includes a comprehensive, verified test suite.

### Quick Test Execution
Run all 67 unit tests:
```bash
python -m pytest tests/unit -v
```

Expected output:
```text
======================= 67 passed in 3.36s =======================
```
**Zero warnings, zero failures.**

### Running Specific Test Modules
```bash
# 1. Test Phase 1 & Phase 2.1 Adaptive Routing
python -m pytest tests/unit/test_adaptive_router.py -v

# 2. Test Phase 2 Retrieval Sufficiency & Escalation
python -m pytest tests/unit/test_retrieval_sufficiency.py -v

# 3. Test Phase 3 Response Validation
python -m pytest tests/unit/test_response_validator.py -v

# 4. Test API Key Rotation and 429 Cooldown
python -m pytest tests/unit/test_key_rotation.py -v

# 5. Test English-Only Latin Script Compliance Guard
python -m pytest tests/unit/test_language_guard.py -v

# 6. Test Configuration Invariants
python -m pytest tests/unit/test_config.py -v
```

---

## 28. Running the Benchmarks

Hyper-RAG provides reproducible benchmark scripts to evaluate routing quality, latency, and threshold sensitivity.

### Running the Pilot Benchmark
Evaluates routing decisions across factual, comparative, and complex query archetypes:
```bash
python pilot_benchmark.py
```

### Running the Full 39-Query Benchmark Suite
```bash
python run_full_benchmark.py
```
This script evaluates the complete 39-query benchmark suite and outputs:
- `benchmark_results.json`: Execution log containing per-query latency, scores, modes, and decisions.
- `threshold_analysis.json`: Multi-threshold sensitivity comparison (thresholds 40, 50, 60, 70).

---

## 29. Reading Verification Logs

When full pipeline verification is executed, complete run artifacts are saved in `logs/full_pipeline_YYYYMMDD_HHMMSS/`:

```text
logs/full_pipeline_20260930_234500/
├── SUMMARY.md             # High-level pass/fail summary and change log
├── TEST_MATRIX.md         # Detailed 32-check status matrix and test breakdown
├── results.json           # Machine-readable JSON summary
├── pipeline.log           # Full orchestration log
├── unit_tests.log         # Complete pytest standard output
├── api_tests.log          # REST endpoint response traces
├── webui_tests.log        # Playwright UI automation logs
├── security_checks.log    # Secret masking and directory traversal logs
├── warnings.log           # Recorded runtime warnings (0 in verified baseline)
└── errors.log             # Recorded runtime errors (0 in verified baseline)
```

If an issue occurs, inspect `SUMMARY.md` first for the overall diagnosis, then check `errors.log` and `warnings.log`.

---

## 30. Running Everything: Single Master Runbook

Use this section as your complete, copy-and-paste operational cheat sheet.

### 1. Install Dependencies
```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r web-ui/backend/requirements.txt
cd web-ui/frontend && npm install && cd ../..

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r web-ui/backend/requirements.txt
cd web-ui/frontend && npm install && cd ../..
```

### 2. Configure Environment
```bash
# Windows
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```
*(Add your `OPENROUTER_API_KEYS` and `EMB_API_KEYS` inside `.env`)*

### 3. Start Backend Server
```bash
python -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Start Frontend Console
```bash
cd web-ui/frontend
npm run dev
```

### 5. Access Web UI
Open browser to `http://localhost:5173/`

### 6. Run Standalone API Server
```bash
python -m uvicorn service_api:app --host 0.0.0.0 --port 8002
```

### 7. Run Unit Tests (Hermetic, Fast)
```bash
python -m pytest tests/unit -v
```

### 8. Run Live Upstream Smoke Tests (Requires Real Keys)
```bash
python tests/internal/test_openrouter.py
python tests/internal/test_embedding.py
```

### 9. Build Web UI for Production
```bash
cd web-ui/frontend
npm run build
cd ../..
```

### 10. Run Full Benchmark
```bash
python run_full_benchmark.py
```

### 11. Clean Local Runtime Caches
```bash
# Windows PowerShell
Remove-Item -Recurse -Force .\test_cache, .\scratch, .\__pycache__ -ErrorAction SilentlyContinue

# Linux / macOS
rm -rf test_cache scratch __pycache__ .pytest_cache
```

---

## 31. Troubleshooting Guide

| Symptom | Probable Cause | Exact Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'hyperrag'` | Virtual environment not active or PYTHONPATH missing root. | Activate virtual environment (`.\venv\Scripts\activate` or `source venv/bin/activate`). Run scripts from repository root. |
| `HTTP 401 Unauthorized` | Missing or invalid API key. | Check `OPENROUTER_API_KEYS` and `EMB_API_KEYS` in `.env`. Ensure keys have no surrounding quotes or trailing spaces. |
| `HTTP 429 Rate Limit Exceeded` | Upstream provider rate limit reached. | Add multiple comma-separated keys in `.env` to enable automatic round-robin rotation. |
| Port 8000 already in use | Another process is holding port 8000. | Start on a different port: `python -m uvicorn web-ui.backend.main:app --port 8005`, or terminate the blocking process. |
| Frontend cannot reach backend | Backend not running or CORS issue. | Ensure backend is running on `http://127.0.0.1:8000`. Confirm Vite proxy settings in `vite.config.js`. |
| `UnicodeDecodeError` on Windows | Non-UTF8 Windows console codepage. | Set Python UTF-8 encoding in PowerShell: `$env:PYTHONUTF8=1` or run `chcp 65001`. |
| Query unexpectedly routed to Core | Query contained comparison words (*versus*, *difference*) or causal terms. | Check `rag.last_adaptive_decision.features` to see which triggers fired. If desired, adjust `ADAPTIVE_CORE_THRESHOLD` in `.env`. |
| Query escalated from Lite to Core | Lite retrieval found insufficient evidence or lacked hyperedges. | This is normal adaptive behavior! Inspect `rag.last_adaptive_decision.escalation_reason`. |
| Validation score below 70 | Answer omitted key query aspects or contained unsupported numbers. | Check `rag.last_validation_result.missing_aspects` and `unsupported_claims`. |

---

## 32. Security and API Key Safety

To safeguard your credentials:
1. **Never Commit `.env`**: `.gitignore` already excludes `.env`, `my_config.py`, and runtime caches. Always verify with `git status` before pushing code.
2. **Never Hardcode Keys in Code**: Always load keys via `my_config.py` or `os.getenv()`.
3. **Key Masking in Logs & UI**: Settings endpoints and logs mask all keys as `sk-or-***`. Never remove key masking in custom logging.
4. **Directory Traversal Protection**: The file manager sanitizes all uploaded filenames, preventing path traversal attacks (`../`).

---

## 33. Advanced Usage and Tuning

### Adjusting Routing Sensitivity
If you want Hyper-RAG to route more queries to **Hyper-Core**:
- Lower `ADAPTIVE_CORE_THRESHOLD` from `60` to `50` or `45`.
If you want to maximize speed and use **Hyper-Lite** more often:
- Raise `ADAPTIVE_CORE_THRESHOLD` to `70` or `75`.

### Customizing Validation Weights
In `.env`, tune the relative weights of the three validation dimensions:
```env
ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT=0.40
ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT=0.40
ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT=0.20
ADAPTIVE_VALIDATION_THRESHOLD=70
```
The sum of weights must be greater than zero.

---

## 34. Developer Workflow

### Adding New Tests
1. Add new unit tests to `tests/unit/test_<module>.py`.
2. Ensure tests use isolated mocks and make **zero** external HTTP calls.
3. Run `python -m pytest tests/unit` to verify all 67+ tests pass with 0 warnings.

### Adding New Configuration Options
1. Define the variable in `my_config.py` with a safe default.
2. Add the variable to `.env.example` with documentation comments.
3. Update `validate_config()` in `my_config.py`.
4. Document the variable in `docs/CONFIGURATION.md`.

---

## 35. Reproducibility & Verification Invariants

Hyper-RAG guarantees complete reproducibility:
- **Hermetic Unit Tests**: All 67 unit tests run completely offline without API keys or internet access.
- **Strict Metric Separation**: Verification reports distinguish Pytest unit tests (67 passed), pipeline system checks (32 passed), API checks (4 passed), Web UI checks (6 passed), and benchmark evaluations (2 passed).
- **Zero Warnings**: The verified baseline maintains **0 warnings** and **0 errors** across all test suites.
- **Evidence-Supported vs. Fact-Checked**: Validation checks alignment against retrieved documents only; it never claims global fact-checking.
- **Self-Contained Data**: All tests and benchmarks run on repository-included fixtures and mock data.

---

## 36. Frequently Asked Questions (FAQ)

### Q1: Why does Hyper-RAG use two providers (OpenRouter and Mistral)?
OpenRouter offers top-tier LLM reasoning models (e.g. Nemotron, Claude, GPT-4) with streaming support. Mistral provides state-of-the-art 1024-dimensional dense embeddings (`mistral-embed`). Separating reasoning from vector indexing provides optimal cost and performance.

### Q2: Can I use Hyper-RAG without an internet connection?
The entire unit test suite and local routing algorithms run 100% offline. Query execution and indexing require network access to reach OpenRouter and Mistral.

### Q3: Why did my simple question switch to Core mode?
If a question scored $<60$ in Phase 1, it started in Lite mode. But if Lite retrieval returned empty context, redundant text, or lacked hyperedge relationships, Phase 2 detected insufficient evidence and automatically escalated to Core to prevent an incomplete or hallucinated answer.

### Q4: Does Phase 3 validation make another LLM call?
No. Phase 3 validation is 100% deterministic and runs in-process in Python. It adds approximately 2.5 milliseconds of latency and incurs zero token costs.

### Q5: How do I completely reset the database?
Use the Web UI: click **Settings** $\rightarrow$ **Reset Knowledge Base**, or delete the cache folder (`rm -rf caches/default`).

### Q6: Where can I find more in-depth technical details?
- System Architecture: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- Adaptive RAG Specification: [`docs/ADAPTIVE_HYPERRAG.md`](ADAPTIVE_HYPERRAG.md)
- Configuration Reference: [`docs/CONFIGURATION.md`](CONFIGURATION.md)
- API Reference: [`docs/API_REFERENCE.md`](API_REFERENCE.md)
- Verification Baseline: [`docs/VERIFICATION_AND_OUTCOMES.md`](VERIFICATION_AND_OUTCOMES.md)
