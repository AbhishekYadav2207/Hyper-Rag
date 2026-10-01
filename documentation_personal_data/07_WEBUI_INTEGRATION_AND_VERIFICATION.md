# Document 07: WebUI Integration & Verification

This guide explains how custom-indexed knowledge bases are exposed to the Hyper-RAG React Web Console, how the backend discovers multi-database folders, how the frontend manages state, and how to verify interactions using automated browser agents.

---

## 1. Database Discovery Architecture

The WebUI does not require hardcoding database names. Instead, it discovers available knowledge bases dynamically from the filesystem:

```text
┌────────────────────────────────────────────────────────┐
│               caches/<dataset_name>_test/              │
│       (Isolated indexing output containing .hgdb)      │
└───────────────────────────┬────────────────────────────┘
                            │ (Windows Junction: mklink /J)
                            ▼
┌────────────────────────────────────────────────────────┐
│           hyperrag_cache/<dataset_name>_test           │
│       (Directory Junction inside discovery root)       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│     db_manager.list_databases() (web-ui/backend/db.py) │
│       - Scans hyperrag_cache/ for subdirectories       │
│       - Returns list: ["mock", "<dataset_name>_test"]  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│            GET http://127.0.0.1:8000/databases         │
│       - Frontend fetches list on page mount            │
│       - Populates database selector dropdown in header │
└────────────────────────────────────────────────────────┘
```

### Creating the Filesystem Junction
On Windows, create the link using `mklink /J`:
```powershell
cmd /c mklink /J ".\hyperrag_cache\tsbc_maritime_test" ".\caches\tsbc_maritime_test"
```
On Linux/macOS, use a symbolic link:
```bash
ln -s /path/to/Hyper-RAG/caches/tsbc_maritime_test /path/to/Hyper-RAG/hyperrag_cache/tsbc_maritime_test
```

---

## 2. Frontend State Management & The "Thinking..." Hang Case Study

During the TSBC maritime integration, we diagnosed and permanently resolved a critical WebUI defect where queries hung indefinitely on `"Thinking..."`.

### The Symptom
When submitting a query in the Chat view, the UI rendered a message bubble with a decision badge showing `"Thinking..."`. Even after the FastAPI backend returned HTTP 200 with the full answer text, the UI spinner spun forever and the answer never rendered.

### The Diagnostic Triage (How to Diagnose Frontend Bugs)
1. **Step 1: Check Backend Logs**:  
   Backend logs showed:
   ```text
   INFO: 127.0.0.1:54321 - "POST /hyperrag/query HTTP/1.1" 200 OK
   ```
   *Conclusion*: The backend was healthy and not hanging.
2. **Step 2: Inspect Browser Network Tab**:  
   Inspecting the response body for `POST /hyperrag/query` revealed:
   ```json
   {
     "success": true,
     "response": "In Maritime Occurrence 4, the vessel ANVOURGON...",
     "entities": [...],
     "hyperedges": [...]
   }
   ```
   *Conclusion*: Full response was delivered to the browser. The bug was inside the React client state logic.
3. **Step 3: Inspect React State in `web-ui/frontend/src/pages/Home/index.tsx`**:  
   We inspected `updateLastMessage(content, extraData)`:
   ```typescript
   // DEFECTIVE IMPLEMENTATION:
   setConversation(conv => ({
       ...conv,
       messages: conv.messages.map((msg, index) =>
           index === conv.messages.length - 1
               ? {
                   ...msg,
                   // BUG: 'content' parameter was completely ignored!
                   // msg.content remained the initial placeholder 'Thinking...'
                   entities: extraData?.entities || msg.entities || [],
                   hyperedges: extraData?.hyperedges || msg.hyperedges || [],
                   adaptive_decision: extraData?.adaptive_decision,
               }
               : msg
       )
   }))
   ```
   *Conclusion*: The metadata (`entities`, `hyperedges`) was merged into the message, but `msg.content` was never assigned the new string, leaving `"Thinking..."` permanently displayed.
4. **Step 4: Loading Guard**:  
   `setIsLoading(false)` was not in a `finally` block. If an error occurred in parsing, the loading state never cleared.

### The Verified Solution
1. In `Home/index.tsx`:
   ```typescript
   content: content !== undefined && content !== null ? content : msg.content
   ```
2. Supported both API response conventions:
   ```typescript
   const responseContent = data.response || data.answer || 'No response content'
   ```
3. Wrapped query calls in `try ... catch ... finally { setIsLoading(false) }`.
4. In `web-ui/backend/main.py`, ensured both keys are returned:
   ```python
   return {
       "success": True,
       "response": result.get("response", ""),
       "answer": result.get("response", ""),
       ...
   }
   ```
5. Rebuilt the frontend bundle:
   ```powershell
   cd web-ui/frontend
   npm run build
   ```

---

## 3. Automated Browser Verification Workflow (Playwright)

Never claim that WebUI integration works without automated browser validation. We developed [scratch/verify_tsbc_browser.py](../scratch/verify_tsbc_browser.py) to execute automated end-to-end browser tests.

```python
# Reusable Playwright Verification Pattern
import asyncio
from playwright.async_api import async_playwright

async def verify_webui():
    async with async_playwright() as p:
        # Launch system Chrome or Edge in headless mode
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        # Step 1: Open WebUI with pre-set database
        await page.add_init_script("localStorage.setItem('selectedDatabase', 'tsbc_maritime_test');")
        await page.goto("http://127.0.0.1:8000", wait_until="networkidle")

        # Step 2: Submit query
        textarea = page.locator("textarea")
        await textarea.fill("What vessel was involved in maritime occurrence 4?")
        await page.keyboard.press("Enter")

        # Step 3: Verify Thinking state appears
        thinking = page.locator("text='Thinking...'")
        await thinking.wait_for(state="visible", timeout=6000)

        # Step 4: Verify Thinking state clears and answer renders
        await thinking.wait_for(state="hidden", timeout=90000)
        prose_blocks = await page.locator("div.prose").all_inner_texts()
        answer = prose_blocks[-1]

        assert "ANVOURGON" in answer.upper()
        await page.screenshot(path="scratch/verified_query.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_webui())
```

### Verification Deliverables to Archive
- `scratch/tsbc_db_selected.png`: Proves database selector displayed custom dataset.
- `scratch/tsbc_query1_thinking.png`: Proves initial loading state triggered.
- `scratch/tsbc_query1_answered.png`: Proves full prose answer rendered cleanly.
- `console_logs`: Proves 0 runtime uncaught JavaScript exceptions.

---

## 4. API Key Management Architecture (WebUI Settings Source of Truth)

Hyper-RAG enforces a strict server-side credential management architecture where the **WebUI Settings interface is the authoritative runtime source of truth**:

```text
WebUI Settings (/#/Setting)
          │ (Masked input, password fields)
          ▼
POST /settings (Over HTTPS / Local IPC)
          │ (Server-side validation & atomic write)
          ▼
Server-Side settings.json (0600 permissions, gitignored)
          │ (Dynamic lazy loading per request)
          ▼
Runtime Client Initializer
   ├─► OpenRouter LLM Client (<OPENROUTER_API_KEY>)
   └─► Mistral Embedding Client (<MISTRAL_API_KEY>)
```

### Precedence and Security Rules
1. **WebUI Settings is Authoritative**:
   - `WebUI Settings value > missing credential / configuration error`.
   - `.env` is **not** the normal runtime credential source for the WebUI. If no key is configured in WebUI Settings, the system will not silently pull keys from `.env`; it returns an explicit error prompting the user to configure Settings.
2. **Distinct Multi-Provider Credentials**:
   - **LLM Provider**: OpenRouter API Key (default model: `nvidia/nemotron-3-ultra-550b-a55b:free`, base URL: `https://openrouter.ai/api/v1`).
   - **Embedding Provider**: Mistral API Key (canonical model: `mistral-embed`, 1024 dimensions, base URL: `https://api.mistral.ai/v1`).
3. **No Secret Leaks to Frontend**:
   - `GET /settings` returns masked preview strings (e.g. `••••••••••••abcd`) and boolean flags (`apiKeyConfigured: true`). Full secret keys are never returned.
   - Raw credentials are never stored in `localStorage` or `sessionStorage`.
4. **Dynamic Client Instantiation**:
   - Clients are created lazily at runtime. Updating credentials in the Settings UI immediately takes effect on the next query or embedding operation without restarting the server.
5. **Connection Testing**:
   - Both LLM and Embedding connections can be tested independently from the Settings UI via `POST /test-api`.

