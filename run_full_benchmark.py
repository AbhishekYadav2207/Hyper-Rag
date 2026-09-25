# -*- coding: utf-8 -*-
"""
Adaptive Hyper-RAG Full Evaluation and Benchmark Suite.
Evaluates 39 realistic queries across 13 categories on caches/mock.
Measures:
- Phase 1: Query complexity routing
- Phase 2: Retrieval sufficiency
- Lite -> Core escalation
- Fixed Lite vs. Fixed Core vs. Adaptive execution
- Threshold analysis (40, 50, 60, 70)
- Execution latency, LLM request count, retrieval item count, and context size
"""
import sys
import json
import base64
import time
import asyncio
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent))

from hyperrag import HyperRAG, QueryParam
from hyperrag.utils import EmbeddingFunc
from hyperrag.adaptive_router import AdaptiveRouter, ComplexityWeights
from hyperrag.retrieval_sufficiency import RetrievalSufficiencyEvaluator

# =============================================================================
# 1. EVALUATION DATASET (39 QUERIES ACROSS 13 CATEGORIES)
# =============================================================================
EVALUATION_QUERIES = [
    # 1. Simple factual
    {"id": "Q01", "category": "Simple factual", "query": "Who is Ebenezer Scrooge?", "expected_requirement": "Lite"},
    {"id": "Q02", "category": "Simple factual", "query": "Who was Jacob Marley in relation to Scrooge?", "expected_requirement": "Lite"},
    {"id": "Q03", "category": "Simple factual", "query": "Where is Scrooge's counting-house located?", "expected_requirement": "Lite"},

    # 2. Definition
    {"id": "Q04", "category": "Definition", "query": "What is a counting-house?", "expected_requirement": "Lite"},
    {"id": "Q05", "category": "Definition", "query": "What is the Ghost of Christmas Past?", "expected_requirement": "Lite"},
    {"id": "Q06", "category": "Definition", "query": "What are Bed-curtains in the story?", "expected_requirement": "Lite"},

    # 3. Single-entity explanation
    {"id": "Q07", "category": "Single-entity explanation", "query": "Describe the character and personality of Bob Cratchit.", "expected_requirement": "Lite"},
    {"id": "Q08", "category": "Single-entity explanation", "query": "Explain the significance of Tiny Tim in the narrative.", "expected_requirement": "Lite"},
    {"id": "Q09", "category": "Single-entity explanation", "query": "What role does Mr. Fezziwig play in Scrooge's memories?", "expected_requirement": "Lite"},

    # 4. Multi-aspect
    {"id": "Q10", "category": "Multi-aspect", "query": "What are the appearance, behavior, actions, and lessons of the Ghost of Christmas Present?", "expected_requirement": "Core"},
    {"id": "Q11", "category": "Multi-aspect", "query": "Detail the background, occupation, family life, and struggles of Bob Cratchit.", "expected_requirement": "Core"},
    {"id": "Q12", "category": "Multi-aspect", "query": "Explain the causes, manifestations, consequences, and resolution of Scrooge's miserliness.", "expected_requirement": "Core"},

    # 5. Comparison
    {"id": "Q13", "category": "Comparison", "query": "Compare Ebenezer Scrooge and Mr. Fezziwig in terms of their treatment of employees.", "expected_requirement": "Core"},
    {"id": "Q14", "category": "Comparison", "query": "What is the difference between the Ghost of Christmas Past and the Ghost of Christmas Present?", "expected_requirement": "Core"},
    {"id": "Q15", "category": "Comparison", "query": "Compare the attitudes of Scrooge and his nephew Fred towards Christmas.", "expected_requirement": "Core"},

    # 6. Causal
    {"id": "Q16", "category": "Causal", "query": "How does Marley's death contribute to Scrooge's isolation?", "expected_requirement": "Core"},
    {"id": "Q17", "category": "Causal", "query": "Why did Belle decide to break her engagement with Scrooge?", "expected_requirement": "Core"},
    {"id": "Q18", "category": "Causal", "query": "What causes Scrooge to change his attitude towards humanity?", "expected_requirement": "Core"},

    # 7. Temporal
    {"id": "Q19", "category": "Temporal", "query": "How has Scrooge's relationship with Christmas evolved over time from his youth to old age?", "expected_requirement": "Core"},
    {"id": "Q20", "category": "Temporal", "query": "Describe the chronological progression of the visits of the three spirits during the night.", "expected_requirement": "Core"},
    {"id": "Q21", "category": "Temporal", "query": "Historically, how did Scrooge's partnership with Jacob Marley develop over the years?", "expected_requirement": "Core"},

    # 8. Multi-hop
    {"id": "Q22", "category": "Multi-hop", "query": "How does Scrooge's treatment of Bob Cratchit affect Tiny Tim through family circumstances?", "expected_requirement": "Core"},
    {"id": "Q23", "category": "Multi-hop", "query": "What is the connection between Marley's warning, the visit of the spirits, and Scrooge's redemption?", "expected_requirement": "Core"},
    {"id": "Q24", "category": "Multi-hop", "query": "Explain the relationship between greed, poverty, and the children Ignorance and Want.", "expected_requirement": "Core"},

    # 9. Aggregation
    {"id": "Q25", "category": "Aggregation", "query": "List all the spirits and apparitions that visit Scrooge during the story.", "expected_requirement": "Core"},
    {"id": "Q26", "category": "Aggregation", "query": "Summarize all the visions shown to Scrooge by the Ghost of Christmas Yet to Come.", "expected_requirement": "Core"},
    {"id": "Q27", "category": "Aggregation", "query": "Provide a comprehensive overview of all the Cratchit family members mentioned in the text.", "expected_requirement": "Core"},

    # 10. Long but simple
    {"id": "Q28", "category": "Long but simple", "query": "Could you please be kind enough to tell me who Ebenezer Scrooge is in simple everyday language?", "expected_requirement": "Lite"},
    {"id": "Q29", "category": "Long but simple", "query": "I was wondering if you might provide me with some basic background information regarding who Jacob Marley was.", "expected_requirement": "Lite"},
    {"id": "Q30", "category": "Long but simple", "query": "If it is not too much trouble, can you please tell me where the story takes place in England?", "expected_requirement": "Lite"},

    # 11. Short but complex
    {"id": "Q31", "category": "Short but complex", "query": "Why Fezziwig versus Scrooge?", "expected_requirement": "Core"},
    {"id": "Q32", "category": "Short but complex", "query": "How did greed cause Marley's chains?", "expected_requirement": "Core"},
    {"id": "Q33", "category": "Short but complex", "query": "Compare Fred vs Scrooge.", "expected_requirement": "Core"},

    # 12. Ambiguous
    {"id": "Q34", "category": "Ambiguous", "query": "What happened to the clerk?", "expected_requirement": "Lite/Borderline"},
    {"id": "Q35", "category": "Ambiguous", "query": "Who was the partner?", "expected_requirement": "Lite/Borderline"},
    {"id": "Q36", "category": "Ambiguous", "query": "Tell me about the boy.", "expected_requirement": "Lite/Borderline"},

    # 13. Relationship-heavy
    {"id": "Q37", "category": "Relationship-heavy", "query": "Explain the complex relationship between Ebenezer Scrooge, Bob Cratchit, and Tiny Tim.", "expected_requirement": "Core"},
    {"id": "Q38", "category": "Relationship-heavy", "query": "Detail the interactions and shared history between Scrooge, Belle, and Fezziwig.", "expected_requirement": "Core"},
    {"id": "Q39", "category": "Relationship-heavy", "query": "How do the three Christmas spirits interconnect to influence Scrooge's ultimate transformation?", "expected_requirement": "Core"},
]

# =============================================================================
# 2. VECTOR MATRIX & EMBEDDING SIMULATOR
# =============================================================================
def load_precomputed_embeddings():
    d = json.load(open("caches/mock/vdb_entities.json", encoding="utf-8"))
    mat = np.frombuffer(base64.b64decode(d["matrix"]), dtype=np.float32).reshape(-1, 1024)
    entity_map = {}
    for i, item in enumerate(d["data"]):
        name = item.get("entity_name", "").lower().strip()
        if name:
            entity_map[name] = mat[i]
            for word in re.findall(r"\b[a-z]{4,}\b", name):
                if word not in entity_map:
                    entity_map[word] = mat[i]
    return entity_map, mat

ENTITY_MAP, FULL_MATRIX = load_precomputed_embeddings()

async def benchmark_embed(texts: list[str]) -> np.ndarray:
    results = []
    for t in texts:
        t_clean = t.lower().strip()
        if t_clean in ENTITY_MAP:
            results.append(ENTITY_MAP[t_clean])
            continue
        matched_vecs = []
        words = re.findall(r"\b[a-z]{4,}\b", t_clean)
        for w in words:
            if w in ENTITY_MAP:
                matched_vecs.append(ENTITY_MAP[w])
        if matched_vecs:
            avg_v = np.mean(matched_vecs, axis=0)
            avg_v = avg_v / (np.linalg.norm(avg_v) + 1e-9)
            results.append(avg_v)
        else:
            rnd = np.random.randn(1024).astype(np.float32)
            rnd = rnd / (np.linalg.norm(rnd) + 1e-9)
            results.append(rnd)
    return np.array(results, dtype=np.float32)

# =============================================================================
# 3. INSTRUMENTED LLM MOCK FOR BENCHMARKING
# =============================================================================
class InstrumentedLLM:
    def __init__(self):
        self.call_count = 0
        self.context_lengths = []

    def reset(self):
        self.call_count = 0
        self.context_lengths = []

    async def __call__(self, prompt, system_prompt=None, history_messages=None, **kwargs):
        self.call_count += 1
        
        # Keyword extraction prompt
        if "low_level_keywords" in prompt or "keywords_extraction" in prompt:
            query_match = re.search(r"User Query:?\s*(.*?)(?:$|\n\n)", prompt, re.DOTALL | re.IGNORECASE)
            q_text = query_match.group(1).strip() if query_match else prompt[-100:]
            terms = [w for w in re.findall(r"[A-Z][a-z]+|[a-z]+", q_text) if len(w) > 3 and w.lower() not in {"what", "who", "where", "explain", "describe", "compare", "between", "versus", "with", "from", "terms", "story", "text"}]
            low_level = terms[:4] if terms else ["scrooge"]
            high_level = [t for t in terms if len(t) > 5][:2]
            return json.dumps({
                "low_level_keywords": low_level,
                "high_level_keywords": high_level
            })
        
        # Reasoning prompt
        self.context_lengths.append(len(prompt))
        # Realistic LLM inference delay simulation: ~60ms per call
        await asyncio.sleep(0.06)
        return f"Synthesized reasoning response based on {len(prompt)} characters of context."

# =============================================================================
# 4. BENCHMARK RUNNER
# =============================================================================
async def run_benchmark():
    print("=" * 110)
    print("STARTING ADAPTIVE HYPER-RAG EVALUATION & BENCHMARK")
    print(f"Total Test Queries: {len(EVALUATION_QUERIES)} across 13 Categories")
    print("=" * 110)

    llm_instance = InstrumentedLLM()
    rag = HyperRAG(
        working_dir="caches/mock",
        llm_model_func=llm_instance,
        embedding_func=EmbeddingFunc(embedding_dim=1024, max_token_size=8192, func=benchmark_embed)
    )

    results_data = []

    for idx, item in enumerate(EVALUATION_QUERIES, 1):
        qid = item["id"]
        cat = item["category"]
        q = item["query"]
        expected = item["expected_requirement"]

        # -------------------------------------------------------------
        # A. Run Fixed Lite
        # -------------------------------------------------------------
        llm_instance.reset()
        t0 = time.time()
        err_lite = None
        try:
            res_lite = await rag.aquery(q, param=QueryParam(mode="lite"))
        except Exception as e:
            err_lite = str(e)
        t_lite = time.time() - t0
        lite_llm_calls = llm_instance.call_count
        lite_ctx_size = llm_instance.context_lengths[-1] if llm_instance.context_lengths else 0

        # -------------------------------------------------------------
        # B. Run Fixed Core
        # -------------------------------------------------------------
        llm_instance.reset()
        t0 = time.time()
        err_core = None
        try:
            res_core = await rag.aquery(q, param=QueryParam(mode="core"))
        except Exception as e:
            err_core = str(e)
        t_core = time.time() - t0
        core_llm_calls = llm_instance.call_count
        core_ctx_size = llm_instance.context_lengths[-1] if llm_instance.context_lengths else 0

        # -------------------------------------------------------------
        # C. Run Adaptive
        # -------------------------------------------------------------
        llm_instance.reset()
        t0 = time.time()
        err_adapt = None
        try:
            res_adapt = await rag.aquery(q, param=QueryParam(mode="adaptive"))
        except Exception as e:
            err_adapt = str(e)
        t_adapt = time.time() - t0
        adapt_llm_calls = llm_instance.call_count
        adapt_ctx_size = llm_instance.context_lengths[-1] if llm_instance.context_lengths else 0

        dec = rag.last_adaptive_decision
        complexity_score = dec.score if dec else None
        initial_mode = dec.initial_mode if dec else None
        suff_score = dec.retrieval_sufficiency_score if dec else None
        suff_bool = dec.retrieval_sufficient if dec else None
        final_mode = dec.final_mode if dec else None
        escalated = dec.escalated if dec else False
        escalation_reason = dec.escalation_reason if dec else None
        ret_item_count = dec.retrieval_metrics.get("num_items", 0) if (dec and dec.retrieval_metrics) else 0

        # Record query result
        entry = {
            "id": qid,
            "category": cat,
            "query": q,
            "expected_requirement": expected,
            "complexity_score": complexity_score,
            "initial_mode": initial_mode,
            "retrieval_sufficiency_score": suff_score,
            "retrieval_sufficient": suff_bool,
            "final_mode": final_mode,
            "escalated": escalated,
            "escalation_reason": escalation_reason,
            "lite_latency_ms": round(t_lite * 1000, 1),
            "core_latency_ms": round(t_core * 1000, 1),
            "adapt_latency_ms": round(t_adapt * 1000, 1),
            "lite_llm_calls": lite_llm_calls,
            "core_llm_calls": core_llm_calls,
            "adapt_llm_calls": adapt_llm_calls,
            "retrieval_item_count": ret_item_count,
            "context_size": adapt_ctx_size,
            "error_status": err_adapt or "OK"
        }
        results_data.append(entry)

        status_marker = "ESCALATED" if escalated else ("CORE" if final_mode == "core" else "LITE")
        print(f"[{qid}] ({cat:<22}) Score:{complexity_score:>2} | Init:{initial_mode:<4} | Suff:{str(suff_score):>4} | Final:{final_mode:<4} | {status_marker:<9} | {t_adapt*1000:>6.1f}ms")

    # Save raw benchmark data
    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)
    print("\nSaved full benchmark data to benchmark_results.json")

    # -------------------------------------------------------------
    # 5. THRESHOLD ANALYSIS (40, 50, 60, 70)
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("THRESHOLD SENSITIVITY ANALYSIS")
    print("=" * 80)
    thresholds = [40, 50, 60, 70]
    th_summary = {}

    evaluator = RetrievalSufficiencyEvaluator(threshold=60.0, log_evaluations=False)

    for th in thresholds:
        router_th = AdaptiveRouter(core_threshold=th, log_decisions=False)
        lite_count = 0
        core_count = 0
        escalation_count = 0

        for item in results_data:
            q = item["query"]
            d = router_th.route(q)
            if d.mode == "core":
                core_count += 1
            else:
                # Lite initially: check if it escalated in the real benchmark
                # A query escalates if its retrieval sufficiency was insufficient (< 60)
                suff = item["retrieval_sufficiency_score"]
                if suff is not None and suff < 60.0:
                    escalation_count += 1
                    core_count += 1
                else:
                    lite_count += 1

        th_summary[th] = {
            "initial_lite": 39 - (core_count - escalation_count),
            "final_lite": lite_count,
            "final_core": core_count,
            "escalations": escalation_count
        }
        print(f"Threshold: {th:<2} | Initial Lite: {39 - (core_count - escalation_count):<2} | Final Lite: {lite_count:<2} | Final Core: {core_count:<2} | Escalations: {escalation_count:<2}")

    with open("threshold_analysis.json", "w", encoding="utf-8") as f:
        json.dump(th_summary, f, indent=2)

    return results_data, th_summary

if __name__ == "__main__":
    asyncio.run(run_benchmark())
