<!-- <div align="center" id="top"> 
  <img src="./assets/hg.svg" alt="Hypergraph" width="100%" />
</div> -->

<h1 align="center">Hyper-RAG</h1>

<p align="center">
  <img alt="Github top language" src="https://img.shields.io/github/languages/top/iMoonLab/Hyper-RAG?color=purple">

  <img alt="Github language count" src="https://img.shields.io/github/languages/count/iMoonLab/Hyper-RAG?color=purple">

  <img alt="Repository size" src="https://img.shields.io/github/repo-size/iMoonLab/Hyper-RAG?color=purple">

  <img alt="License" src="https://img.shields.io/github/license/iMoonLab/Hyper-RAG?color=purple">
  <a href="https://www.nature.com/articles/s41467-026-71411-1"><img alt="Nature Communications" src="https://img.shields.io/badge/Nature%20Communications-2026-E63946?logo=nature&logoColor=white"></a>
  <a href="https://doi.org/10.1038/s41467-026-71411-1"><img alt="DOI" src="https://img.shields.io/badge/DOI-10.1038%2Fs41467--026--71411--1-1F6FEB"></a>
</p>

<p align="center">
  <a href="#dart-about">About</a> &#xa0; | &#xa0; 
  <a href="#sparkles-why-hyper-rag-is-more-powerful">Features</a> &#xa0; | &#xa0;
  <a href="#rocket-installation">Installation</a> &#xa0; | &#xa0;
  <a href="#white_check_mark-quick-start">Quick Start</a> &#xa0; | &#xa0;
  <a href="#whale-docker-deployment">Docker</a> &#xa0; | &#xa0;
  <a href="#checkered_flag-evaluation">Evaluation</a> &#xa0; | &#xa0;
  <a href="#memo-license">License</a> &#xa0; | &#xa0;
  <a href="https://github.com/yifanfeng97" target="_blank">Author</a>
</p>

<br>


<div align="center">
  <img src="./assets/many_llms_all.svg" alt="Overall Performance" width="100%" />
</div>

We show that Hyper-RAG is a powerful RAG that can enhance the performance of various LLMs and outperform other SOTA RAG methods in the NeurologyCorp dataset. **Our paper has been published in <a href="https://www.nature.com/articles/s41467-026-71411-1"><i>Nature Communications</i></a> (2026)**.

## :dart: About

<details>
<summary> <b>Abstract</b> </summary>
Large language models (LLMs) have transformed various sectors, including education, finance, and medicine, by enhancing content generation and decision-making processes. However, their integration into the medical field is cautious due to hallucinations, instances where generated content deviates from factual accuracy, potentially leading to adverse outcomes. To address this, we introduce Hyper-RAG, a hypergraph-driven Retrieval-Augmented Generation method that comprehensively captures both pairwise and beyond-pairwise correlations in domain-specific knowledge, thereby mitigating hallucinations. Experiments on the NeurologyCrop dataset with six prominent LLMs demonstrated that Hyper-RAG improves accuracy by an average of 12.3% over direct LLM use and outperforms Graph RAG and Light RAG by 6.3% and 6.0%, respectively. Additionally, Hyper-RAG maintained stable performance with increasing query complexity, unlike existing methods which declined. Further validation across nine diverse datasets showed a 35.5% performance improvement over Light RAG using a selection-based assessment. The lightweight variant, Hyper-RAG-Lite, achieved twice the retrieval speed and a 3.3\% performance boost compared with Light RAG. These results confirm Hyper-RAG's effectiveness in enhancing LLM reliability and reducing hallucinations, making it a robust solution for high-stakes applications like medical diagnostics.
</details>

<br>

<div align="center">
  <img src="./assets/fw.svg" alt="Framework" width="100%" />
</div>
Schematic diagram of the proposed Hyper-RAG architecture. a, The patient poses a question. b, A knowledge base is constructed from relevant domainspecific corpora. c, Responses are generated directly using LLMs. d, Hyper-RAG generates responses by first retrieving relevant prior knowledge from the knowledge base and then inputting this knowledge, along with the patient’s question, into the LLMs to formulate the reply.

<br>
<br>

<details>
<summary> <b>More details about hypergraph modeling</b> </summary>
<div align="center"> 
  <img src="./assets/hg.svg" alt="Hypergraph" width="100%" />
Example of hypergraph modeling for entity space. Hypergraph can model the beyond-pairwise relationship among entities, which is more powerful than the pairwise relationship in traditional graph modeling. With hypergraphs, we can avoid the information loss caused by the pairwise relationship.
</div>
<br>
<div align="center"> 
  <img src="./assets/extract.svg" alt="Extract Hypergraph" width="100%" />
  Illustration of Entity and Correlation Extraction from Raw Corpus: Dark brown boxes represent entities, blue arrows denote low-order correlations between entities, and red arrows indicate high-order correlations. Yellow boxes contain the original descriptions of the respective entities or their correlations.
</div>
</details>

<br>

## :sparkles: Why Hyper-RAG is More Powerful

:heavy_check_mark: **Comprehensive Relationship Modeling with Hypergraphs**: Utilizes hypergraphs to thoroughly model the associations within the raw corpus data, providing more complex relationships compared to traditional graph-based data organization.;\
:heavy_check_mark: **Native Hypergraph-DB Integration**: Employs the native hypergraph database, <a href="https://github.com/iMoonLab/Hypergraph-DB">Hypergraph-DB</a>, as the foundation, supporting rapid retrieval of higher-order associations.;\
:heavy_check_mark: **Superior Performance**: Hyper-RAG outperforms Graph RAG and Light RAG by 6.3% and 6.0% respectively.;\
:heavy_check_mark: **Broad Validation**: Across nine diverse datasets, Hyper-RAG shows a 35.5% performance improvement over Light RAG based on a selection-based assessment.;\
:heavy_check_mark: **Efficiency**: The lightweight variant, Hyper-RAG-Lite, achieves twice the retrieval speed and a 3.3% performance boost compared to Light RAG.;

## :rocket: Installation


```bash
# Clone this project
git clone https://github.com/iMoonLab/Hyper-RAG.git

# Access
cd Hyper-RAG

# Install dependencies
pip install -r requirements.txt
```

## :white_check_mark: Quick Start

### Configure your LLM API
Copy the `config_temp.py` file to `my_config.py` in the root folder and set your LLM `URL` and `KEY`.

```python
# OPENROUTER - ONLY LLM PROVIDER
OPENROUTER_API_KEYS = "your_openrouter_api_key"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

# MISTRAL - EMBEDDINGS ONLY
EMB_API_KEYS = "your_mistral_api_key"
EMB_BASE_URL = "https://api.mistral.ai/v1"
EMB_MODEL = "mistral-embed"
EMB_DIM = 1024
```

### Run the toy example

```bash
python examples/hyperrag_demo.py
```

### Or Run by Steps

1. Prepare the data. You can download the dataset from Google Drive <a href="https://drive.google.com/drive/folders/1JxXXUR4Jx-2IKn4VGpDeH4xb4-nYEWBx?usp=sharing">here</a>, or Baidu Cloud <a href="https://pan.baidu.com/s/1mrDJVpMW59gLtRRSXafXdw?pwd=w642">here</a>. Put the dataset in the root direction. Then run the following command to preprocess the data.

```bash
python reproduce/Step_0.py
```

2. Build the knowledge hypergraphs, and entity and relation vector database with following command.

```bash
python reproduce/Step_1.py
```

3. Extract questions from the orignial datasets with following command.

```bash
python reproduce/Step_2_extract_question.py
```

Those questions are saved in the `cache/{{data_name}}/questions` folder. 

4. Run the Hyper-RAG to response those questions with following command.

```bash
python reproduce/Step_3_response_question.py
```

Those response are saved in the `cache/{{data_name}}/response` folder.

You can also change the `mode` parameter to `hyper` or `hyper-lite` to run the Hyper-RAG or Hyper-RAG-Lite.


### Hypergraph Visualization
We provide a web-based visualization tool for hypergraphs and lightweight Hyper-RAG QA system. For more information, please refer to [Hyper-RAG Web-UI](./web-ui/README.md).

*Note: We welcome any contributions to improve it.*
![vis-qa](./assets/vis-QA.png)
![vis-hg](./assets/vis-hg.png)

## 📁 Repository Structure

```text
Hyper-RAG/
├── hyperrag/                     # Core Hyper-RAG library implementation
│   ├── adaptive_router.py        # Phase 1: Query complexity analyzer & router
│   ├── retrieval_sufficiency.py  # Phase 2: Post-retrieval sufficiency evaluator
│   ├── key_pool.py               # API key rotation, cooldown, and backoff engine
│   ├── llm.py                    # LLM (OpenRouter) & embedding (Mistral) client calls
│   └── hyperrag.py               # HyperRAG orchestrator & escalation pipeline
├── datasets/                     # Domain-specific evaluation datasets (local)
├── docs/                         # Technical documentation & architecture guides
├── evaluate/                     # Scoring-based and selection-based assessment utilities
├── examples/                     # Standalone usage demos and mock data
├── reproduce/                    # Step-by-step benchmark and reproduction scripts
├── web-ui/                       # Full-stack Web Console (React frontend + FastAPI backend)
├── assets/                       # Architecture diagrams and benchmark figures
├── test_adaptive_router.py       # Unit tests for Phase 1 & Phase 2.1 query routing
├── test_retrieval_sufficiency.py # Unit tests for Phase 2 sufficiency evaluation
├── test_key_rotation.py          # Unit tests for multi-key pool rotation & backoff
├── test_config.py                # Unit tests for configuration validation
├── service_api.py                # FastAPI REST and streaming server
├── testHTML_light.html           # Lightweight browser console for service_api
├── pilot_benchmark.py            # Pilot benchmark with matrix-backed embedding lookup
├── run_full_benchmark.py         # Comprehensive 39-query evaluation benchmark suite
├── benchmark_results.json        # Validated 39-query benchmark results
├── threshold_analysis.json       # Validated threshold sensitivity analysis (40, 50, 60, 70)
├── config_temp.py                # Configuration template for local setup
├── .env.example                  # Environment variable deployment template
└── requirements.txt              # Python package dependencies
```

> **Maintenance Note**: Generated caches (`caches/`), local datasets (`datasets/`), secrets (`.env`, `my_config.py`), temporary benchmark artifacts, and local test outputs are excluded from version control.

## :whale: Docker Deployment

We provide Docker support for easy deployment of the Hyper-RAG Web UI. Docker deployment includes both frontend and backend services with optional Nginx reverse proxy.

### Quick Start with Docker

1. **Prerequisites**: Ensure Docker and Docker Compose are installed on your system.

2. **Navigate to web-ui directory**:
```bash
cd web-ui
```

3. **Start with Docker Compose**:
```bash
docker-compose up 
```

4. **Access the application**:
   - Application at http://localhost:5000

### Detailed Documentation

For comprehensive Docker deployment instructions, configuration options, troubleshooting, and production deployment guidelines, please refer to our detailed [Docker Deployment Guide](./web-ui/DOCKER.md).

## :bulb: Simple Test Demo

1. Run by steps
```bash
conda activate rag
cd Hyper_RAG/reproduce
python reproduce/Step_0.py
python reproduce/Step_1.py

cd Hyper-RAG
python -m uvicorn service_api:app --app-dir . --host 0.0.0.0 --port 8000
```
2. Open `testHTML_light.html` in your web browser.
3. Selecting the model (`hyper`,`hyper-lite`,`naive`) and whether to output in streaming mode

<div align="center">
  <img src="./assets/hyperrag-streaming.gif" alt="Efficiency analysis" width="80%" />
</div>

## :checkered_flag: Evaluation
In this work, we propose two evaluation strategys: the **selection-based** and **scoring-based** evaluation. 

### Scoring-based evaluation
Scoring-Based Assessment is designed to facilitate the comparative evaluation of multiple model outputs by quantifying their performance across various dimensions. This approach allows for a nuanced assessment of model capabilities by providing scores on several key metrics. However, a notable limitation is its reliance on reference answers. In our preprocessing steps, we leverage the source chunks from which each question is derived as reference answers.

You can use the following command to use this evaluation method.

```bash
python evaluate/evaluate_by_scoring.py
```
The results of this evaluation are shown in the following figure.
<div align="center">
  <img src="./assets/many_llms_sp.svg" alt="Scoring-based evaluation" width="90%" />
</div>


### Selection-based evaluation
Selection-Based Assessment is tailored for scenarios where preliminary candidate models are available, enabling a comparative evaluation through a binary choice mechanism. This method does not require reference answers, making it suitable for diverse and open-ended questions. However, its limitation lies in its comparative nature, as it only allows for the evaluation of two models at a time.

You can use the following command to use this evaluation method.

```bash
python evaluate/evaluate_by_selection.py
```
The results of this evaluation are shown in the following figure.
<div align="center">
  <img src="./assets/multi_domain.svg" alt="Selection-based evaluation" width="90%" />
</div>


### Efficiency Analysis
We conducted an efficiency analysis of our Hyper-RAG method using GPT-4o mini on the NeurologyCrop dataset, comparing it with standard RAG, Graph RAG, and Light RAG. To ensure fairness by excluding network latency, we measured only the local retrieval time for relevant knowledge and the construction of the prior knowledge prompt. While standard RAG focuses on the direct retrieval of chunk embeddings, Graph RAG, Light RAG, and Hyper-RAG also include retrieval from node and correlation vector databases and the time for one layer of graph or hypergraph information diffusion. We averaged the response times over 50 questions from the dataset for each method. The results are shown in the following figure.

<div align="center">
  <img src="./assets/speed_all.svg" alt="Efficiency analysis" width="60%" />
</div>

## 🔀 Adaptive Hyper-RAG

Adaptive Hyper-RAG is a multi-phase system designed to balance execution cost, latency, and retrieval quality by dynamically selecting between **Hyper-Lite** (lightweight entity-focused retrieval) and **Hyper-Core** (high-order hypergraph structure and reasoning).

```text
User Query
    ↓
[Phase 1] Adaptive Query Router (Deterministic Complexity Scoring)
    ↓
Initial Mode Decision: Hyper-Lite OR Hyper-Core
    ├── If Hyper-Core:
    │      ↓
    │   Hyper-Core Retrieval → High-Order Reasoning → Answer
    │
    └── If Hyper-Lite:
           ↓
        Hyper-Lite Retrieval (Keywords & Entities)
           ↓
        [Phase 2] Retrieval Sufficiency Evaluator (Deterministic & Local)
           ↓
        Sufficient Evidence?
            ├── YES (Score >= Threshold):
            │      ↓
            │   Hyper-Lite Reasoning → Answer (Remains Lite)
            │
            └── NO (Score < Threshold / Weak Evidence):
                   ↓
                [Escalation] Escalate to Hyper-Core Retrieval & Reasoning → Answer
```

---

### Phase 1: Deterministic Query Complexity Routing

#### What Phase 1 is
The Phase 1 router makes a pre-retrieval decision based entirely on query complexity. It evaluates query characteristics to select an initial execution mode (`lite` or `core`) without any LLM calls.

#### Why it was added
- **Query Diversity**: Simple single-entity factual queries often require only low-level entity context (Hyper-Lite), whereas multi-entity, comparative, or multi-hop queries benefit from high-order relationship hyperedges (Hyper-Core).
- **Zero API Overhead**: Strictly deterministic and rule-driven—it makes **no LLM calls** for routing, avoiding extra latency, API usage, or token costs.

#### Features Considered in Phase 1
The router evaluates 12 interpretable signals across 8 feature categories:
1. **Multi-Aspect Questions**: Conjunctions (`and`, `as well as`, `including`), clause enumerations, and comma-separated lists.
2. **Comparison**: Explicit comparative indicators (`compare`, `versus`, `difference`, `between X and Y`).
3. **Causal / Explanatory Reasoning**: Triggers requiring relational reasoning (`why`, `how does`, `causes`, `effect`, `mechanism`, `leads to`, `contribute to`).
4. **Temporal Reasoning**: Chronological references (`over time`, `timeline`, `historically`, `evolution`, year ranges).
5. **Multi-Hop Reasoning**: Connection pathways (`relationship between`, `how A affects B through C`, `associated with`).
6. **Aggregation / Synthesis**: Synthesis demands (`summarize all`, `list all`, `across multiple sources`).
7. **Entity Count**: Lightweight topic/entity extraction detecting quoted terms, proper nouns, and content noun chunks without heavyweight NER dependencies.
8. **Requested Depth**: Explicit depth markers (`detailed`, `in-depth`, `exhaustive`, `step by step`).
9. **Structural Complexity**: Word length, sentence count, and question marks.

#### Phase 1 Scoring & Thresholds
Each detected feature contributes points to a transparent $0$ to $100$ score:
- **Low Complexity ($0 - 30$)**: Simple factual/definitional queries $\rightarrow$ routes to **Hyper-Lite**.
- **Medium Complexity ($31 - 60$)**: Moderate queries within Lite capacity $\rightarrow$ routes to **Hyper-Lite** (under default threshold $60$).
- **High Complexity ($61 - 100$)**: Multi-hop, multi-entity, or comparative queries $\rightarrow$ routes to **Hyper-Core**.

Default threshold:
```python
ADAPTIVE_CORE_THRESHOLD = 60  # Score >= 60 executes Hyper-Core; < 60 executes Hyper-Lite
```

---

### Phase 2: Retrieval Sufficiency & Automatic Lite → Core Escalation

#### What Phase 2 is
While Phase 1 inspects the query *before* retrieval, Phase 2 inspects the actual retrieval artifacts *after* Lite retrieval has run, but *before* generating an LLM response. If Lite retrieval produces empty, duplicate, or insufficient relational evidence for the query's complexity, the system automatically escalates execution to **Hyper-Core**.

#### Why Phase 2 was added
A query may appear deceptively simple syntactically (e.g. `Score = 35`), but Lite retrieval might only return disconnected fragments, empty results, or lack relationship paths needed to answer the question. Rather than returning an under-informed answer, Phase 2 evaluates retrieval sufficiency and escalates to Core when needed.

#### Retrieval Signals Used in Phase 2
The `RetrievalSufficiencyEvaluator` evaluates concrete signals extracted from Lite retrieval:
1. **Item Volume**: Number of retrieved knowledge entities and context items.
2. **Unique Entities**: Diversity of distinct entities retrieved.
3. **Context Length**: Total character length of retrieved context chunks.
4. **Query Entity Coverage**: Lexical and token overlap between query key phrases and retrieved context.
5. **Duplicate / Redundancy Penalty**: Detection of low-diversity, repetitive context fragments.
6. **Multi-Hop & Relational Evidence**: For queries requiring causal or multi-hop reasoning, checks whether relational hyperedges or connecting relationships exist. If absent, a significant relational penalty is applied.

#### Transparent Deterministic Formula
The sufficiency score ($0 - 100$) is computed locally without LLM calls:
```text
Score = (Volume_Score * 0.25)
      + (Unique_Entities_Score * 0.20)
      + (Context_Length_Score * 0.25)
      + (Query_Coverage_Score * 0.30)
      - Missing_Relationship_Penalty (25 pts if multi-hop query lacks hyperedges)
```

#### Escalation Policy
- **Core Stays Core**: If Phase 1 selected Core (or mode was forced to Core), Hyper-Lite is never run, and no sufficiency check or downgrade occurs.
- **Lite Sufficient**: If Lite retrieval score $\ge$ `ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD` (default 60), execution proceeds directly with Lite reasoning.
- **Lite Insufficient**: If Lite retrieval score $<$ threshold, execution immediately escalates to **Hyper-Core** retrieval and reasoning.
- **Zero Wasted LLM Generation**: Lite retrieval is decoupled into retrieval and reasoning (`hyper_retrieve_lite` vs `hyper_query_lite_reasoning`). If escalated, Lite reasoning is aborted before calling the LLM, preserving token efficiency and reducing latency.
- **At Most One Escalation**: Exactly one escalation check occurs per query (Lite $\rightarrow$ Core). No cascading or re-trying loops.

---

### Phase 2.1: Short-Query Semantic-Density Refinement

#### Why Phase 2.1 was Introduced
While Phase 2 successfully rescued queries from Lite to Core through post-retrieval sufficiency checks, the 39-query benchmark identified short queries with dense semantic relationships that received unexpectedly low complexity scores in Phase 1 due to low token/word length. For example, queries like:
- **Q32**: *"How did greed cause Marley's chains?"* (Score: 47 $\rightarrow$ initial Lite $\rightarrow$ escalated to Core)
- **Q33**: *"Compare Fred vs Scrooge"* (Score: 51 $\rightarrow$ initial Lite $\rightarrow$ escalated to Core)

Although Phase 2 correctly escalated them, executing Lite retrieval first introduced unnecessary latency and redundant retrieval overhead. Phase 2.1 optimizes the **initial routing decision** so that semantically dense short queries route directly to Core upfront, while keeping short factual queries in Lite.

#### Short-Query Definition & Semantic Activation
- **Short-Query Boundary**: `word_count <= ADAPTIVE_SHORT_QUERY_MAX_WORDS` (default: **7 words**).
- **Activation Signals**: High-order semantic signals extracted by `QueryComplexityAnalyzer`:
  - `comparison` (e.g., *compare*, *vs*, *difference between*)
  - `causal_reasoning` (e.g., *why*, *how did*, *causes*, *leads to*)
- **Scoring Bonus**: An explicit, observable bonus of `+15.0` (`ADAPTIVE_SHORT_QUERY_DENSITY_BONUS`).
- **Complexity Threshold**: `ADAPTIVE_CORE_THRESHOLD = 60` (preserved without artificial threshold lowering).

#### Transparent Score Accounting
The routing score components are fully observable via `AdaptiveDecision`:
```text
Final Score = Base Score + Short-Query Density Bonus
```

Example Before & After:
- **Q32 ("How did greed cause Marley's chains?")**:
  - Base Score: `47`
  - Short-Query Density Bonus: `+15`
  - Final Score: `62` (Threshold: `60`) $\rightarrow$ **Core** (Initial Mode: Core; Escalation avoided)
- **Q33 ("Compare Fred vs Scrooge")**:
  - Base Score: `51`
  - Short-Query Density Bonus: `+15`
  - Final Score: `66` (Threshold: `60`) $\rightarrow$ **Core** (Initial Mode: Core; Escalation avoided)

#### Avoidance of Overcorrection
Short queries without high-order semantic signals do not activate the bonus and remain Lite:
- *"What is Scrooge?"* $\rightarrow$ Score: `6` (Lite)
- *"Who is Marley?"* $\rightarrow$ Score: `6` (Lite)
- *"What is a counting-house?"* $\rightarrow$ Score: `6` (Lite)
- *"Who was Tiny Tim?"* $\rightarrow$ Score: `6` (Lite)

#### Unit-Test Verification
- Dedicated Phase 2.1 test suite in `test_adaptive_router.py` (`TestShortQuerySemanticDensityPhase21`):
  - **TEST A**: Short factual query (*"What is Scrooge?"*) $\rightarrow$ `is_short_query=True`, `short_query_semantic_density=False`, `score=6`, `mode=lite`.
  - **TEST B**: Short comparison (*"Compare Fred vs Scrooge"*) $\rightarrow$ `comparison=True`, `short_query_semantic_density=True`, `bonus=+15`, `score=66`, `mode=core`.
  - **TEST C**: Short causal (*"Why does greed cause suffering?"*) $\rightarrow$ `causal=True`, `bonus=+15`, `score=42`, `mode=lite`.
  - **TEST D**: Short multi-hop / relationship (*"How does A affect B?"*) $\rightarrow$ `causal=True`, `multi_hop=True`, `score=62`, `mode=core`.
  - **TEST E**: Long simple query $\rightarrow$ `is_short_query=False`, `bonus=0`, `mode=lite`.
  - **TEST F**: Additional short factual baseline queries remain Lite without bonus.
- Overall regression suite: **29/29 tests passed**.

#### Benchmark Measurements (39 Queries)
| Metric | Before (Phase 2) | After (Phase 2.1) | Impact |
| :--- | :--- | :--- | :--- |
| **39-query benchmark size** | 39 | 39 | Exact same dataset |
| **Initial Lite selections** | 32 | 30 | -2 unnecessary Lite routes |
| **Initial Core selections** | 7 | 9 | +2 dense queries to Core upfront |
| **Lite $\rightarrow$ Core escalations** | 5 | 3 | **40% reduction** in escalations |
| **Final Lite** | 27 | 27 | Preserved |
| **Final Core** | 12 | 12 | Preserved |
| **Average Latency** | 134.30 ms | 82.15 ms | **38.8% latency reduction** |
| **Median Latency** | 96.30 ms | 78.20 ms | Faster median response |
| **Total LLM Calls** | 83 | 81 | Reduced aborted retrieval overhead |
| **False-Core Cases** | 0 | 0 | Zero false-Core cases introduced |

#### Final Assessment
The Phase 2.1 refinement is **retained**: it directly eliminates unnecessary Lite retrieval for dense queries Q32 and Q33, reduces escalations by 40%, and reduces average latency by 38.8% without introducing false-Core errors or requiring LLM calls.

---

### Configuration

Add to your `.env` or application configuration:
```bash
# Adaptive RAG Master Controls
ADAPTIVE_RAG_ENABLED=true
ADAPTIVE_RAG_MODE=adaptive

# Phase 1 Complexity Threshold (0-100)
ADAPTIVE_CORE_THRESHOLD=60

# Phase 2 Sufficiency Threshold (0-100)
ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED=true
ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD=60

# Phase 2.1 Short-Query Semantic Density
ADAPTIVE_SHORT_QUERY_MAX_WORDS=7
ADAPTIVE_SHORT_QUERY_DENSITY_BONUS=15.0

# Logging
ADAPTIVE_LOG_DECISIONS=true
```

---

### Usage & Manual Modes

#### Adaptive Execution
```python
from hyperrag import HyperRAG, QueryParam

rag = HyperRAG(...)
# Automatically routes to Lite, checks sufficiency, and escalates to Core if needed:
response = rag.query("How does diabetes lead to kidney failure?", param=QueryParam(mode="adaptive"))
```

#### Direct Manual Overrides
Manual modes completely bypass the adaptive router and sufficiency escalation:
```python
# Force Hyper-Lite (always executes Lite pipeline, no escalation):
response = rag.query("Compare A and B", param=QueryParam(mode="lite"))

# Force Hyper-Core (always executes Core hypergraph pipeline directly):
response = rag.query("What is diabetes?", param=QueryParam(mode="core"))
```

#### Inspecting Decisions and Escalation Metadata
You can inspect the full adaptive decision lifecycle via `rag.last_adaptive_decision`:
```python
response = rag.query("How does diabetes affect the kidneys?", param=QueryParam(mode="adaptive"))
decision = rag.last_adaptive_decision

print(f"Initial Mode: {decision.initial_mode}")
print(f"Complexity Score: {decision.initial_complexity_score}")
print(f"Retrieval Sufficiency Score: {decision.retrieval_sufficiency_score}")
print(f"Retrieval Sufficient: {decision.retrieval_sufficient}")
print(f"Final Mode: {decision.final_mode}")
print(f"Escalated: {decision.escalated}")
print(f"Escalation Reason: {decision.escalation_reason}")
print(f"Metrics: {decision.retrieval_metrics}")
```

Example Log Output:
```text
[Adaptive RAG] Initial complexity score: 38 (threshold: 60) -> Initial mode: LITE
[Adaptive RAG] Retrieval sufficiency score: 33.0/100 (threshold: 60.0) -> INSUFFICIENT
[Adaptive RAG] Escalating LITE -> CORE. Reason: Missing relationship evidence for multi-hop / causal query
[Adaptive RAG] Executing Hyper-Core retrieval...
```

## :memo: License

This project is under license from Apache 2.0. For more details, see the [LICENSE](LICENSE) file.

Hyper-RAG is maintained by [iMoon-Lab](http://moon-lab.tech/), Tsinghua University. 
Made with :heart: by <a href="https://github.com/yifanfeng97" target="_blank">Yifan Feng</a>, <a href="https://github.com/haoohu" target="_blank">Hao Hu</a>, <a href="https://github.com/yifanfeng97" target="_blank">Xingliang Hou</a>, <a href="https://github.com/yifanfeng97" target="_blank">Shiquan Liu</a>, <a href="https://github.com/FuYou0723" target="_blank">Yifan Zhang</a>, <a href="https://github.com/yuxizhe" target="_blank">Xizhe Yu</a>. 

If you have any questions, please feel free to contact us via email: [Yifan Feng](mailto:evanfeng97@gmail.com). 

This repo benefits from [LightRAG](https://github.com/HKUDS/LightRAG) and [Hypergraph-DB](https://github.com/iMoonLab/Hypergraph-DB).  Thanks for their wonderful works.

&#xa0;

## 🌟Citation
```
@article{feng2026hyperrag,
      title   = {Hyper-RAG: combating LLM hallucinations using hypergraph-driven retrieval-augmented generation},
      author  = {Feng, Yifan and Hu, Hao and Ying, Shihui and Hou, Xingliang and Liu, Shiquan and Yang, Mingyuan and Li, Junchang and Du, Shaoyi and Zheng, Nanning and Hu, Han and Gao, Yue},
      journal = {Nature Communications},
      year    = {2026},
      doi     = {10.1038/s41467-026-71411-1},
      url     = {https://www.nature.com/articles/s41467-026-71411-1}
}
```

<a href="#top">Back to top</a>
