# Template: Dataset Field-to-Context Mapping

Use this template to design the transformation from raw source fields to canonical normalized dictionaries, Hyper-RAG context perspectives, extracted entities, and hypergraph relations.

---

## 1. Field-Level Transformation Matrix

| Raw Source Field | Normalized Canonical Field | Target Context Perspective | Extracted Entity Vertex? | Hyperedge / Relationship Role |
|---|---|---|---|---|
| `OccID` | `occurrence_id` | All Contexts (Anchor) | Yes (Occurrence: 4) | Central occurrence anchor |
| `OccDate` | `occurrence_date` | `occurrence_overview` | No | Chronological attribute |
| `AccIncTypeDisplayEng` | `incident_type` | `occurrence_overview` | Yes (Event: EXPLOSION) | Primary event node |
| `NearestLocationDescription` | `nearest_location` | `occurrence_overview` | Yes (Location: Rivière-au-Renard) | Geographic vertex |
| `VesselName` | `vessel_name` | `vessel_profile` | Yes (Vessel: ANVOURGON) | Primary subject vertex |
| `VesselFlagDisplayEng` | `flag` | `vessel_profile` | Yes (Country: GREECE) | Registry link |
| `GrossTonnage` | `gross_tonnage` | `vessel_profile` | No | Numeric vessel spec |
| `WeatherConditionDisplayEng` | `weather_condition` | `environmental_conditions` | No | Environmental attribute |
| `SeaStateDisplayEng` | `sea_state` | `environmental_conditions` | No | Environmental attribute |
| `VesselDamageDegreeDisplayEng` | `damage_degree` | `damage_and_safety` | Yes (Damage: MAJOR) | Incident outcome |
| `TotalDeaths` | `total_deaths` | `damage_and_safety` | No | Casualty statistic (0) |
| `LsApplianceDisplayEng` | `equipment.appliance` | `equipment_profile` | Yes (Equipment: Lifeboat) | Safety asset vertex |

---

## 2. Context Perspective Specifications

Define the target perspectives for your domain:

### Perspective 1: `[perspective_name_1]`
- **Semantic Purpose**: `[e.g. Incident Overview & Location]`
- **Anchor Sentence**: `"Occurrence [ID] involving [Entity] occurred on [Date] in [Location]..."`
- **Fields Included**: `[Field A, Field B, Field C]`
- **Target Word Count**: `[150 to 250 words]`

### Perspective 2: `[perspective_name_2]`
- **Semantic Purpose**: `[e.g. Primary Subject Profile]`
- **Anchor Sentence**: `"Subject Profile for [Entity] in Occurrence [ID]..."`
- **Fields Included**: `[Field D, Field E, Field F]`
- **Target Word Count**: `[150 to 250 words]`

### Perspective 3: `[perspective_name_3]`
- **Semantic Purpose**: `[e.g. Environmental / Telemetry Data]`
- **Anchor Sentence**: `"Telemetry and environment recorded for Occurrence [ID]..."`
- **Fields Included**: `[Field G, Field H, Field I]`
- **Target Word Count**: `[100 to 200 words]`

### Perspective 4: `[perspective_name_4]`
- **Semantic Purpose**: `[e.g. Outcome & Safety Assessment]`
- **Anchor Sentence**: `"Outcomes and damage reported for Occurrence [ID]..."`
- **Fields Included**: `[Field J, Field K, Field L]`
- **Target Word Count**: `[150 to 250 words]`

---

## 3. Negative Grounding Policy (Absent Fields)

List attributes that are known to be null or unrecorded in the source dataset, and define the explicit phrasing to use in context paragraphs:

| Field Name | Expected Frequency | Explicit Prose Statement |
|---|---|---|
| `[builder]` | < 2% present | *"Vessel builder information is not recorded in source records."* |
| `[imo_number]` | < 5% present | *"IMO number is not available in source data."* |
| `[secondary_contact]`| < 10% present | *"Secondary contact details were not provided."* |
