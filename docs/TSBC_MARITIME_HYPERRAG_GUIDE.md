# TSBC Maritime Corpus Integration Guide for Hyper-RAG

This guide details the integration of the Transportation Safety Board of Canada (TSBC) Maritime Occurrence Corpus into the Hyper-RAG system, following an isolated, safe, and minimal-API-cost workflow.

---

## 1. Overview & Architecture

The TSBC integration pipeline connects real Canadian maritime occurrence records to Hyper-RAG's adaptive hypergraph reasoning engine while preserving existing mock indexes, enforcing strict API quota guards, and supporting the existing WebUI interface.

```text
┌────────────────────────────────────────────────────────┐
│  external_data/maritime_corpus.jsonl │
│  (68,355 lines | 44,329 occurrences | Local & Read-Only)│
└───────────────────────────┬────────────────────────────┘
                            │ (Local Parsing & Schema Discovery)
                            ▼
┌────────────────────────────────────────────────────────┐
│         datasets/tsbc_maritime/pipeline.py              │
│  - Deterministic 9-factor ranking                      │
│  - Deduplication (equipment & occurrences)             │
│  - Canonical normalization                             │
│  - Strict API Safety Limits (max_records=1 by default) │
└─────────────┬──────────────────────────┬───────────────┘
              │ (Zero API calls)         │ (--dry-run)
              ▼                          ▼
┌───────────────────────────┐  ┌─────────────────────────┐
│ tsbc_maritime_test_1.jsonl│  │ Dry-Run Preflight Report │
│ (Occurrence ID: 4)        │  │ 0 external API calls     │
└─────────────┬─────────────┘  └─────────────────────────┘
              │ (--index)
              ▼
┌────────────────────────────────────────────────────────┐
│       Hyper-RAG Isolated Knowledge Base                │
│  Directory: caches/tsbc_maritime_test/                 │
│  Junction:  hyperrag_cache/tsbc_maritime_test          │
│  Embedding: mistral-embed (1024-dim, https://api.mistral.ai/v1)
│  LLM:       nvidia/nemotron-3-ultra-550b-a55b:free     │
└─────────────┬──────────────────────────────────────────┘
              │
              ▼
┌────────────────────────────────────────────────────────┐
│       Hyper-RAG Web Console & FastAPI Server           │
│  Backend:  web-ui/backend/main.py (Port 8000)          │
│  Frontend: React + Vite Single-Page App                │
│  Database: Selected via header 'tsbc_maritime_test'    │
└────────────────────────────────────────────────────────┘
```

---

## 2. Source Corpus Audit & Discovered Schema

- **Corpus Location**: `external_data/maritime_corpus.jsonl`
- **Total Lines**: 68,355 (100% valid JSON, 0 malformed records)
- **Unique Occurrences**: 44,329
- **Perspectives**:
  - `occurrence_summary` (40,510 records)
  - `vessel_consolidated_narrative` (27,845 records)

### Actual Schema Discovered

Each line contains:
1. `occurrence_id` (integer)
2. `document` (text narrative)
3. `provenance` (`perspective`, `pattern_id`, `spans`)
4. `structured`:
   - `occurrence`: `OccID`, `OccNo`, `OccClassDisplayEng`, `OccDate`, `OccTime`, `OccTypeDisplayEng`, `AccIncTypeDisplayEng`, `Summary`, `SearchAndRescueIND_DisplayEng`, `DamageIND_DisplayEng`, `NearestLocationDescription`, `Latitude`, `Longitude`, `WeatherConditionDisplayEng`, `SeaStateDisplayEng`, `TotalDeaths`, `TotalSeriousInjuries`, `TotalMinorInjuries`, `TotalMissingIndividuals`.
   - `vessels` (list): `VesselName`, `OfficialNo`, `VesselTypeDisplayEng`, `VesselSubTypeDisplayEng`, `VesselFlagDisplayEng`, `PortOfRegistryDisplayEng`, `GrossTonnage`, `PropulsionTypeDisplayEng`, `HullMaterialDisplayEng`, `DeparturePortDisplayEng`, `DestinationPortDisplayEng`, `VesselDamageLocationDisplayEng`, `VesselDamageDegreeDisplayEng`, `navigation_equipment` (list), `lsa_equipment` (list).

---

## 3. Deterministic 1-Record Selection Rationale

Selection was performed using a deterministic 9-factor scoring function:
1. Occurrence metadata completeness
2. Vessel details completeness
3. Geographic coordinates and description
4. Environmental & weather conditions (clear, calm glassy sea)
5. Damage specifications (major damage, engine room)
6. Search and rescue (SAR) operations deployed
7. Life-saving equipment (lifeboats)
8. Navigation equipment (magnetic compass)
9. Multiple perspective narratives available in corpus

**Selected Occurrence**: **Occurrence ID 4**
- **Vessel Involved**: `ANVOURGON` (Official No: 4305, Flag: GREECE, Registry: Piraeus, 7,266 GT)
- **Incident**: Explosion and engine room fire on 1975-01-08 at 19:00 UTC in the Laurentian Region (near Rivière-au-Renard).
- **Casualties**: 0 fatalities, 0 serious injuries, 0 missing individuals (all crew rescued by SAR).
- **Damage**: Major damage to Hull / Engineering Spaces (Engine Room); vessel towed to Halifax.
- **Unavailable / Unknown Fields**: Vessel builder name, MMSI, IMO number (used for negative / anti-hallucination tests).

---

## 4. Normalization & Deduplication

Implemented in [pipeline.py](../datasets/tsbc_maritime/pipeline.py):
- **Equipment Deduplication**: Removes duplicate equipment entries (e.g., redundant Lifeboat and Magnetic Compass records) based on composite key tuples.
- **Provenance Preservation**: Retains source file path, occurrence ID, vessel name, and original perspective identifiers.
- **Context Generation**: Produces 5 clean, factual perspectives:
  1. `occurrence_overview`
  2. `vessel_profile`
  3. `environmental_conditions`
  4. `damage_and_safety`
  5. `equipment_profile`

---

## 5. API Safety Guards & Dry-Run Mode

To prevent accidental full-corpus ingestion or excessive quota usage:
- **Default Record Limit**: `max_records = 1`
- **Default Context Limit**: `max_contexts = 5`
- **Default Concurrency**: `1`
- **Embedding Dimensions**: `1024` (Mistral embeddings)

### Running Dry-Run Estimation
```powershell
python -m datasets.tsbc_maritime.pipeline --dataset tsbc_maritime_test_1 --dry-run
```
*Zero external API calls are made. Generates a preflight estimate in `datasets/tsbc_maritime/reports/`.*

---

## 6. Isolated Indexing

To index the 1-record dataset into `caches/tsbc_maritime_test`:
```powershell
python -m datasets.tsbc_maritime.pipeline --dataset tsbc_maritime_test_1 --index
```
This builds:
- `caches/tsbc_maritime_test/hypergraph_chunk_entity_relation.hgdb` (22 vertices, 3 hyperedges)
- `caches/tsbc_maritime_test/vdb_chunks.json`
- `caches/tsbc_maritime_test/vdb_entities.json`
- `caches/tsbc_maritime_test/vdb_relationships.json`
- Automatically links to `hyperrag_cache/tsbc_maritime_test` for WebUI discovery.

---

## 7. WebUI Startup & Usage

### 1. Start FastAPI Backend:
```powershell
python -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Access Web Console:
Open your browser to:
```
http://127.0.0.1:8000/#/Hyper/chat
```

### 3. Switch Knowledge Base:
In the top header database selector dropdown, choose **`tsbc_maritime_test`**.

### 4. Verified Test Queries:
1. **Direct Retrieval**:
   - *Query*: "What vessel was involved in maritime occurrence 4?"
   - *Answer*: Confirms **ANVOURGON** (Greek cargo vessel, 7,266 GT).
2. **Damage & Casualties**:
   - *Query*: "What damage was reported for maritime occurrence 4 and were there any casualties?"
   - *Answer*: Confirms major damage to engine room; confirms **0 fatalities, 0 injuries**.
3. **Unknown / Negative (Anti-Hallucination)**:
   - *Query*: "Who was the builder of the vessel ANVOURGON?"
   - *Answer*: Confirms that builder information is **not available / not recorded** in TSBC records.

---

## 8. Automated Testing

Run the full local unit test suite (offline, 0 API calls):
```powershell
pytest tests/test_tsbc_maritime.py -v
```

Run end-to-end browser verification via Playwright:
```powershell
python scratch/verify_tsbc_browser.py
```

---

## 9. Next Safe Step: Controlled 3-Record Expansion

The 3-record raw dataset (`tsbc_maritime_test_3.jsonl`) has already been extracted and dry-run validated in `datasets/tsbc_maritime/raw_reference/`:
- **Occurrence 4**: `ANVOURGON`
- **Occurrence 48**: `SIDNEY W.`
- **Occurrence 205**: `LASSIE III`

To index the 3-record dataset safely when quota permits:
```powershell
python -m datasets.tsbc_maritime.pipeline --dataset tsbc_maritime_test_3 --max-records 3 --max-contexts 15 --index
```
