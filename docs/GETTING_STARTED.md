# Getting Started with Hyper-RAG & Adaptive Hyper-RAG
**The 5-Minute Developer Quick-Start Guide**

Welcome to Hyper-RAG! This guide will take you from zero to running your first adaptive retrieval query in under five minutes.

---

## 1. Prerequisites Check

Before starting, verify you have the required tools installed on your system:

| Tool | Minimum Version | Check Command |
|---|---|---|
| **Python** | 3.10 or 3.11 | `python --version` |
| **Node.js** | 18.0.0+ | `node --version` |
| **npm** | 9.0.0+ | `npm --version` |
| **Git** | 2.30+ | `git --version` |

---

## 2. Five-Minute Setup

### Step 1: Clone the Repository
```bash
git clone https://github.com/AbhishekYadav2207/Hyper-Rag.git
cd Hyper-Rag
```

### Step 2: Set Up Virtual Environment & Dependencies

#### On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r web-ui/backend/requirements.txt
```

#### On Linux / macOS (bash/zsh):
```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r web-ui/backend/requirements.txt
```

### Step 3: Install Frontend Dependencies
```bash
cd web-ui/frontend
npm install
cd ../..
```

### Step 4: Configure Your Environment (`.env`)
Copy the environment template:

```bash
# Windows
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

Open `.env` in your text editor and add your API keys:
```env
OPENROUTER_API_KEYS=your_openrouter_api_key_here
EMB_API_KEYS=your_mistral_api_key_here
```
*(Adaptive routing, sufficiency checks, and response validation are already enabled by default!)*

---

## 3. Verify Your Environment (Instant Smoke Test)

Run the fast offline unit test suite to verify your Python environment:

```bash
python -m pytest tests/unit -v
```

Expected output:
```text
======================= 67 passed in 3.36s =======================
```
All 67 tests run completely locally with **0 warnings** and require no API keys or internet connection.

---

## 4. Launch the Web Console

You need two terminal windows:

### Terminal 1: Start Backend API
```bash
# Ensure venv is active
python -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: Start Frontend Console
```bash
cd web-ui/frontend
npm run dev
```

Open your browser to:
👉 **`http://localhost:5173/`**

---

## 5. Your First Adaptive Queries

Once the Web Console opens in your browser:

### 1. Factual Query (Hyper-Lite)
- Ask: `"What is a counting-house?"`
- **Result**: Answer returns quickly. The metadata badge shows `Mode: lite` with a low complexity score ($6/100$). The system used fast entity-passage matching.

### 2. Comparative Relational Query (Hyper-Core)
- Ask: `"Compare Ebenezer Scrooge and nephew Fred regarding their values and family attitudes."`
- **Result**: The metadata badge shows `Mode: core` with a complexity score ($66/100$). The system automatically traversed multi-entity hyperedges to construct a comparative answer.

---

## 6. Architecture at a Glance

Hyper-RAG dynamically routes each query based on measured complexity and retrieved evidence:

```text
User Question
     │
     ▼
[Phase 1] Complexity Analysis (0–100 Score)
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
```

---

## 7. Next Steps

- **Read the Complete Beginner Manual**: [`docs/USER_MANUAL.md`](USER_MANUAL.md)
- **Explore Web Console Views**: [`docs/WEB_UI_GUIDE.md`](WEB_UI_GUIDE.md)
- **Deep-Dive into System Architecture**: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- **Understand Adaptive Hyper-RAG**: [`docs/ADAPTIVE_HYPERRAG.md`](ADAPTIVE_HYPERRAG.md)
- **Troubleshoot Common Issues**: [`docs/TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
- **Interactive REST API Reference**: [`docs/API_REFERENCE.md`](API_REFERENCE.md)
