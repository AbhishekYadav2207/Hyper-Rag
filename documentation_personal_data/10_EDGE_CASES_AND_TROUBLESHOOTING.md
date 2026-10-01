# Document 10: Edge Cases & Troubleshooting Field Guide

This troubleshooting handbook provides symptoms, root causes, confirmation steps, and verified fixes for errors encountered when integrating custom datasets into Hyper-RAG.

---

## Issue 01: `ModuleNotFoundError: No module named 'db'`

- **Symptom**: Starting Uvicorn backend crashes immediately on startup:
  ```text
  ModuleNotFoundError: No module named 'db'
  ```
- **Likely Cause**: In `web-ui/backend/main.py`, imports from sibling files (`db.py`, `file_manager.py`) were written as top-level imports (`from db import ...`). When executed via package notation `uvicorn web-ui.backend.main:app`, Python resolves modules relative to root, not the subfolder.
- **How to Confirm**: Run `python -m uvicorn web-ui.backend.main:app --port 8000` from project root and inspect traceback.
- **Fix**: In `web-ui/backend/main.py`, use explicit relative package imports:
  ```python
  from .db import get_hypergraph, getFrequentVertices, ...
  from .file_manager import file_manager
  ```
- **Verification**: Restart Uvicorn; backend starts on port 8000 without import errors.

---

## Issue 02: WebUI Permanently Stuck on "Thinking..."

- **Symptom**: Query submitted in WebUI shows decision badge with `"Thinking..."` forever. Backend terminal logs confirm `POST /hyperrag/query HTTP/1.1 200 OK` and show completed LLM synthesis.
- **Likely Cause**:
  1. In `web-ui/frontend/src/pages/Home/index.tsx`, `updateLastMessage(content, extraData)` neglected to assign `content` to the message object, keeping `msg.content` as the placeholder string `"Thinking..."`.
  2. `setIsLoading(false)` was not placed inside a `finally` block.
  3. API response field naming mismatch (`data.response` vs `data.answer`).
- **How to Confirm**: Open browser DevTools Network tab, inspect `POST /hyperrag/query` response. If JSON contains valid answer string, the bug is client-side state in React.
- **Fix**:
  1. In `web-ui/frontend/src/pages/Home/index.tsx`:
     ```typescript
     content: content !== undefined && content !== null ? content : msg.content
     ```
  2. Support fallback: `const responseContent = data.response || data.answer || 'No response content'`.
  3. Wrap queries in `try ... finally { setIsLoading(false) }`.
  4. In `web-ui/backend/main.py`, return both keys: `{"response": resp, "answer": resp}`.
  5. Run `cd web-ui/frontend && npm run build`.
- **Verification**: Run Playwright test `python scratch/verify_tsbc_browser.py`; "Thinking..." clears within seconds.

---

## Issue 03: Embedding Dimension Mismatch (1024 vs. 1536)

- **Symptom**: Query throws `ValueError: shapes (1024,) and (1536,) not aligned` or retrieval returns zero matching vectors.
- **Likely Cause**: The knowledge base was indexed using `mistral-embed` (1024 dimensions), but `settings.json` or query fallback functions defaulted to OpenAI `text-embedding-3-small` (1536 dimensions).
- **How to Confirm**: Check vector length in `caches/<dataset>/vdb_chunks.json` (1024) vs. vector length in query log (1536).
- **Fix**:
  1. Set `EMB_MODEL=mistral-embed` and `EMB_DIM=1024` in `my_config.py` and `settings.example.json`.
  2. In `web-ui/backend/main.py`, add runtime normalization in `get_effective_settings()`:
     ```python
     if saved.get("embeddingModel") in ("text-embedding-3-small", None) or saved.get("embeddingDim") in (1536, None):
         saved["embeddingModel"] = "mistral-embed"
         saved["embeddingDim"] = 1024
         saved["embeddingBaseUrl"] = "https://api.mistral.ai/v1"
     ```
  3. In `get_hyperrag_embedding_func()`, ensure `EMB_API_KEY` is passed to Mistral API.
- **Verification**: Vector search runs cleanly without shape mismatch exceptions.

---

## Issue 04: Windows Console Encoding Crash (`UnicodeEncodeError`)

- **Symptom**: Running scripts or starting backend crashes with:
  ```text
  UnicodeEncodeError: 'charmap' codec can't encode characters in position ...: character maps to <undefined>
  ```
- **Likely Cause**: Windows PowerShell/CMD default to legacy OEM codepages (CP1252/CP437) which fail on Unicode symbols like arrows (`→`), French accents (`Rivière-au-Renard`), or emojis.
- **How to Confirm**: Run script in PowerShell and observe crash on `print()`.
- **Fix**: Standardize console streams in Python entry points:
  ```python
  import sys
  if sys.platform == "win32":
      if sys.stdout and hasattr(sys.stdout, "reconfigure"):
          sys.stdout.reconfigure(encoding="utf-8", errors="replace")
      if sys.stderr and hasattr(sys.stderr, "reconfigure"):
          sys.stderr.reconfigure(encoding="utf-8", errors="replace")
  ```
- **Verification**: Unicode narratives print cleanly without terminating the process.

---

## Issue 05: Custom Database Missing from WebUI Dropdown

- **Symptom**: The dataset was indexed into `caches/my_dataset_test/`, but the WebUI header dropdown only shows `mock` and `default`.
- **Likely Cause**: The backend scans `hyperrag_cache/`, not `caches/`. The directory junction was not created.
- **How to Confirm**: Run `GET http://127.0.0.1:8000/databases`. If your dataset is not in the array, the directory is absent from `hyperrag_cache/`.
- **Fix**: Create a directory junction in `hyperrag_cache/`:
  ```powershell
  cmd /c mklink /J "D:\Rag\Hyper-RAG\hyperrag_cache\my_dataset_test" "D:\Rag\Hyper-RAG\caches\my_dataset_test"
  ```
- **Verification**: Refresh browser; database appears immediately in dropdown.

---

## Issue 06: HTTP 429 Rate Limit on OpenRouter / Mistral

- **Symptom**: Query synthesis fails with `HTTP 429 Too Many Requests`.
- **Likely Cause**: Free-tier rate limits reached on OpenRouter or Mistral API.
- **How to Confirm**: Check Uvicorn console for HTTP 429 status code.
- **Fix**:
  1. Add multiple API keys to `.env` (`OPENROUTER_API_KEYS=key1,key2,key3`).
  2. Hyper-RAG's `parse_api_keys()` in `my_config.py` supports round-robin pool rotation with automatic cooldowns.
  3. If using single key, wait 60 seconds before re-querying.
- **Verification**: Key pool automatically switches to healthy key.

---

## Issue 07: Model Hallucinates Facts for Missing Attributes

- **Symptom**: User asks "Who built vessel ANVOURGON?" and the model invents a shipyard name instead of stating the fact is unrecorded.
- **Likely Cause**: The context perspective did not explicitly state that the field was absent, so the LLM defaulted to parametric training memory.
- **How to Confirm**: Review `contexts/<dataset>_contexts.json`. Does it mention builder info at all?
- **Fix**: In your context generator, explicitly write negative statements for absent fields:
  ```python
  if not vessel.get("builder"):
      text += " Vessel builder information is not recorded in source data."
  ```
- **Verification**: Re-index and re-query. LLM confirms builder information is unavailable.

---

## Issue 08: Duplicate Child Entities Inflating Contexts

- **Symptom**: Generated contexts contain repeated sentences: *"Lifeboat carried onboard. Lifeboat carried onboard."*
- **Likely Cause**: Multiple source rows (e.g. `occurrence_summary` and `vessel_consolidated_narrative`) contained identical child equipment records.
- **How to Confirm**: Check length of child array in raw JSON vs normalized JSON.
- **Fix**: Implement composite tuple deduplication in `RecordNormalizer`:
  ```python
  seen = set()
  for item in items:
      key = (item.get("name"), item.get("status"))
      if key not in seen:
          seen.add(key)
          deduped.append(item)
  ```
- **Verification**: Run `pytest tests/test_tsbc_maritime.py -k test_deduplication_equipment`; passes with 1 entry.
