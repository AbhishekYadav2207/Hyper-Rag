# Document 12: Reusable Command Reference

This reference documents the verified CLI commands used in the Hyper-RAG repository for environment setup, offline auditing, dry-run estimation, isolated indexing, backend serving, automated testing, and browser verification.

---

## 1. Environment & Status Verification

### Check Hyper-RAG Python Import
```powershell
python -c "import hyperrag; print('HyperRAG OK')"
```

### Check Git Working Tree & Modified Files
```powershell
git status -s
```

### View Recent Git Commits
```powershell
git log -n 5 --oneline
```

---

## 2. TSBC Maritime Pipeline Commands (Case Study Reference)

### A. Run Source Corpus Local Audit (Zero API Calls)
```powershell
python scratch/audit_tsbc_corpus.py
```
*Output: `scratch/audit_results.json` documenting 68,355 lines and 44,329 occurrences.*

### B. Run Deterministic Candidate Scoring
```powershell
python scratch/find_deterministic_candidates.py
```
*Output: `scratch/scored_candidates.json` confirming Occurrence 4 as top-ranked candidate.*

### C. Run 1-Record Dry-Run Preflight (Zero API Calls)
```powershell
python -m datasets.tsbc_maritime.pipeline --dataset tsbc_maritime_test_1 --dry-run
```
*Output: `datasets/tsbc_maritime/reports/tsbc_maritime_test_1_dry_run_report.json`.*

### D. Run 1-Record Isolated Hyper-RAG Indexing
```powershell
python -m datasets.tsbc_maritime.pipeline --dataset tsbc_maritime_test_1 --index
```
*Builds index into `caches/tsbc_maritime_test/` and links to `hyperrag_cache/tsbc_maritime_test`.*

### E. Run Controlled 3-Record Dry-Run (Zero API Calls)
```powershell
python -m datasets.tsbc_maritime.pipeline --dataset tsbc_maritime_test_3 --max-records 3 --max-contexts 15 --dry-run
```

### F. Run Controlled 3-Record Indexing
```powershell
python -m datasets.tsbc_maritime.pipeline --dataset tsbc_maritime_test_3 --max-records 3 --max-contexts 15 --index
```

---

## 3. WebUI & Backend Server Commands

### Start FastAPI Backend with Hot Reload (Port 8000)
- **Windows PowerShell**:
  ```powershell
  python -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000 --reload
  ```
- **Linux / macOS**:
  ```bash
  python -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000 --reload
  ```

### Build Frontend Static Bundle
```powershell
cd web-ui/frontend
npm run build
cd ../..
```

### Create Filesystem Junction for WebUI Database Discovery
- **Windows PowerShell**:
  ```powershell
  cmd /c mklink /J "D:\Rag\Hyper-RAG\hyperrag_cache\tsbc_maritime_test" "D:\Rag\Hyper-RAG\caches\tsbc_maritime_test"
  ```
- **Linux / macOS**:
  ```bash
  ln -s /path/to/Hyper-RAG/caches/tsbc_maritime_test /path/to/Hyper-RAG/hyperrag_cache/tsbc_maritime_test
  ```

### Query Database Discovery Endpoint via cURL
```powershell
curl http://127.0.0.1:8000/databases
```

### Query Hyper-RAG API via cURL
```powershell
curl -X POST http://127.0.0.1:8000/hyperrag/query `
  -H "Content-Type: application/json" `
  -d '{\"query\": \"What vessel was involved in maritime occurrence 4?\", \"mode\": \"adaptive\", \"database\": \"tsbc_maritime_test\"}'
```

---

## 4. Automated Testing & Verification Commands

### Run Offline Pytest Suite (Zero API Calls)
```powershell
pytest tests/test_tsbc_maritime.py -v
```

### Run Full Hyper-RAG Core Test Suite
```powershell
pytest tests/unit/ -v
```

### Run End-to-End Headless Browser Verification (Playwright)
```powershell
python scratch/verify_tsbc_browser.py
```
*Captures screenshots into `scratch/tsbc_db_selected.png`, `scratch/tsbc_query1_thinking.png`, `scratch/tsbc_query1_answered.png`.*

---

## 5. Generic Parameterized Commands for Your Next Dataset

Replace `<dataset_name>` with your custom dataset identifier (e.g. `financial_sec_q3`, `clinical_oncology`):

### Dry-Run Estimation Pattern
```powershell
python -m datasets.<dataset_name>.pipeline --dataset <dataset_name>_test_1 --dry-run
```

### Isolated Indexing Pattern
```powershell
python -m datasets.<dataset_name>.pipeline --dataset <dataset_name>_test_1 --max-records 1 --max-contexts 5 --index
```

### Directory Junction Creation Pattern
```powershell
cmd /c mklink /J "D:\Rag\Hyper-RAG\hyperrag_cache\<dataset_name>_test" "D:\Rag\Hyper-RAG\caches\<dataset_name>_test"
```

### Run Custom Dataset Unit Tests
```powershell
pytest tests/test_<dataset_name>.py -v
```
