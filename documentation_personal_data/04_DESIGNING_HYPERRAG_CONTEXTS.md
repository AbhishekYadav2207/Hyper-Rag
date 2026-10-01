# Document 04: Designing Hyper-RAG Contexts

This guide explains how to transform normalized tabular, relational, or document data into high-signal **context perspectives** optimized for Hyper-RAG's dual hypergraph and vector indexing engines.

---

## 1. Why Blindly Dumping Raw Records Fails

A common anti-pattern in RAG ingestion is converting an entire database row into a single giant text paragraph or JSON string:

```text
[ANTI-PATTERN: Monolithic Text Dump]
"Occurrence 4 happened on 1975-01-08 at 19:00 UTC in LAURENTIAN REGION. Nearest location: ST LAWRENCE-GULF OF-RIVIERE AU RENARD. Weather: CLEAR. Sea: CALM. Vessel: ANVOURGON. OfficialNo: 4305. GrossTonnage: 7266. Flag: GREECE. Port: Piraeus. Damage: MAJOR in Engine Room. Deaths: 0. Injuries: 0. Missing: 0. Lifeboat: No. Compass: On. Narrative: CREW RESCUED VESSEL TOWED TO HALIFAX AFTER FIRE IN ENGINE ROOM..."
```

### Why This Hurts Hyper-RAG Retrieval:
1. **Embedding Dilution**: A dense paragraph containing weather, engine mechanics, ship flags, and casualty numbers yields an "average" embedding vector. When a user asks "What was the weather?", the vector distance is diluted by ship tonnage and casualty data.
2. **Chunk Boundary Splitting**: If a monolithic row exceeds the chunk character limit (typically 1000-1200 characters), Hyper-RAG's chunker splits the text mid-sentence, stranding vessel metadata in chunk 1 and damage details in chunk 2.
3. **Loss of Hypergraph Structure**: Hyper-RAG builds hyperedges connecting multi-entity sets. Slicing dense records into thematic perspectives allows the system to construct clean hyperedges corresponding to real relational groupings (e.g. Environmental Conditions vs. Engineering Damage).

---

## 2. The Context Perspective Architecture

Instead of one monolithic text chunk, decompose each primary record into **3 to 6 semantic perspectives**:

```text
┌────────────────────────────────────────────────────────┐
│               CANONICAL SOURCE RECORD                  │
│               Occurrence ID: 4 (ANVOURGON)             │
└───────────────┬────────────┬─────────────┬─────────────┘
                │            │             │
        ┌───────┴──────┐ ┌───┴────────┐ ┌──┴───────────────┐
        ▼              ▼ ▼            ▼ ▼                  ▼
┌──────────────┐┌──────────────┐┌──────────────┐┌────────────────┐
│ Context 1:   ││ Context 2:   ││ Context 3:   ││ Context 4:     │
│ Occurrence   ││ Vessel       ││ Environment  ││ Damage & Safety│
│ Overview     ││ Profile      ││ Conditions   ││ Details        │
└──────────────┘└──────────────┘└──────────────┘└────────────────┘
```

Each perspective is a self-contained factual paragraph (100–300 words) that includes:
1. **The Primary Entity Anchor**: (e.g. *"Maritime Occurrence 4 involving vessel ANVOURGON..."*) ensuring all perspectives link to the same entity vertices.
2. **Cohesive Semantic Grouping**: Information naturally asked together (e.g. wave height + sea state + wind speed).
3. **Explicit Handling of Absent Fields**: Statements of unrecorded values to prevent hallucinated answers.

---

## 3. The TSBC Implementation Case Study

In our maritime pipeline ([datasets/tsbc_maritime/pipeline.py](file:///d:/Rag/Hyper-RAG/datasets/tsbc_maritime/pipeline.py)), we decomposed Occurrence 4 into 5 distinct perspectives:

### Perspective 1: `occurrence_overview`
> "Maritime Occurrence ID 4 (Occurrence Number 4) was an official Fact-Finding investigation into an Accident involving an EXPLOSION. The incident occurred on 1975-01-08 at 19:00:00 UTC in the Laurentian Region. Nearest geographic location: ST LAWRENCE-GULF OF-RIVIERE AU RENARD-PRET DE at coordinates 49.0° N, 64.1667° W. Primary vessel involved: ANVOURGON. Summary: CREW RESCUED VESSEL TOWED TO HALIFAX AFTER FIRE IN ENGINE ROOM."

### Perspective 2: `vessel_profile`
> "Vessel Profile for ANVOURGON (Official No: 4305), involved in Occurrence 4: The vessel is a General Cargo (Cargo - Solid) ship flying the flag of GREECE, with Port of Registry at Piraeus. Gross tonnage is 7266.0 GT. Propulsion type: PROPELLER with a STEEL hull. Voyage departed from QUEBEC, CANADA destined for QUEBEC, CANADA. Vessel builder information is not recorded in TSBC records."

### Perspective 3: `environmental_conditions`
> "Environmental and meteorological conditions for Maritime Occurrence 4 (ANVOURGON): Weather condition was reported as CLEAR. Sea state was recorded as CALM (GLASSY) - 0 meters. Wind direction code was 3.0. Light conditions and atmospheric visibility supported maritime navigation at the time of the occurrence."

### Perspective 4: `damage_and_safety`
> "Damage and Casualty assessment for Occurrence 4 (Vessel: ANVOURGON): Damage indicator was confirmed as 'Yes'. Vessel suffered MAJOR damage categorized under Hull and Engineering Spaces, specifically located in the Engine room. Search and Rescue (SAR) operations were deployed: 'Yes'. Casualty statistics: Total Deaths: 0, Total Serious Injuries: 0, Total Minor Injuries: 0, Total Missing Individuals: 0. Crew was successfully rescued and vessel was towed to Halifax."

### Perspective 5: `equipment_profile`
> "Equipment profile for ANVOURGON in Maritime Occurrence 4: Navigation equipment: Magnetic compass was installed and operating (Status: On). Life-saving appliances (LSA): Lifeboats were carried onboard (Used: No). Equipment records reflect operational status during the occurrence."

---

## 4. Designing Perspectives Across Other Domains

Do NOT copy the TSBC maritime perspectives for unrelated data. Derive perspectives matching the natural queries of your domain:

### Financial & Corporate Filings
- **Filing Overview**: Ticker, company name, fiscal period, filing date, CIK, auditor.
- **Income & Revenue Performance**: Revenue, operating margin, EPS, segment performance, EBITDA.
- **Balance Sheet & Liquidity**: Debt obligations, cash runway, current ratio, capital expenditures.
- **Risk Factors & Legal Disclosures**: Pending litigation, regulatory vulnerabilities, supply chain risks.

### Healthcare & Clinical Records
- **Patient Administrative Profile**: De-identified ID, age group, admission date, discharge status, attending unit.
- **Clinical History & Presentation**: Chief complaint, past medical history, onset chronology.
- **Diagnostic Findings & Labs**: Vital signs, pathology reports, imaging results, blood chemistry values.
- **Treatment Plan & Pharmacology**: Medications administered, dosage, surgical procedures, contraindications.

### Legal Case Documents
- **Case Header & Procedural History**: Court, docket number, parties (plaintiff/defendant), judgment date, judges.
- **Claims & Statutory Questions**: Causes of action, relevant statutory provisions, claims asserted.
- **Court Analysis & Findings of Fact**: Material evidence considered, credibility findings, jurisdictional ruling.
- **Disposition & Orders**: Final judgment, damages awarded, injunctive relief, dissenting opinions.

### Customer Support & Enterprise IT Tickets
- **Ticket Header & SLA Metrics**: Ticket ID, client name, tier, priority, creation timestamp, resolution time.
- **Problem Narrative**: User complaint, error codes, affected systems, reproduction steps.
- **Diagnostic Telemetry**: Server logs, stack trace, affected cluster/region, network latency.
- **Resolution & Root Cause**: Action taken by engineer, patch version applied, root cause category.

---

## 5. Optimal Granularity & Entity Linking Rules

To ensure Hyper-RAG's hypergraph engine extracts rich relationships:

1. **Word Count Window**: Aim for **150 to 350 words** per perspective. Chunks under 50 words lack context; chunks over 600 words risk fragmentation.
2. **Anchor Entity Rule**: Always repeat the primary entity name or ID in the first sentence of *every* perspective (e.g. *"In quarterly filing Q3-2025 for Acme Corp..."*). This guarantees that Hyper-RAG connects all perspectives to the same central entity vertex in `hypergraph_chunk_entity_relation.hgdb`.
3. **Structured Prose over Raw JSON**: Write natural English sentences rather than JSON strings:
   - *Good*: "Total casualties: 0 deaths and 0 injuries."
   - *Poor*: `"TotalDeaths": 0, "TotalInjuries": 0`
   Natural prose significantly improves cosine similarity with human search queries.
4. **Explicit Negative Grounding**: When a field is missing, state it explicitly: *"IMO number is not available in source data."* This arms the LLM with direct factual evidence of absence when responding to negative queries.
