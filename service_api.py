from __future__ import annotations

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple, Any

import asyncio
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# =============================================================================
# Logging
# =============================================================================
logger = logging.getLogger("hyperrag_api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# =============================================================================
# Configuration (Environment Variables)
# =============================================================================
DATA_NAME = os.getenv("HYPERRAG_DATA_NAME", "pathology").strip()
MODE = os.getenv("HYPERRAG_MODE", "hyper").strip()  # hyper | hyper-lite | naive | llm
MAX_QPS = float(os.getenv("HYPERRAG_MAX_QPS", "3").strip() or "3")
API_KEY = os.getenv("HYPERRAG_API_KEY", "").strip()
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("HYPERRAG_ALLOWED_ORIGINS", "*").split(",")]

# =============================================================================
# Directory and Import Paths
# =============================================================================
THIS_FILE = Path(__file__).resolve()
ROOT = THIS_FILE.parent
WORKING_DIR = ROOT / "caches" / DATA_NAME

sys.path.append(str(ROOT))

# =============================================================================
# Internal Imports
# =============================================================================
from hyperrag import HyperRAG, QueryParam  # noqa: E402
from hyperrag.utils import EmbeddingFunc  # noqa: E402
from hyperrag.llm import openrouter_mistral_stream_if_cache  # noqa: E402

from reproduce.Step_3_response_question import llm_model_func, embedding_func  # noqa: E402
from my_config import EMB_DIM  # noqa: E402

# =============================================================================
# FastAPI
# =============================================================================
app = FastAPI(title="HyperRAG API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag: Optional[HyperRAG] = None
query_param: Optional[QueryParam] = None

# =============================================================================
# Request/Response Schemas
# =============================================================================
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=6000)
    mode: Optional[str] = Field(
        default=None,
        description="Override default mode: adaptive / hyper / core / hyper-lite / lite / naive / llm",
    )


class QueryResponse(BaseModel):
    answer: str
    mode: str
    latency_ms: int
    adaptive_decision: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    language_guard: Optional[Dict[str, Any]] = None


# =============================================================================
# Rate Limiting (single-process)
# =============================================================================
_rate_state: Dict[str, Tuple[float, int]] = {}
_RATE_WINDOW_SEC = 1.0


def _rate_limit(ip: str) -> None:
    if MAX_QPS <= 0:
        return
    now = time.time()
    window_start, count = _rate_state.get(ip, (now, 0))
    if now - window_start >= _RATE_WINDOW_SEC:
        _rate_state[ip] = (now, 1)
        return
    if count >= int(MAX_QPS):
        raise HTTPException(status_code=429, detail="Too many requests (rate limit exceeded). Please try again later.")
    _rate_state[ip] = (window_start, count + 1)


def _require_api_key(x_api_key: Optional[str]) -> None:
    if not API_KEY:
        return
    if (not x_api_key) or (x_api_key != API_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid X-API-Key")


# =============================================================================
# Startup: Initialize HyperRAG (inject llm_model_stream_func)
# =============================================================================
@app.on_event("startup")
async def _startup() -> None:
    global rag, query_param
    WORKING_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Starting HyperRAG service")
    logger.info("ROOT=%s", ROOT)
    logger.info("WORKING_DIR=%s", WORKING_DIR)
    logger.info("MODE=%s", MODE)

    async def llm_model_stream_func(prompt, system_prompt=None, history_messages=None, **kwargs):
        # OpenRouter -> Mistral streaming output
        async for tok in openrouter_mistral_stream_if_cache(
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            **kwargs,
        ):
            yield tok

    rag = HyperRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_model_func,                 # Non-streaming
        llm_model_stream_func=llm_model_stream_func,   # Streaming
        embedding_func=EmbeddingFunc(
            embedding_dim=EMB_DIM,
            max_token_size=8192,
            func=embedding_func,
        ),
    )

    query_param = QueryParam(mode=MODE)
    logger.info("HyperRAG started successfully")


@app.on_event("shutdown")
async def _shutdown() -> None:
    logger.info("Shutting down HyperRAG service")


# =============================================================================
# Endpoints
# =============================================================================
@app.get("/healthz")
async def healthz() -> dict:
    return {
        "status": "ok",
        "data_name": DATA_NAME,
        "mode": MODE,
        "working_dir": str(WORKING_DIR),
        "api_key_required": bool(API_KEY),
    }


@app.post("/query", response_model=QueryResponse)
async def query(
    req: QueryRequest,
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> QueryResponse:
    _require_api_key(x_api_key)
    ip = request.client.host if request.client else "unknown"
    _rate_limit(ip)

    if rag is None:
        raise HTTPException(status_code=503, detail="Service is not ready yet. Please try again later.")

    mode = (req.mode or MODE).strip().lower()
    valid_modes = {"adaptive", "hyper", "core", "hyper-lite", "lite", "naive", "llm"}
    if mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode parameter: valid modes are {', '.join(sorted(valid_modes))}",
        )

    qp = QueryParam(mode=mode)

    t0 = time.time()
    try:
        answer = await rag.aquery(req.question, param=qp)
    except Exception as e:
        logger.exception("Query execution failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    latency_ms = int((time.time() - t0) * 1000)
    decision_dict = (
        rag.last_adaptive_decision.to_dict()
        if getattr(rag, "last_adaptive_decision", None)
        else None
    )
    val_dict = (
        rag.last_validation_result.to_dict()
        if getattr(rag, "last_validation_result", None)
        else None
    )
    lang_dict = (
        rag.last_language_result.to_dict()
        if getattr(rag, "last_language_result", None)
        else None
    )
    return QueryResponse(
        answer=answer,
        mode=mode,
        latency_ms=latency_ms,
        adaptive_decision=decision_dict,
        validation=val_dict,
        language_guard=lang_dict,
    )


@app.post("/query_stream")
async def query_stream(
    req: QueryRequest,
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    HyperRAG streaming output:
    - Calls rag.astream_query(...), retrieves/graphs/constrains within HyperRAG,
      then streams tokens from the LLM.
    """
    _require_api_key(x_api_key)
    ip = request.client.host if request.client else "unknown"
    _rate_limit(ip)

    if rag is None:
        raise HTTPException(status_code=503, detail="Service is not ready yet. Please try again later.")

    mode = (req.mode or MODE).strip().lower()
    valid_modes = {"adaptive", "hyper", "core", "hyper-lite", "lite", "naive", "llm"}
    if mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode parameter: valid modes are {', '.join(sorted(valid_modes))}",
        )

    qp = QueryParam(mode=mode)

    async def gen():
        try:
            async for tok in rag.astream_query(req.question, param=qp):
                if tok:
                    yield tok
                await asyncio.sleep(0)
        except Exception as e:
            logger.exception("query_stream execution failed: %s", e)
            yield f"\n[ERROR] {str(e)}\n"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")
