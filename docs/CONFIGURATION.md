# Hyper-RAG Configuration Reference

This guide details all environment variables, system constants, and runtime parameters across Hyper-RAG and Adaptive Hyper-RAG.

---

## 1. Configuration Architecture

Hyper-RAG loads configuration values using a hierarchical lookup pattern:
1. Active environment variables (e.g. injected in container or shell).
2. The root `.env` file (loaded via `python-dotenv`).
3. Built-in defaults in `my_config.py`.

```text
┌─────────────────────────────────┐
│     OS Environment Variables    │ (Highest Priority)
└───────────────┬─────────────────┘
                │ fallback
┌───────────────▼─────────────────┐
│           Root .env             │
└───────────────┬─────────────────┘
                │ fallback
┌───────────────▼─────────────────┐
│   my_config.py Defaults         │ (Lowest Priority)
└─────────────────────────────────┘
```

---

## 2. LLM Provider Configuration (OpenRouter ONLY)

> [!IMPORTANT]
> **OpenRouter is the ONLY LLM provider.** It handles all text generation and streaming. Mistral is an embedding-only provider and is never used as an LLM reasoning fallback.

| Variable Name | Type | Default | Allowed Values | Example | Purpose & Effect |
|---|---|---|---|---|---|
| `OPENROUTER_API_KEYS` | `str` | *None* | Comma-separated keys | `sk-or-v1-k1,sk-or-v1-k2` | List of OpenRouter API keys used for round-robin rotation. |
| `OPENROUTER_API_KEY` | `str` | *None* | Single API key string | `sk-or-v1-k1` | Backward-compatible fallback if `OPENROUTER_API_KEYS` is omitted. |
| `OPENROUTER_BASE_URL` | `str` | `https://openrouter.ai/api/v1` | Valid HTTP/HTTPS URL | `https://openrouter.ai/api/v1` | Base URL for OpenAI-compatible endpoint. |
| `OPENROUTER_MODEL` | `str` | `nvidia/nemotron-3-ultra-550b-a55b:free` | Valid OpenRouter model ID | `meta-llama/llama-3.3-70b-instruct` | Model identifier used for reasoning and streaming. |

---

## 3. Embedding Provider Configuration (Mistral ONLY)

> [!IMPORTANT]
> **Mistral is the ONLY embedding provider.** It generates 1024-dimensional dense vectors stored in vector databases.

| Variable Name | Type | Default | Allowed Values | Example | Purpose & Effect |
|---|---|---|---|---|---|
| `EMB_API_KEYS` | `str` | *None* | Comma-separated keys | `key1,key2` | List of Mistral API keys for rotation. |
| `EMB_API_KEY` | `str` | *None* | Single API key string | `key1` | Single key fallback if `EMB_API_KEYS` is omitted. |
| `MISTRAL_API_KEY` | `str` | *None* | Single API key string | `key1` | Backward-compatibility alias for `EMB_API_KEY`. |
| `EMB_BASE_URL` | `str` | `https://api.mistral.ai/v1` | Valid HTTP/HTTPS URL | `https://api.mistral.ai/v1` | Mistral API endpoint URL. |
| `EMB_MODEL` | `str` | `mistral-embed` | Official Mistral model | `mistral-embed` | Embedding model identifier. |
| `EMB_DIM` | `int` | `1024` | `1024` (Strict) | `1024` | Output embedding dimension. Must match index dimension. |

---

## 4. Adaptive Hyper-RAG Routing Configuration

### General Adaptive Controls
| Variable Name | Type | Default | Allowed Values | Example | Purpose & Effect |
|---|---|---|---|---|---|
| `ADAPTIVE_RAG_ENABLED` | `bool` | `true` | `true`, `false`, `1`, `0` | `true` | Master toggle. If `false`, falls back to `core` mode. |
| `ADAPTIVE_RAG_MODE` | `str` | `adaptive` | `adaptive`, `core`, `lite` | `adaptive` | Default mode when client does not supply one. |
| `ADAPTIVE_LOG_DECISIONS` | `bool` | `true` | `true`, `false` | `true` | Emits detailed routing and escalation logs to console. |

### Phase 1: Pre-Retrieval Complexity Scoring
| Variable Name | Type | Default | Allowed Values | Example | Purpose & Effect |
|---|---|---|---|---|---|
| `ADAPTIVE_CORE_THRESHOLD` | `int` | `60` | `0` to `100` | `60` | Score cutoff. Score $\ge 60$ routes to Core; $< 60$ routes to Lite. |

### Phase 2: Post-Retrieval Sufficiency Evaluation
| Variable Name | Type | Default | Allowed Values | Example | Purpose & Effect |
|---|---|---|---|---|---|
| `ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED` | `bool` | `true` | `true`, `false` | `true` | Enables post-retrieval sufficiency check on Lite retrieval. |
| `ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD` | `int` | `60` | `0` to `100` | `60` | Sufficiency cutoff. Score $< 60$ escalates Lite $\rightarrow$ Core. |

### Phase 2.1: Short-Query Semantic Density
| Variable Name | Type | Default | Allowed Values | Example | Purpose & Effect |
|---|---|---|---|---|---|
| `ADAPTIVE_SHORT_QUERY_MAX_WORDS` | `int` | `7` | `1` to `50` | `7` | Maximum word count to qualify for short-query bonus. |
| `ADAPTIVE_SHORT_QUERY_DENSITY_BONUS` | `float` | `15.0` | `0.0` to `100.0` | `15.0` | Points added when short query contains comparison or causal terms. |

---

## 5. Phase 3: Response Validation Configuration

| Variable Name | Type | Default | Allowed Values | Example | Purpose & Effect |
|---|---|---|---|---|---|
| `ADAPTIVE_VALIDATION_ENABLED` | `bool` | `true` | `true`, `false` | `true` | Master toggle for Phase 3 response validation. |
| `ADAPTIVE_VALIDATION_THRESHOLD` | `float` | `70.0` | `0.0` to `100.0` | `70.0` | Minimum weighted score required for `valid = True`. |
| `ADAPTIVE_VALIDATION_LOG_DECISIONS` | `bool` | `true` | `true`, `false` | `true` | Emits validation score breakdowns to the application log. |
| `ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT` | `float` | `0.40` | `0.0` to `1.0` | `0.40` | Weight for completeness dimension ($W_1$). |
| `ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT` | `float` | `0.40` | `0.0` to `1.0` | `0.40` | Weight for evidence support dimension ($W_2$). |
| `ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT` | `float` | `0.20` | `0.0` to `1.0` | `0.20` | Weight for query relevance dimension ($W_3$). |

> [!NOTE]
> The sum of the three validation weights must be greater than zero. The default weights sum to $1.00$ ($0.40 + 0.40 + 0.20 = 1.00$).

---

## 6. Server & Network Configuration

Used by `service_api.py` and `web-ui/backend/main.py`:

| Variable Name | Type | Default | Example | Purpose & Effect |
|---|---|---|---|---|
| `HOST` / `HYPERRAG_HOST` | `str` | `0.0.0.0` | `127.0.0.1` | Network interface to bind HTTP server. |
| `PORT` / `HYPERRAG_PORT` | `int` | `8002` (service) / `8000` (web-ui) | `8000` | Port on which the FastAPI application listens. |
| `WORKING_DIR` | `str` | `./caches/pathology` | `./caches/default` | Local directory storing hypergraphs and vector indices. |
| `HYPERRAG_API_KEY` | `str` | `""` (Empty) | `secret-token` | If set, enforces client authentication via `X-API-Key` header. |
| `HYPERRAG_MAX_QPS` | `float` | `3.0` | `10.0` | In-process rate limit per client IP address. |
| `HYPERRAG_ALLOWED_ORIGINS` | `str` | `*` | `http://localhost:5173` | Allowed CORS origins for browser security. |

---

## 7. Key Rotation & Backoff Rules

The internal `KeyPool` in `hyperrag/key_pool.py` automatically manages API keys:
- **Round-Robin Selection**: Requests rotate through provided keys to distribute rate limits.
- **HTTP 429 Handling**: Keys that encounter rate limiting are temporarily placed in cooldown.
- **HTTP 401 Handling**: Keys that return unauthorized are flagged as permanently invalid.
- **Concurrency Safety**: Thread-safe key leasing and return mechanisms.

---

## 8. Configuration Validation (`validate_config()`)

At application startup, `my_config.validate_config()` checks the following invariants:
1. `OPENROUTER_API_KEYS` is non-empty.
2. `EMB_API_KEYS` is non-empty.
3. `EMB_DIM` is strictly `1024`.
4. `ADAPTIVE_CORE_THRESHOLD` is between `0` and `100`.
5. `ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD` is between `0` and `100`.
6. `ADAPTIVE_VALIDATION_THRESHOLD` is between `0` and `100`.
7. Validation weights sum to $> 0$.

If any check fails, an error message lists the missing variables without printing secret keys.
