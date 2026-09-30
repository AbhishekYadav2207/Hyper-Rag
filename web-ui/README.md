# HyperRAG Web UI

HyperRAG Web UI is a full-stack Web application based on React + FastAPI, providing an interactive interface and management console for the Hyper-RAG system.

## Project Overview

HyperRAG Web UI provides an intuitive Web interface for interacting with and managing the HyperRAG system, including hypergraph visualization, document management, and adaptive retrieval-augmented question answering.

## Quick Start

### Requirements

- Node.js 18+
- Python 3.11+
- npm / pnpm

### Backend Setup

1. Enter backend directory:

```bash
cd web-ui/backend
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start development server:

```bash
fastapi dev main.py
```

### Frontend Setup

1. Enter frontend directory:

```bash
cd web-ui/frontend
```

2. Install dependencies:

```bash
npm install
# or
pnpm install
```

3. Start development server:

```bash
npm run dev
```

The frontend application runs on `http://localhost:5173`.

## Pages and Views

- **Chat**: Intelligent QA interface with Adaptive RAG, Lite, and Core routing.
- **HyperGraph**: Interactive hypergraph visualization and exploration.
- **Database**: Complete CRUD operations on hypergraph entities and hyperedges.
- **Files**: Document upload, status tracking, and embedding progress monitoring.
- **Settings**: Model parameters, API keys, and query mode configuration.
- **API Docs**: Interactive Swagger documentation.

## Key Features

### Retrieval QA (Chat)

- Intelligent QA interface supporting multiple RAG modes.
- Defaults to **Adaptive RAG** with dynamic Lite/Core escalation and Phase 3 response validation.
- Supports direct execution in `hyper` (Core), `hyper-lite` (Lite), and baseline modes.
- Conversation history management and local persistence.

### Hypergraph Visualization (Graph)

- Interactive hypergraph visualization.
- Node and hyperedge detail inspection.
- Dynamic layout and zoom capabilities.

### HypergraphDB Management (DB)

- Full hypergraph database management interface.
- CRUD operations for vertices and hyperedges.
- Database switching and status inspection.
- Neighborhood querying and relation analysis.

### Document Management (Files)

- Drag-and-drop file upload interface.
- Supports PDF, DOCX, TXT, and Markdown formats.
- Real-time embedding progress tracking via WebSocket logs.
- Batch document processing and management.

### System Settings (Setting)

- LLM and embedding configuration.
- Database connection management.
- API connectivity test tool.

### API Documentation (API)

- FastAPI automatic Swagger/OpenAPI documentation.
- Interactive API testing interface.

## Tech Stack

### Frontend

- **React 18** - UI library
- **Ant Design & Radix UI** - Component libraries
- **AntV G6** - Graph visualization
- **React Router** - Routing
- **MobX** - State management
- **Tailwind CSS** - Styling
- **Vite** - Build tool

### Backend

- **FastAPI** - Python web framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation
- **WebSocket** - Real-time progress and logging
- **OpenRouter / Mistral** - Model integrations

## Core Endpoints

- `GET /db` - Get hypergraph data
- `POST /hyperrag/query` - QA query (supports `mode="adaptive"`, `mode="hyper"`, `mode="hyper-lite"`, etc.)
- `POST /hyperrag/query_stream` - Streaming QA query
- `POST /hyperrag/insert` - Document insertion
- `POST /files/upload` - File upload
- `POST /files/embed` - Document embedding
- `GET /settings` - Get system settings
- `POST /settings` - Save system settings
- `GET /databases` - Get database list
