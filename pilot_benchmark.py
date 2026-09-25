# -*- coding: utf-8 -*-
"""
Pilot test with exact matrix-backed embedding lookup.
"""
import sys
import json
import base64
import time
import asyncio
import re
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent))

from hyperrag import HyperRAG, QueryParam
from hyperrag.utils import EmbeddingFunc

def load_precomputed_embeddings():
    d = json.load(open("caches/mock/vdb_entities.json", encoding="utf-8"))
    mat = np.frombuffer(base64.b64decode(d["matrix"]), dtype=np.float32).reshape(-1, 1024)
    entity_map = {}
    for i, item in enumerate(d["data"]):
        name = item.get("entity_name", "").lower().strip()
        if name:
            entity_map[name] = mat[i]
            # Also map individual words if >= 4 chars
            for word in re.findall(r"\b[a-z]{4,}\b", name):
                if word not in entity_map:
                    entity_map[word] = mat[i]
    return entity_map, mat

entity_map, full_matrix = load_precomputed_embeddings()

async def benchmark_embed(texts: list[str]) -> np.ndarray:
    results = []
    for t in texts:
        t_clean = t.lower().strip()
        # Direct match
        if t_clean in entity_map:
            results.append(entity_map[t_clean])
            continue
        # Substring or word match
        matched_vecs = []
        words = re.findall(r"\b[a-z]{4,}\b", t_clean)
        for w in words:
            if w in entity_map:
                matched_vecs.append(entity_map[w])
        if matched_vecs:
            avg_v = np.mean(matched_vecs, axis=0)
            avg_v = avg_v / (np.linalg.norm(avg_v) + 1e-9)
            results.append(avg_v)
        else:
            # Unmatched / novel entity: small random vector perpendicular to main cluster
            rnd = np.random.randn(1024).astype(np.float32)
            rnd = rnd / (np.linalg.norm(rnd) + 1e-9)
            results.append(rnd)
    return np.array(results, dtype=np.float32)

def get_smart_llm():
    call_counts = {"count": 0, "contexts": []}

    async def benchmark_llm(prompt, system_prompt=None, history_messages=None, **kwargs):
        call_counts["count"] += 1
        
        # Check if this is keyword extraction
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
        
        # Reasoning call: record context size and simulate realistic inference
        call_counts["contexts"].append(len(prompt))
        await asyncio.sleep(0.05)
        return f"Synthesized response for context length {len(prompt)}."

    return benchmark_llm, call_counts

async def test_pilot():
    llm_func, tracker = get_smart_llm()
    rag = HyperRAG(
        working_dir="caches/mock",
        llm_model_func=llm_func,
        embedding_func=EmbeddingFunc(embedding_dim=1024, max_token_size=8192, func=benchmark_embed)
    )

    test_queries = [
        ("Who is Ebenezer Scrooge?", "Simple factual"),
        ("What is a counting-house?", "Definition"),
        ("Compare Ebenezer Scrooge and Mr. Fezziwig in terms of their treatment of employees.", "Comparison"),
    ]

    for q, cat in test_queries:
        print(f"\n--- Query: {q} ({cat}) ---")
        tracker["count"] = 0
        tracker["contexts"] = []
        t0 = time.time()
        res = await rag.aquery(q, param=QueryParam(mode="adaptive"))
        dt = time.time() - t0
        dec = rag.last_adaptive_decision
        print(f"Adaptive: time={dt*1000:.1f}ms, LLM calls={tracker['count']}")
        print(f"Dec: initial={dec.initial_mode}, score={dec.score}, suff={dec.retrieval_sufficiency_score}, final={dec.final_mode}, escalated={dec.escalated}")

if __name__ == "__main__":
    asyncio.run(test_pilot())
