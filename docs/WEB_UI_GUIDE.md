# Hyper-RAG Web Console: Complete Interface Guide

The **Hyper-RAG Web Console** is a modern, full-stack visual workspace built with **React 18** and **Vite 6.4.3**, connected to an asynchronous **FastAPI** backend. It enables users to converse with knowledge bases, inspect high-order hypergraphs in 2D and 3D, browse raw database tables, manage files, and configure models interactively.

---

## 1. Web UI Architecture & Quick Startup

```text
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│     Frontend (Vite 6.4.3)       │  HTTP /   │     Backend (FastAPI Server)    │
│     React 18 Single-Page App    │  WS / SSE │     web-ui/backend/main.py      │
│     http://localhost:5173       │◄─────────►│     http://127.0.0.1:8000       │
└─────────────────────────────────┘           └─────────────────────────────────┘
```

### Starting the Web Console
1. **Start Backend Server**:
   ```bash
   python -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. **Start Frontend Dev Server** (in a separate terminal):
   ```bash
   cd web-ui/frontend
   npm run dev
   ```
3. Open your browser to `http://localhost:5173/`.

---

## 2. Global Navigation & Layout

The Web Console features a persistent top navigation bar with direct access to all 6 views:
- **Chat** (`/#/Chat`): Interactive question answering with Adaptive RAG by default.
- **Database** (`/#/DB`): Tabular browser for vertices and hyperedges.
- **Visualization** (`/#/Graph`): Interactive 2D/3D hypergraph canvas with entity inspector.
- **Files** (`/#/Files`): Drag-and-drop document upload and embedding manager.
- **API Docs** (`/#/API`): Embedded OpenAPI Swagger documentation.
- **Settings** (`/#/Setting`): Model provider configuration and database reset.

---

## 3. View 1: Chat View (`/#/Chat`)

The primary conversational workspace.

### Controls & Header Bar
- **RAG Mode Selector**:
  - `Adaptive RAG` *(Default)*: Automatically chooses between Lite and Core, checking retrieval sufficiency and escalating when needed.
  - `Hyper-Core`: Forces full hypergraph diffusion on every query.
  - `Hyper-Lite`: Forces lightweight entity-passage vector search.
  - `Naive RAG`: Standard vector chunk retrieval without graph structures.
  - `Direct LLM`: Direct model response without retrieval.
- **Database Selector**: Switch between active knowledge bases (e.g., `default`, uploaded documents).
- **Streaming Toggle**: Enable or disable real-time token-by-token streaming.

### Asking a Question
1. Type your question into the message input bar at the bottom.
2. Click **Send** or press `Enter`.
3. As the model replies, tokens stream onto the screen.

### Inspecting Adaptive Decision Metadata
Every message returned by Adaptive RAG includes an expandable **Decision Badge**:
- **Effective Mode**: `lite` or `core`.
- **Complexity Score**: Additive Phase 1 score ($0 - 100$).
- **Core Threshold**: Target threshold ($60$).
- **Sufficiency Score**: Phase 2 retrieval sufficiency score ($0 - 100$).
- **Escalation Status**: Shows whether the query escalated from Lite to Core with the exact reason.
- **Phase 3 Validation**: Displays completeness, evidence support, and relevance scores ($0 - 100$).

---

## 4. View 2: HyperGraph Database (`/#/DB`)

The database explorer provides direct tabular visibility into the underlying hypergraph structure.

### Available Tabs
1. **Vertices Tab**:
   - `Vertex ID`: Unique identifier for the entity node.
   - `Entity Name`: Name of the extracted concept or entity.
   - `Category`: Classified entity type (e.g., `Person`, `Medical`, `Concept`, `Organization`).
   - `Description`: Synthesized summary of the entity's attributes.
   - `Degree Centrality`: Number of hyperedges connected to this vertex.
2. **Hyperedges Tab**:
   - `Hyperedge ID`: Unique identifier for the high-order hyperedge.
   - `Member Entities`: List of all vertices bound together by this hyperedge.
   - `Relationship Summary`: Semantic description of the multi-entity relationship.
   - `Weight / Importance`: Weight of the connection.

### Filtering & Search
- Use the **Search Box** to search entities or hyperedges by keyword.
- Sort columns by clicking column headers.

---

## 5. View 3: HyperGraph Visualization (`/#/Graph`)

An interactive visual canvas rendering high-order hypergraph networks.

### Interactive Features
- **2D / 3D Mode Toggle**: Switch between a 2D spring-embedded graph and a 3D orbit view with zoom and rotation.
- **Hyperedge Convex Hulls**: Translucent colored hulls enclose groups of entities that share a hyperedge, allowing visual identification of complex multi-entity facts.
- **Node Click Inspection**: Click any entity node to open the **Entity Details Panel**:
  - Displays the full description.
  - Lists all incident hyperedges.
  - Lists immediate neighbor entities.
- **Physics Layout Controls**: Adjust charge strength, link distance, and gravity to untangle dense clusters.

---

## 6. View 4: Files & Ingestion (`/#/Files`)

The document management hub for indexing custom text corpora.

### Features
- **Drag-and-Drop Dropzone**: Upload `.txt`, `.pdf`, `.docx`, or `.md` files.
- **Document Table**: View uploaded filenames, file sizes, upload timestamps, and indexing status (`Uploaded`, `Embedding`, `Indexed`).
- **Embed Button**: Triggers the background ingestion pipeline:
  1. Chunking text into ~1200 token passages.
  2. Embedding passages with Mistral.
  3. LLM entity and relation extraction via OpenRouter.
  4. Hypergraph DB construction.
- **Real-Time Progress**: Progress updates stream via WebSocket (`ws://localhost:8000/ws`) displaying current chunk extraction status.
- **Delete File**: Remove indexed documents from the active database.

---

## 7. View 5: API Documentation (`/#/API`)

An embedded interactive Swagger UI (`http://localhost:8000/docs`).

### How to Use
- Browse all REST endpoints organized by tags (`default`, `database`, `hyperrag`, `files`, `settings`).
- Click **Try it out** on any endpoint (e.g., `POST /hyperrag/query`).
- Enter request parameters and click **Execute** to view live responses, headers, and latency.

---

## 8. View 6: Settings (`/#/Setting`)

Configuration panel for model providers and system state.

### Configurable Options
- **LLM Provider**:
  - Model Name: `nvidia/nemotron-3-ultra-550b-a55b:free`
  - Base URL: `https://openrouter.ai/api/v1`
- **Embedding Provider**:
  - Model Name: `mistral-embed`
  - Dimensions: `1024` (fixed)
  - Base URL: `https://api.mistral.ai/v1`
- **Security & Key Masking**:
  - All API keys are masked as `sk-or-***` or `***`. Real credentials are never sent to the browser in plaintext.
- **Tracked Template Configuration**:
  - `settings.example.json` is provided in the repository root as a tracked canonical template. Copy it to `settings.json` (ignored by git) to customize local overrides:
    ```bash
    cp settings.example.json settings.json
    ```
- **Reset Knowledge Base**: Button to wipe current cached databases and start fresh.

---

## 9. Common UI Errors and Resolutions

| Issue | Likely Cause | Solution |
|---|---|---|
| **Network Error / Failed to Fetch** | Backend server is not running on port 8000. | Start backend: `python -m uvicorn web-ui.backend.main:app --port 8000`. |
| **Chat stuck on "Thinking..."** | Message content update omitted in React state. | Resolved: `updateLastMessage` in `Home/index.tsx` assigns `msg.content = content` and backend provides both `response` and `answer` aliases. |
| **Embedding dimension mismatch (1024 vs 1536)** | Vector DB created with 1024-dim Mistral, but runtime requested 1536-dim OpenAI embedding. | Resolved: Ensure `settings.json` and backend use `mistral-embed` (1024 dims). |
| **Vite connection refused on 5173** | Frontend dev server is not started. | Run `cd web-ui/frontend && npm run dev` or access directly via `http://127.0.0.1:8000` (FastAPI SPA mount). |
| **Upload fails with 413 or 500** | Unsupported file format or file locked by another process. | Ensure files are `.txt`, `.pdf`, `.docx`, or `.md`. |
| **Chat responses take long on complex queries** | Core hypergraph diffusion is running across dense clusters. | This is expected behavior for complex relational reasoning. Check streaming toggle for faster time-to-first-token. |
| **Empty graph on Visualization page** | No documents have been indexed yet. | Go to `/#/Files`, upload a document, and click `Embed`. |

