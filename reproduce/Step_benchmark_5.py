# -*- coding: utf-8 -*-
"""
Hyper-RAG 5-Context Benchmark Script
Controlled single-run benchmark using:
- Primary LLM: OpenRouter (nvidia/nemotron-3-ultra-550b-a55b:free)
- Embeddings: Mistral (mistral-embed, 1024-dim)
- Working directory: caches/benchmark_5
- Dataset: First 5 contexts from caches/mix/contexts/mix_unique_contexts.json
"""

import sys
import os
import time
import json
import shutil
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows to prevent charmap encoding errors
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.append(str(Path(__file__).resolve().parent.parent))

import numpy as np
from openai import AsyncOpenAI

from hyperrag import HyperRAG, QueryParam
from hyperrag.utils import EmbeddingFunc
from hyperrag.llm import openrouter_nvidia_complete_if_cache
from hyperdb import HypergraphDB

from my_config import (
    EMB_API_KEY,
    EMB_BASE_URL,
    EMB_MODEL,
    EMB_DIM,
    OPENROUTER_MODEL,
    validate_config,
)

# Global API counters
openrouter_llm_requests = 0
mistral_embedding_requests = 0
nvidia_called = False
mistral_llm_called = False


async def llm_model_func(
    prompt,
    system_prompt=None,
    history_messages=None,
    **kwargs,
) -> str:
    global openrouter_llm_requests, nvidia_called, mistral_llm_called
    openrouter_llm_requests += 1
    nvidia_called = True

    try:
        # Strictly use NVIDIA OpenRouter, no Mistral fallback
        return await openrouter_nvidia_complete_if_cache(
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            **kwargs,
        )
    except Exception as e:
        print(f"\n[NVIDIA / OpenRouter LLM ERROR]: {type(e).__name__}: {e}")
        # Stop benchmark cleanly on failure, no retry storm
        raise


async def embedding_func(texts: list[str]) -> np.ndarray:
    global mistral_embedding_requests
    mistral_embedding_requests += 1

    try:
        client = AsyncOpenAI(
            api_key=EMB_API_KEY,
            base_url=EMB_BASE_URL,
            max_retries=0,  # Prevent internal SDK retry loops
        )
        response = await client.embeddings.create(
            model=EMB_MODEL,
            input=texts,
            encoding_format="float",
        )
        return np.array(
            [item.embedding for item in response.data],
            dtype=np.float32,
        )
    except Exception as e:
        status_code = getattr(e, "status_code", None)
        err_str = str(e)
        if status_code == 429 or "429" in err_str or "rate limit" in err_str.lower():
            print(f"\n[MISTRAL EMBEDDING RATE LIMIT 429 DETECTED]: {e}")
            print("Stopping benchmark immediately to prevent retry storm.")
        else:
            print(f"\n[MISTRAL EMBEDDING ERROR]: {type(e).__name__}: {e}")
        raise


def run_benchmark():
    validate_config(exit_on_error=True)

    benchmark_dir = Path("caches") / "benchmark_5"
    mix_context_file = Path("caches") / "mix" / "contexts" / "mix_unique_contexts.json"
    benchmark_context_file = benchmark_dir / "contexts" / "benchmark_5_unique_contexts.json"

    # ==================================================
    # 1. PREPARE FRESH DIRECTORY
    # ==================================================
    if benchmark_dir.exists():
        print(f"Removing existing benchmark directory: {benchmark_dir}")
        shutil.rmtree(benchmark_dir)

    benchmark_contexts_dir = benchmark_dir / "contexts"
    benchmark_contexts_dir.mkdir(parents=True, exist_ok=True)

    # ==================================================
    # 2. CREATE 5-CONTEXT DATASET
    # ==================================================
    if not mix_context_file.exists():
        raise FileNotFoundError(f"Source context file does not exist: {mix_context_file}")

    with open(mix_context_file, "r", encoding="utf-8-sig") as f:
        all_contexts = json.load(f)

    if len(all_contexts) < 5:
        raise ValueError(f"Source file contains fewer than 5 contexts: {len(all_contexts)}")

    benchmark_contexts = all_contexts[:5]

    with open(benchmark_context_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_contexts, f, indent=2, ensure_ascii=False)

    print("=== DATASET ===")
    print(f"Source: {mix_context_file}")
    print(f"Selected contexts: {len(benchmark_contexts)}")
    print(f"Output: {benchmark_context_file}\n")

    # ==================================================
    # 3. INITIALIZE HYPER-RAG
    # ==================================================
    rag = HyperRAG(
        working_dir=benchmark_dir,
        # Conservative settings
        llm_model_max_async=1,
        embedding_func_max_async=1,
        embedding_batch_num=32,
        entity_extract_max_gleaning=0,
        chunk_token_size=1000,
        chunk_overlap_token_size=0,
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=EMB_DIM,
            max_token_size=8192,
            func=embedding_func,
        ),
    )

    # ==================================================
    # 4. BUILD THE HYPERGRAPH
    # ==================================================
    print("=== BUILD START ===")
    build_start = time.perf_counter()

    try:
        rag.insert(benchmark_contexts)
    except Exception as e:
        print(f"\n[INSERTION FAILURE]: Hypergraph construction failed: {e}")
        print(f"OpenRouter LLM requests made before failure: {openrouter_llm_requests}")
        print(f"Mistral embedding requests made before failure: {mistral_embedding_requests}")
        raise

    build_time = time.perf_counter() - build_start
    print("=== BUILD COMPLETE ===")
    print(f"Build time: {build_time:.2f} seconds\n")

    # ==================================================
    # 5. RECORD HYPER-RAG STATISTICS FROM ACTUAL STORAGE
    # ==================================================
    # Documents count
    doc_file = benchmark_dir / "kv_store_full_docs.json"
    with open(doc_file, "r", encoding="utf-8") as f:
        docs_data = json.load(f)
    num_docs = len(docs_data)

    # Chunks count
    chunk_file = benchmark_dir / "kv_store_text_chunks.json"
    with open(chunk_file, "r", encoding="utf-8") as f:
        chunks_data = json.load(f)
    num_chunks = len(chunks_data)

    # Vertices and Hyperedges count from .hgdb file
    hgdb_file = benchmark_dir / "hypergraph_chunk_entity_relation.hgdb"
    hg = HypergraphDB()
    hg.load(str(hgdb_file))
    num_vertices = hg.num_v
    num_hyperedges = hg.num_e

    # ==================================================
    # 6. DO ONE GROUNDED MULTI-HOP QUERY
    # ==================================================
    question = (
        "Which film served as the directorial debut for Manimaran and starred "
        "the 2010 national Clean & Clear Fresh Face winner, and which film "
        "company established by Vetrimaaran co-produced it?"
    )

    print("=== QUESTION ===")
    print(question)
    print()

    query_start = time.perf_counter()

    try:
        answer = rag.query(
            question,
            param=QueryParam(mode="hyper"),
        )
    except Exception as e:
        print(f"\n[QUERY FAILURE]: Reasoning query failed: {e}")
        print(f"OpenRouter LLM requests made: {openrouter_llm_requests}")
        print(f"Mistral embedding requests made: {mistral_embedding_requests}")
        raise

    query_time = time.perf_counter() - query_start
    total_time = build_time + query_time

    print(f"Query time: {query_time:.2f} seconds\n")

    # ==================================================
    # 7. FINAL OUTPUT FORMAT
    # ==================================================
    print("========================================")
    print("       HYPER-RAG 5-CONTEXT BENCHMARK")
    print("========================================")
    print()
    print("Dataset")
    print("-------")
    print(f"Contexts: {len(benchmark_contexts)}")
    print(f"Working directory: {benchmark_dir}")
    print()
    print("Hypergraph")
    print("----------")
    print(f"Documents: {num_docs}")
    print(f"Chunks: {num_chunks}")
    print(f"Vertices: {num_vertices}")
    print(f"Hyperedges: {num_hyperedges}")
    print()
    print("API Usage")
    print("---------")
    print(f"OpenRouter LLM requests: {openrouter_llm_requests}")
    print(f"Mistral embedding requests: {mistral_embedding_requests}")
    print()
    print("Timing")
    print("------")
    print(f"Build time: {build_time:.2f} seconds")
    print(f"Query time: {query_time:.2f} seconds")
    print(f"Total time: {total_time:.2f} seconds")
    print()
    print("Question")
    print("--------")
    print(question)
    print()
    print("Answer")
    print("------")
    print(answer)
    print()
    print("========================================")
    print()

    # ==================================================
    # 8. VALIDATION OF NVIDIA ANSWER
    # ==================================================
    # Check if answer is in English
    # Quick ascii / latin check
    non_ascii_ratio = sum(1 for c in answer if ord(c) > 127) / max(len(answer), 1)
    is_english = "YES" if non_ascii_ratio < 0.10 else "NO"

    # Check grounding: contains key entities from the benchmark contexts
    grounded_keys = ["udhayam nh4", "ashrita", "grass root"]
    grounded_matches = sum(1 for k in grounded_keys if k in answer.lower())
    grounded = "YES" if grounded_matches >= 2 else ("UNCERTAIN" if grounded_matches == 1 else "NO")

    print("VALIDATION:")
    print(f"NVIDIA provider confirmed: {'YES' if nvidia_called else 'NO'}")
    print(f"Mistral LLM fallback detected: {'YES' if mistral_llm_called else 'NO'}")
    print(f"English response: {is_english}")
    print(f"Answer grounded in benchmark contexts: {grounded}")


if __name__ == "__main__":
    run_benchmark()
