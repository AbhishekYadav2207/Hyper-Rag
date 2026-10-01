# Document 03: Dataset Inspection & Normalization Guide

This guide details the technical procedures for inspecting raw, arbitrary domain datasets—including JSON, JSONL, CSV, Parquet, Excel, and SQL exports—and normalizing them into clean, canonical data structures ready for Hyper-RAG.

---

## 1. Input Format Ingestion Strategies

Raw personal or enterprise datasets arrive in diverse formats. Each format requires specific local loading strategies to prevent memory exhaustion and encoding errors:

| Source Format | Recommended Reader | Key Considerations | Failure Modes to Prevent |
|---|---|---|---|
| **JSONL / NDJSON** | Line-by-line `open(..., encoding='utf-8')` | Minimal memory footprint; streamable | Malformed JSON lines; trailing commas |
| **Monolithic JSON** | `json.load()` or `ijson` (streaming) | Parse once; extract root arrays | OOM on files > 1 GB; unbalanced brackets |
| **CSV / TSV** | `csv.DictReader` or `pandas.read_csv(chunksize=1000)` | Standard header parsing; type coercion | Escaped delimiters, mixed encodings (CP1252/UTF-8) |
| **Parquet** | `pyarrow.parquet` or `duckdb` | High performance columnar storage | Schema evolution across partitions |
| **Excel (.xlsx)** | `openpyxl` (read_only=True) | Sheet selection, date formatting | Formula cells evaluating to null; date serial numbers |
| **SQL Database** | SQLAlchemy / SQLite cursors | Deterministic `ORDER BY` for reproducible slicing | Unindexed queries; unclosed connection pools |

---

## 2. Offline Schema Discovery & Field Profiling

Before designing ingestion pipelines, execute an offline audit script to profile every field across the dataset:

```python
# Generic schema profiling pattern (Zero API calls)
import json
from collections import Counter
from pathlib import Path

def profile_dataset(file_path: Path):
    field_types = {}
    null_counts = Counter()
    total_records = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            total_records += 1
            for k, v in record.items():
                t = type(v).__name__
                field_types.setdefault(k, set()).add(t)
                if v is None or v == "" or v == []:
                    null_counts[k] += 1

    return {
        "total_records": total_records,
        "fields": {k: list(types) for k, types in field_types.items()},
        "null_percentages": {k: (null_counts[k] / total_records) * 100 for k in field_types}
    }
```

### Critical Profiling Questions to Answer
1. **Primary Identifier**: Is there a single unique ID field, or do you need a composite key (e.g. `client_id + date + sequence_no`)?
2. **Cardinality**: Are narrative fields long (>500 words), short snippets (<20 words), or empty?
3. **Array Nesting**: Do child arrays represent one-to-many relationships (e.g. a vessel having 4 pieces of equipment, a patient having 3 prescriptions)?
4. **Sparsity**: What percentage of records have missing values for key attributes?

---

## 3. Resolving Identities & Semantics

In Hyper-RAG, your data will be decomposed into text chunks, entities (vertices), and relationships (hyperedges). Defining proper identities during normalization prevents fragmentation:

```text
┌────────────────────────────────────────────────────────┐
│  Raw Input Row                                         │
│  { "OccID": 4, "VesselName": "ANVOURGON", "Year": 1975 }│
└───────────────────────────┬────────────────────────────┘
                            │ Normalization
                            ▼
┌────────────────────────────────────────────────────────┐
│  Canonical Occurrence Identity: occ_4                   │
│  Entity Identity 1: Vessel: ANVOURGON                  │
│  Entity Identity 2: Port: Piraeus                      │
│  Relationship / Hyperedge: (ANVOURGON, Explosion, 1975)│
└────────────────────────────────────────────────────────┘
```

1. **Canonical Record Identity**: The fundamental event or document boundary (e.g. `occurrence_id = 4`). All perspectives must carry this ID.
2. **Entity Identity**: Primary real-world entities mentioned in the text (e.g. `ANVOURGON`, `Halifax`, `Engine Room`). Names must be stripped of trailing spaces and casing normalized.
3. **Relationship Identity**: Co-occurrences that belong in the same hyperedge (e.g. Vessel + Event + Location).

---

## 4. Deduplication Algorithms for Nested Structures

Raw real-world records frequently contain duplicate child objects across multiple reporting perspectives. 

### The Composite Key Deduplication Pattern
In our TSBC implementation, Occurrence 4 contained duplicate lifeboat and magnetic compass entries because the same equipment was logged in both the summary perspective and the vessel narrative.

```python
def deduplicate_nested_items(items: list[dict], key_fields: list[str]) -> list[dict]:
    """
    Deduplicate a list of dictionaries based on a tuple of key fields.
    Case-insensitive, whitespace-stripped.
    """
    seen = set()
    deduped = []
    for item in items:
        # Build composite identity tuple
        key = tuple(str(item.get(k, "")).strip().lower() for k in key_fields)
        if key not in seen and any(part for part in key):
            seen.add(key)
            deduped.append(item)
    return deduped
```

*Example Applied to Maritime Equipment*:
- Raw input: Two records with `{"LsApplianceDisplayEng": "Lifeboat", "UsedEnumDisplayEng": "No"}`.
- Composite key: `("lifeboat", "no")`.
- Output: Exactly one cleaned lifeboat entry.

---

## 5. Handling Missing Fields & Preserving Provenance

### Avoiding Synthetic Hallucinations
A common defect in RAG ingestion is substituting null fields with plausible-sounding defaults (e.g. default country = "Unknown", default damage = "None"). 
- **Rule**: If a field is null, explicitly mark it as `None` or `"Not recorded"`.
- When generating prose contexts, write: *"Vessel builder is not recorded in source data."* This explicitly primes the LLM to refuse ungrounded queries rather than hallucinating plausible builders.

### Preserving Provenance Metadata
Every normalized record must retain a `provenance` dictionary:

```json
{
  "provenance": {
    "source_file": "maritime_corpus.jsonl",
    "source_occurrence_id": 4,
    "source_records_count": 2,
    "source_perspectives": ["occurrence_summary", "vessel_consolidated_narrative"],
    "extracted_timestamp": "2026-10-01T10:00:00Z"
  }
}
```

Provenance ensures that every retrieved chunk in the WebUI can be audited directly back to the raw source file.

---

## 6. Dataset-Specific vs. Generic Normalization

| Component | TSBC Maritime Corpus (Specific) | Generic Implementation (Your Dataset) |
|---|---|---|
| **Primary Key** | `occurrence_id` (Integer) | `id`, `uuid`, `row_id`, or composite string |
| **Child Arrays** | `lsa_equipment`, `navigation_equipment` | `transactions`, `symptoms`, `line_items`, `citations` |
| **Deduplication Keys** | Appliance name + Used indicator | Composite tuple of identifying subfields |
| **Perspectives Merged** | `occurrence_summary` + `vessel_consolidated_narrative` | Document header + incident logs + notes |
| **Geographic Keys** | Latitude, Longitude, Bearing, NearestLocation | Address, lat/long, office code, URL, IP address |
