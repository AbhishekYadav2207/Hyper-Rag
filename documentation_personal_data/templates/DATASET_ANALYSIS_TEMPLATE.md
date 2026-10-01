# Template: Dataset Analysis & Schema Audit

Use this template to record the initial offline profiling results for any new dataset prior to writing code.

---

## 1. Dataset Overview

- **Dataset Identifier**: `[e.g. tsbc_maritime, financial_sec_filings, clinical_trials]`
- **Source File Path**: `[Absolute path to raw file, e.g. D:\Datasets\my_data.jsonl]`
- **Storage Format**: `[JSONL / Monolithic JSON / CSV / Parquet / SQLite / Excel]`
- **Total File Size**: `[e.g. 142.5 MB]`
- **Total Record Count**: `[e.g. 68,355 lines / 12,400 rows]`
- **Primary Domain**: `[Maritime / Financial / Healthcare / Legal / IT Telemetry]`

---

## 2. Identifier & Cardinality Analysis

- **Primary Record Key**: `[e.g. occurrence_id, filing_id, case_number, patient_id]`
- **Unique Primary Key Count**: `[e.g. 44,329 unique occurrences]`
- **Record Splitting / Perspectives**: `[Does a single ID appear multiple times? If yes, what perspectives distinguish them?]`
- **Estimated Records per Entity**: `[e.g. 1.54 lines per occurrence]`

---

## 3. Discovered Schema & Data Types

| Field Name | Source Data Type | Null Count (%) | Sample Value | Notes / Handling Strategy |
|---|---|---|---|---|
| `[id]` | Integer / String | 0% | `4` | Canonical primary key |
| `[date]` | ISO String | 1.2% | `"1975-01-08 19:00:00"` | Parse to standardized UTC string |
| `[narrative]` | Long Text String | 5.4% | `"CREW RESCUED..."` | Primary text for context generation |
| `[category]` | Low-cardinality Enum | 0.0% | `"Accident"` | Anchor entity in overview perspective |
| `[nested_items]` | Array of Objects | 42.0% | `[{"type": "A"}]` | Requires deduplication algorithm |
| `[builder]` | String / Null | 98.4% | `null` | Explicit negative grounding required |

---

## 4. Nested Structures & Relational Arrays

List all nested arrays or sub-objects that require deduplication or relational linking:

1. **Child Array 1**: `[e.g. vessels -> lsa_equipment]`
   - *Duplicate Risk*: `[High / Medium / Low]`
   - *Identifying Composite Key*: `[e.g. (appliance_name, used_flag)]`
2. **Child Array 2**: `[e.g. vessels -> navigation_equipment]`
   - *Duplicate Risk*: `[High / Medium / Low]`
   - *Identifying Composite Key*: `[e.g. (aid_type, on_off_status)]`

---

## 5. Potential Risks & Failure Modes

- [ ] **Encoding Hazards**: `[Non-ASCII, Unicode characters, French/German accents]`
- [ ] **Data Sparsity**: `[Key fields missing in >80% of rows]`
- [ ] **Narrative Dilution**: `[Massive unstructured documents requiring custom chunking]`
- [ ] **Memory Constraints**: `[Corpus larger than available RAM requiring streaming]`
