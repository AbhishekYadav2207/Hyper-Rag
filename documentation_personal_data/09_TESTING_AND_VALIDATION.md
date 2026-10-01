# Document 09: Testing & Validation Framework

This document outlines the multi-tier testing framework required to validate custom dataset onboarding into Hyper-RAG before trusting the system with production queries.

---

## 1. Testing Pyramid for Custom Datasets

```text
               ▲
              / \
             /   \      Tier 4: Automated Browser Validation (Playwright)
            /     \     UI Rendering, Thinking clearing, 0 Console Errors
           /───────\
          /         \   Tier 3: Retrieval & Anti-Hallucination Tests
         /           \  Direct Facts, Multi-Field, Unrecorded Information
        /─────────────\
       /               \Tier 2: Index & Storage Integrity Tests
      /                 \Vector Dimensions, Hypergraph Vertices & Edges
     /───────────────────\
    /                     \ Tier 1: Local Unit Tests (Zero API Calls)
   /                       \Normalization, Deduplication, Context Generation
  ───────────────────────────
```

---

## 2. Tier 1: Local Unit Tests (Offline, Zero API Calls)

Implemented in [tests/test_tsbc_maritime.py](file:///d:/Rag/Hyper-RAG/tests/test_tsbc_maritime.py), this test suite runs entirely offline without credentials:

### A. Data Schema & Edge Case Tests
- **Empty Arrays**: Verify that records with empty child arrays (`vessels: []` or `lsa_equipment: []`) do not throw `IndexError`.
- **Null Fields**: Verify that records where all attributes except `id` are null still produce valid contexts containing "Not available".
- **Unicode & Non-ASCII**: Verify that French accents (`Côte-Nord`, `près de`), special symbols (`&`, `'`), and punctuation parse without encoding errors.

### B. Transformation & Deduplication Tests
- **Deduplication**: Feed intentional duplicate equipment entries into `normalize_occurrence()`; assert that output length is exactly 1.
- **Multi-Perspective Merging**: Feed 2 rows with identical `occurrence_id` but different perspectives; assert that both narratives are captured in `provenance.source_perspectives`.

### C. Safety Guard Tests
- Feed 2 records into a pipeline configured with `max_records = 1`; assert that it raises `ValueError("SAFETY GUARD TRIGGERED")`.

*Execution Command*:
```powershell
pytest tests/test_tsbc_maritime.py -v
```

---

## 3. Tier 2: Index & Storage Integrity Tests

After running `--index`, run programmatic checks to verify storage artifacts before launching any UI:

```python
# Storage integrity verification script
import json
from pathlib import Path
from hyperdb import HypergraphDB

def verify_storage(cache_dir: Path, expected_dim: int = 1024):
    hgdb_path = cache_dir / "hypergraph_chunk_entity_relation.hgdb"
    vdb_chunks_path = cache_dir / "vdb_chunks.json"
    vdb_entities_path = cache_dir / "vdb_entities.json"

    assert hgdb_path.exists(), "Hypergraph DB file missing!"
    assert vdb_chunks_path.exists(), "Chunks vector file missing!"
    assert vdb_entities_path.exists(), "Entities vector file missing!"

    # 1. Hypergraph check
    hg = HypergraphDB(storage_file=str(hgdb_path))
    v_count = len(hg.all_v)
    e_count = len(hg.all_e)
    print(f"[OK] Hypergraph loaded: {v_count} vertices, {e_count} hyperedges")
    assert v_count > 0, "Hypergraph has 0 vertices!"
    assert e_count > 0, "Hypergraph has 0 hyperedges!"

    # 2. Vector dimension check
    with open(vdb_chunks_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        matrix = data.get("matrix", [])
        if matrix:
            actual_dim = len(matrix[0])
            assert actual_dim == expected_dim, f"Dimension mismatch! Expected {expected_dim}, got {actual_dim}"
            print(f"[OK] Vector dimensions verified: {actual_dim}")
```

---

## 4. Tier 3: Retrieval & Anti-Hallucination Testing

Execute three distinct classes of query against your new database:

### Test Class 1: Direct Single-Hop Retrieval
- **Goal**: Verify basic factual grounding.
- **Query**: *"What vessel was involved in maritime occurrence 4?"*
- **Acceptance Criteria**: Answer must state **`ANVOURGON`** and identify its Greek flag and official number (4305).

### Test Class 2: Multi-Field Relational Synthesis
- **Goal**: Verify that facts across separate contexts (Damage + Casualties + Overview) are combined.
- **Query**: *"What damage was reported for maritime occurrence 4 and were there any casualties?"*
- **Acceptance Criteria**: Answer must confirm major damage to the Engine Room and vessel towed to Halifax; must explicitly state **0 fatalities, 0 serious injuries, 0 missing individuals**.

### Test Class 3: Anti-Hallucination Negative Fact Test
- **Goal**: Prove that the LLM will not invent information absent from the source data.
- **Query**: *"Who was the builder of the vessel ANVOURGON?"*
- **Ground Truth**: Builder information was null/absent in source records.
- **Acceptance Criteria**: Answer must explicitly state that shipbuilder information is **"not available"**, **"not recorded"**, or **"not specified"** in the TSBC records. If the model names a shipyard, the test **FAILS**.

---

## 5. Tier 4: Automated Browser & WebUI Testing

Run [scratch/verify_tsbc_browser.py](file:///d:/Rag/Hyper-RAG/scratch/verify_tsbc_browser.py) to validate the complete frontend user experience:

1. **Database Selection**: Verifies that the header dropdown successfully selects the target database (`tsbc_maritime_test`).
2. **Thinking State Transition**:
   - Submits query.
   - Waits for `"Thinking..."` to become visible within 6 seconds.
   - Captures `tsbc_query1_thinking.png`.
3. **Response Rendering**:
   - Waits for `"Thinking..."` to disappear.
   - Checks that the final prose bubble contains the expected grounded facts.
   - Captures `tsbc_query1_answered.png`.
4. **Console Hygiene**: Checks that `console.error` and `console.warn` contain 0 entries.
5. **Network Integrity**: Checks that all calls to `POST /hyperrag/query` return HTTP 200.
