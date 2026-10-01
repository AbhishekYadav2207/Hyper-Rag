# Hyper-RAG Troubleshooting & Diagnostic Runbook

This guide covers symptom identification, root-cause diagnosis, and step-by-step resolution for common issues encountered when installing, configuring, running, and developing Hyper-RAG.

---

## 1. Installation & Environment Issues

### 1.1 `ModuleNotFoundError: No module named 'hyperrag'`
- **Symptoms**: Running a test, example, or server fails immediately with `ModuleNotFoundError: No module named 'hyperrag'`.
- **Likely Cause**: The Python virtual environment is not activated, or the command was executed from outside the repository root.
- **How to Check**:
  ```bash
  python -c "import sys; print(sys.prefix)"
  ```
  If this outputs your global Python directory instead of `.../venv`, the virtual environment is inactive.
- **How to Fix**:
  1. Activate your virtual environment:
     - Windows: `.\venv\Scripts\Activate.ps1`
     - Linux/macOS: `source venv/bin/activate`
  2. If running scripts directly from subfolders, ensure the root directory is on your `PYTHONPATH`:
     - Windows PowerShell: `$env:PYTHONPATH="."`
     - Linux/macOS: `export PYTHONPATH="."`

---

### 1.2 Windows Console Encoding Error (`UnicodeDecodeError` / `UnicodeEncodeError`)
- **Symptoms**: Python crashes when logging or printing special characters, or outputs `charmap codec can't encode character`.
- **Likely Cause**: Windows console codepage defaults to legacy ANSI (e.g. CP1252) instead of UTF-8.
- **How to Check**:
  ```powershell
  chcp
  ```
  If the output is `Active code page: 437` or `1252`, UTF-8 is disabled.
- **How to Fix**:
  1. Enable Python UTF-8 mode in PowerShell:
     ```powershell
     $env:PYTHONUTF8=1
     ```
  2. Switch active codepage to UTF-8:
     ```powershell
     chcp 65001
     ```

---

## 2. API Key & Provider Issues

### 2.1 HTTP 401 Unauthorized (`AuthenticationError`)
- **Symptoms**: Backend logs show `HTTP 401 Unauthorized` when sending a query.
- **Likely Cause**: The API key in `.env` is missing, expired, misspelled, or surrounded by accidental quotation marks or whitespace.
- **How to Check**:
  ```bash
  python -c "import my_config; print(bool(my_config.OPENROUTER_API_KEYS), bool(my_config.EMB_API_KEYS))"
  ```
  If either returns `False`, the key is missing.
- **How to Fix**:
  1. Open `.env` and verify:
     ```env
     OPENROUTER_API_KEYS=sk-or-v1-...
     EMB_API_KEYS=...
     ```
  2. Remove any trailing commas, spaces, or surrounding quotes (`"..."`).
  3. Verify key validity using the internal smoke tests:
     ```bash
     python tests/internal/test_openrouter.py
     python tests/internal/test_embedding.py
     ```

---

### 2.2 HTTP 429 Rate Limit Exceeded
- **Symptoms**: Queries fail or stall with `429 Too Many Requests`.
- **Likely Cause**: Upstream provider request-rate or token-rate quota has been reached on the active key.
- **How to Check**: Check application logs for `[KeyPool] Key ... received 429, cooling down`.
- **How to Fix**:
  1. Provide multiple API keys separated by commas in `.env`:
     ```env
     OPENROUTER_API_KEYS=key1,key2,key3
     EMB_API_KEYS=key1,key2
     ```
     The internal `KeyPool` will automatically rotate between keys and manage backoff cooldowns.
  2. Reduce concurrent queries or lower `HYPERRAG_MAX_QPS`.

---

### 2.3 Mistral Embedding Dimension Mismatch (`EMB_DIM` Error)
- **Symptoms**: Startup validation fails with `[Config Error] Missing or invalid configuration: EMB_DIM (must be 1024)`.
- **Likely Cause**: `EMB_DIM` in `.env` was changed from `1024` or omitted.
- **How to Check**: Inspect `EMB_DIM` in `.env`.
- **How to Fix**: Ensure `EMB_DIM=1024` in `.env`. The `mistral-embed` model strictly requires 1024 output dimensions.

---

## 3. Server & Network Issues

### 3.1 Port 8000 / 8002 Already in Use (`Errno 98` or `WSAEADDRINUSE`)
- **Symptoms**: Starting Uvicorn outputs `[Errno 98] Address already in use` or `WSAEADDRINUSE`.
- **Likely Cause**: A previous server instance or another application is occupying the port.
- **How to Check**:
  - Windows: `netstat -ano | findstr :8000`
  - Linux/macOS: `lsof -i :8000`
- **How to Fix**:
  1. Terminate the blocking process, OR:
  2. Launch the server on a different port:
     ```bash
     python -m uvicorn web-ui.backend.main:app --port 8005
     ```

---

### 3.2 Frontend Cannot Reach Backend ("Network Error" in Chat)
- **Symptoms**: Chat interface in the browser displays `Network Error` or fails to send messages.
- **Likely Cause**: The FastAPI backend is not running, or Vite is proxying to the wrong URL.
- **How to Check**: Open `http://127.0.0.1:8000/` in your browser. It should return `{"message": "Welcome to HyperRAG Web-UI API"}`.
- **How to Fix**:
  1. Start the backend: `python -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000`.
  2. Confirm `vite.config.js` proxy targets `http://127.0.0.1:8000`.

---

## 4. Adaptive RAG & Pipeline Diagnoses

### 4.1 Query Unexpectedly Routed to Core
- **Symptoms**: A seemingly simple question ran in Core mode instead of Lite mode.
- **Likely Cause**: The question contained comparative phrases (*"versus"*, *"differ"*), causal words (*"why"*, *"cause"*), or multi-entity references that triggered Phase 1 or Phase 2.1 scoring.
- **How to Check**: Inspect `rag.last_adaptive_decision.features` or read the console log:
  ```text
  [Adaptive RAG] Initial complexity score: 62 (threshold: 60) -> Initial mode: CORE
  ```
- **How to Fix**:
  1. This is normal adaptive behavior! The system detected semantic complexity.
  2. If you want a higher threshold before routing to Core, raise `ADAPTIVE_CORE_THRESHOLD` from `60` to `70` in `.env`.
  3. To strictly force Lite mode regardless of complexity, supply `param=QueryParam(mode="lite")`.

---

### 4.2 Query Escalated from Lite to Core
- **Symptoms**: Log outputs `Escalating LITE -> CORE. Reason: Missing relationship evidence...`.
- **Likely Cause**: Phase 1 selected Lite, but Phase 2 detected that retrieved context lacked required relational hyperedges or was insufficient to answer the question.
- **How to Check**: Check `rag.last_adaptive_decision.escalation_reason`.
- **How to Fix**:
  - This is an intentional safety feature! It prevented an incomplete or hallucinated answer.
  - If you wish to disable escalation entirely, set `ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED=false` in `.env`.

---

### 4.3 Phase 3 Validation Flags `valid = False`
- **Symptoms**: API response shows `"validation": {"valid": false, "score": 62.0}`.
- **Likely Cause**: The generated answer missed key aspects of the question (e.g. compared only one of two entities), contained ungrounded statistics not in the source text, or had an evidence score $< 30$.
- **How to Check**: Inspect `rag.last_validation_result.missing_aspects` and `unsupported_claims`.
- **How to Fix**:
  - The answer was still returned intact! Validation is purely diagnostic.
  - Review the retrieved documents to ensure source texts contain the requested facts.
  - If desired, adjust the validation threshold via `ADAPTIVE_VALIDATION_THRESHOLD` in `.env`.

---

## 5. Storage & Cache Reset Runbook

### How to Completely Reset Local State
If a database or vector index becomes corrupted:
1. Stop backend and frontend servers (`Ctrl + C`).
2. Delete the cache directories:
   - Windows PowerShell:
     ```powershell
     Remove-Item -Recurse -Force .\caches\default, .\hyperrag_cache -ErrorAction SilentlyContinue
     ```
   - Linux/macOS:
     ```bash
     rm -rf ./caches/default ./hyperrag_cache
     ```
3. Restart the backend. Fresh databases will be initialized automatically.

---

## 6. Web UI & Frontend Diagnostics

### 6.1 Adaptive RAG Stuck on "Thinking..." Even Though Backend Returned HTTP 200
- **Symptoms**: After submitting a query, the Web UI permanently displays the Adaptive decision badge with `"Thinking..."`, despite the backend logs confirming successful LLM response and `POST /hyperrag/query HTTP/1.1 200 OK`.
- **Root Cause**:
  1. **Message Content State Drop**: In `web-ui/frontend/src/pages/Home/index.tsx`, the `updateLastMessage(content, extraData)` function accepted the response `content` string, but neglected to assign `content` to the message object in `conv.messages.map()`. The metadata (`adaptive_decision`, `entities`, etc.) was merged, but `msg.content` remained hardcoded to `'Thinking...'`.
  2. **Loading State Guard**: If an exception or malformed payload occurred, `isLoading` could remain true if not protected by a `finally { setIsLoading(false) }` block.
- **Resolution**:
  1. In `Home/index.tsx`, ensure `content: content !== undefined && content !== null ? content : msg.content` is set in `updateLastMessage`.
  2. Support both `data.response` and `data.answer` in single and compare modes.
  3. Wrap queries in `try ... catch ... finally { setIsLoading(false) }`.
  4. Run `npm run build` in `web-ui/frontend` to update static distribution assets.

### 6.2 Embedding Dimension Mismatch (1024 vs 1536)
- **Symptoms**: Query embedding generates a 1536-dimensional vector (`text-embedding-3-small`) while stored vector indexes (`vdb_chunks.json`, `vdb_entities.json`, `vdb_relationships.json`) expect 1024 dimensions.
- **Root Cause**: Stale configuration in `settings.json` or backend defaults specifying `text-embedding-3-small` and dimension `1536` instead of canonical Mistral embeddings.
- **Resolution**:
  1. Configure `embeddingModel: "mistral-embed"`, `embeddingBaseUrl: "https://api.mistral.ai/v1"`, and `embeddingDim: 1024` in `settings.json` and `web-ui/backend/main.py`.
  2. In `get_effective_settings()`, automatically normalize legacy `text-embedding-3-small` or 1536-dim entries to `mistral-embed` and `1024`.
  3. In `get_hyperrag_embedding_func()`, ensure `EMB_API_KEY` is utilized with Mistral base URL.

