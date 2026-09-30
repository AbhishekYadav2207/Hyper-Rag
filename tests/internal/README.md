# Internal Diagnostics

This directory contains developer-oriented diagnostic and smoke test scripts that verify live external provider integrations.

## Difference from Public Test Suite (`tests/unit/`)

| Suite | Location | Requirements | Live API Calls? | Run Automatically? |
| :--- | :--- | :--- | :---: | :---: |
| **Maintained Unit Suite** | `tests/unit/` | None (Mocked) | No | **Yes** (`pytest tests/unit`) |
| **Internal Diagnostics** | `tests/internal/` | Active `.env` keys + Internet | **Yes** | **No** (Run manually) |

## Diagnostic Scripts

### 1. OpenRouter Primary LLM Live Connectivity
Verifies that the configured OpenRouter API key pool, base URL, and chat model respond successfully:
```bash
python tests/internal/test_openrouter.py
```

### 2. Mistral Embeddings Live Connectivity
Verifies that the configured Mistral embedding API key, base URL, model, and 1024-dimension vector output respond successfully:
```bash
python tests/internal/test_embedding.py
```
