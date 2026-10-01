# Document 08: API Quota & Cost Control Manual

This manual provides strict operational procedures to protect your external API budgets, prevent rate-limit exhaustion, and eliminate accidental large-scale billing when onboarding custom datasets into Hyper-RAG.

---

## 1. The Cost Risk in Hyper-RAG

Unlike basic naive RAG systems that only perform embedding lookups, Hyper-RAG builds a **relational knowledge hypergraph**. During ingestion, for each text chunk:
1. It calls an **Embedding Model** to vectorize the chunk.
2. It calls an **LLM** with complex extraction prompts to discover entities, categorize them, and extract relationships.
3. It calls an **Embedding Model** again for each discovered entity and relationship.

```text
[COST MULTIPLIER EFFECT]
1 Dense Record (5 Perspectives) ➔ ~5 Text Chunks
  - 5 Embedding Calls (Chunks)
  - 5 to 10 LLM Extraction Passes (OpenRouter / OpenAI)
  - 15 to 25 Embedding Calls (Entities & Hyperedges)
Total for 1 Record: ~20-30 API operations (~8,000 to 15,000 tokens)

If you accidentally run 10,000 un-budgeted records:
  ➔ 250,000+ API operations
  ➔ 100+ Million LLM tokens consumed
  ➔ Fast HTTP 429 quota exhaustion or massive cloud bills!
```

---

## 2. The 10-Level Quota-Safe Staged Protocol

To guarantee that zero dollars and zero tokens are wasted, strictly adhere to the 10-level protocol:

| Stage Level | Activity | API Cost / Tokens | Protection Mechanism |
|---|---|---|---|
| **Level 0** | Raw source parsing & schema audit | **0 API calls** | Local Python scripts only; read-only files |
| **Level 1** | Normalization & deduplication | **0 API calls** | Deterministic Python rules; no LLM cleaning |
| **Level 2** | Context perspective generation | **0 API calls** | Local string formatting |
| **Level 3** | Preflight dry-run estimation | **0 API calls** | Calculates tokens & chunks offline |
| **Level 4** | Minimal isolated 1-record indexing | **Strictly bounded** (~5 embeddings, ~5 LLM calls) | Hardcoded `max_records = 1` guard |
| **Level 5** | Direct Python retrieval validation | **Minimal** (~2 queries = 2 embeddings + 2 LLM calls) | Offline pytest runner |
| **Level 6** | WebUI manual sanity check | **Minimal** (~1 query) | Localhost manual check |
| **Level 7** | Automated browser verification | **Bounded** (3 queries) | Automated Playwright script |
| **Level 8** | Controlled 3-record expansion | **Measured** (~15-30 embeddings, ~20 LLM calls) | Explicit `--max-records 3` flag |
| **Level 9** | Production batch scaling | **Budgeted & Checkpointed** | Checkpoint database; rate limit timers |

---

## 3. Preflight Cost & Token Estimation Formula

Before running indexing, run `--dry-run`. The pipeline executes the following offline estimation formula:

$$\text{Total Characters} = \sum \text{len}(\text{context.text})$$

$$\text{Estimated Chunks} = \max\left(1, \left\lfloor \frac{\text{Total Characters}}{1000} \right\rfloor + 1\right)$$

$$\text{Estimated Embedding Calls} \approx \text{Estimated Chunks} \times 3 \quad (\text{passages} + \text{entities} + \text{hyperedges})$$

$$\text{Estimated LLM Calls} \approx \text{Estimated Chunks} \times 2 \quad (\text{extraction passes})$$

$$\text{Estimated Token Volume} \approx \text{Estimated Chunks} \times 2,500 \text{ tokens (prompt + output)}$$

*Example from TSBC 1-Record Preflight*:
- Total characters across 5 contexts: `2,094`
- Estimated chunks: `3`
- Estimated embeddings: `~5–10`
- Estimated LLM extraction calls: `~6`
- Total tokens: `< 15,000 tokens`
- **Cost**: A fraction of a cent.

---

## 4. Hardcoded Pipeline Safety Guards

In [datasets/tsbc_maritime/pipeline.py](file:///d:/Rag/Hyper-RAG/datasets/tsbc_maritime/pipeline.py), we implemented programmatic guardrails that abort execution if limits are breached:

```python
# Programmatic guardrail in pipeline.py
if len(records_by_occ) > self.max_records:
    raise ValueError(
        f"SAFETY GUARD TRIGGERED: Dataset has {len(records_by_occ)} occurrences, "
        f"exceeding max_records={self.max_records}. Aborting to protect API quota!"
    )

if len(all_contexts) > self.max_contexts:
    raise ValueError(
        f"SAFETY GUARD TRIGGERED: Generated {len(all_contexts)} contexts, "
        f"exceeding max_contexts={self.max_contexts}. Aborting to protect API quota!"
    )
```

By defaulting CLI flags to `max_records = 1` and `max_contexts = 5`, typing `python -m datasets.your_dataset.pipeline --index` can **never accidentally index the full corpus**.

---

## 5. The "NEVER DO THIS" Rules

> [!CAUTION]
> **1. NEVER run an ingestion loop without an explicit `break` or record limit.**  
> If iterating through a 50,000-line JSONL file, always enforce `if count >= max_records: break`.

> [!CAUTION]
> **2. NEVER use high concurrency during initial onboarding.**  
> Keep `concurrency = 1`. Running 20 parallel async ingestion workers will exhaust API rate limits instantly and obfuscate error traces.

> [!CAUTION]
> **3. NEVER use an LLM for basic data transformation or cleaning.**  
> Regular expressions, string formatting, and date parsing must happen in local Python. Using an LLM to clean dates or deduplicate equipment burns quota for zero benefit.

> [!CAUTION]
> **4. NEVER index directly into `caches/default` or `caches/mock`.**  
> If an indexing run fails or produces corrupted vectors, having it isolated in `caches/<dataset>_test/` allows you to simply delete the folder and restart without harming other databases.

> [!CAUTION]
> **5. NEVER skip the dry-run stage.**  
> Always review `reports/<dataset>_dry_run_report.json` before passing `--index`.
