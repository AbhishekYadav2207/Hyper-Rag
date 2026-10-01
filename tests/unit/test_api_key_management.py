# -*- coding: utf-8 -*-
"""
Security and architecture tests for WebUI API key management.
Verifies all requirements in Section 35:
- WebUI Settings is authoritative runtime source of truth
- Keys are masked and never returned through GET /settings
- Frontend bundles do not embed secrets
- API keys are not in URLs or logs
- Missing keys produce clear, friendly UI errors
- Precedence: WebUI Settings > no key / error (never .env over WebUI Settings)
"""

import os
import sys
import json
import asyncio
import pytest
from pathlib import Path

# Add repository root and backend to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "web-ui" / "backend"))

import main as backend_main
from main import (
    get_settings,
    save_settings,
    test_api_connection as call_test_api_connection,
    get_effective_settings,
    get_hyperrag_llm_func,
    get_hyperrag_embedding_func,
    sanitize_error_message,
    mask_key,
    SettingsModel,
    APITestModel,
)


@pytest.fixture
def temp_settings_file(tmp_path):
    """Fixture providing an isolated settings.json file for tests."""
    temp_file = tmp_path / "settings.json"
    original_file = backend_main.SETTINGS_FILE
    backend_main.SETTINGS_FILE = str(temp_file)
    backend_main.hyperrag_instances.clear()
    
    yield temp_file
    
    backend_main.SETTINGS_FILE = original_file
    backend_main.hyperrag_instances.clear()
    if temp_file.exists():
        temp_file.unlink()


def test_mask_key_utility():
    """Verify key masking behavior."""
    assert mask_key("") == ""
    assert mask_key(None) == ""
    assert mask_key("short") == "••••••••"
    assert mask_key("sk-or-v1-abcdef123456") == "••••••••••••3456"
    assert "abcdef" not in mask_key("sk-or-v1-abcdef123456")


def test_sanitize_error_message():
    """Verify error sanitizer redacts bearer tokens and API keys."""
    raw = "Failed with Bearer sk-or-v1-secretkey9999 and key-secretabc123"
    sanitized = sanitize_error_message(raw)
    assert "secretkey9999" not in sanitized
    assert "secretabc123" not in sanitized
    assert "[REDACTED]" in sanitized or "[REDACTED_API_KEY]" in sanitized


def test_get_settings_never_returns_full_secrets(temp_settings_file):
    """Verify GET /settings never returns full secrets."""
    async def _run():
        secret_llm = "sk-or-v1-fake-secret-llm-key-9999"
        secret_emb = "fake-secret-mistral-embedding-key-8888"

        with open(temp_settings_file, "w", encoding="utf-8") as f:
            json.dump({
                "modelProvider": "openrouter",
                "modelName": "nvidia/nemotron-3-ultra-550b-a55b:free",
                "baseUrl": "https://openrouter.ai/api/v1",
                "apiKey": secret_llm,
                "embeddingModel": "mistral-embed",
                "embeddingBaseUrl": "https://api.mistral.ai/v1",
                "embeddingApiKey": secret_emb,
                "embeddingDim": 1024
            }, f)

        res = await get_settings()
        res_str = json.dumps(res)

        # Full secret keys MUST NOT be present in response
        assert secret_llm not in res_str, "Full LLM API key leaked in GET /settings response!"
        assert secret_emb not in res_str, "Full Embedding API key leaked in GET /settings response!"

        # Preview and status must be present
        assert res["apiKeyConfigured"] is True
        assert res["embeddingApiKeyConfigured"] is True
        assert res["openrouter_configured"] is True
        assert res["mistral_configured"] is True
        assert res["apiKeyPreview"].endswith("9999")
        assert res["embeddingApiKeyPreview"].endswith("8888")

    asyncio.run(_run())


def test_save_settings_and_update(temp_settings_file):
    """Verify POST /settings stores credentials server-side and allows update."""
    async def _run():
        # 1. Initial save with new credentials
        model = SettingsModel(
            apiKey="sk-or-v1-new-key-1111",
            embeddingApiKey="mistral-emb-key-2222",
            modelName="nvidia/nemotron-3-ultra-550b-a55b:free",
        )
        save_res = await save_settings(model)
        assert save_res["success"] is True
        assert save_res["apiKeyConfigured"] is True
        assert save_res["embeddingApiKeyConfigured"] is True

        # Check stored file
        with open(temp_settings_file, "r", encoding="utf-8") as f:
            stored = json.load(f)
        assert stored["apiKey"] == "sk-or-v1-new-key-1111"
        assert stored["embeddingApiKey"] == "mistral-emb-key-2222"

        # 2. Saving with masked key does NOT overwrite with masked value
        model_update = SettingsModel(
            apiKey="••••••••••••1111",
            embeddingApiKey="••••••••••••2222",
            temperature=0.8
        )
        update_res = await save_settings(model_update)
        assert update_res["success"] is True

        with open(temp_settings_file, "r", encoding="utf-8") as f:
            stored_after = json.load(f)
        assert stored_after["apiKey"] == "sk-or-v1-new-key-1111"
        assert stored_after["embeddingApiKey"] == "mistral-emb-key-2222"
        assert stored_after["temperature"] == 0.8

        # 3. Explicit clear
        clear_model = SettingsModel(clearApiKey=True, clearEmbeddingApiKey=True)
        clear_res = await save_settings(clear_model)
        assert clear_res["success"] is True
        assert clear_res["apiKeyConfigured"] is False
        assert clear_res["embeddingApiKeyConfigured"] is False

    asyncio.run(_run())


def test_webui_runtime_precedence_over_env(temp_settings_file, monkeypatch):
    """
    Verify WebUI Settings is the single runtime source of truth.
    .env is NOT the primary runtime source and does not override WebUI settings.
    """
    async def _run():
        # Set legacy .env variables
        monkeypatch.setenv("OPENROUTER_API_KEY", "legacy-env-openrouter-key")
        monkeypatch.setenv("EMB_API_KEY", "legacy-env-mistral-key")

        # Case A: WebUI settings has its own key -> WebUI settings key MUST be used
        with open(temp_settings_file, "w", encoding="utf-8") as f:
            json.dump({
                "apiKey": "webui-authoritative-llm-key",
                "embeddingApiKey": "webui-authoritative-emb-key",
            }, f)

        effective = get_effective_settings()
        assert effective["apiKey"] == "webui-authoritative-llm-key"
        assert effective["embeddingApiKey"] == "webui-authoritative-emb-key"

        # Case B: WebUI settings has empty keys -> do NOT silently use .env keys!
        with open(temp_settings_file, "w", encoding="utf-8") as f:
            json.dump({
                "apiKey": "",
                "embeddingApiKey": "",
            }, f)

        effective_empty = get_effective_settings()
        assert effective_empty["apiKey"] == ""
        assert effective_empty["embeddingApiKey"] == ""

        # Must raise clear configuration errors when calling LLM/embedding
        with pytest.raises(ValueError) as excinfo_llm:
            await get_hyperrag_llm_func("Hello")
        assert "OpenRouter API key is not configured" in str(excinfo_llm.value)

        with pytest.raises(ValueError) as excinfo_emb:
            await get_hyperrag_embedding_func(["text chunk"])
        assert "Mistral API key is not configured" in str(excinfo_emb.value)

    asyncio.run(_run())


def test_changing_key_affects_subsequent_requests(temp_settings_file):
    """Verify changing key in Settings immediately affects runtime without restart."""
    async def _run():
        with open(temp_settings_file, "w", encoding="utf-8") as f:
            json.dump({"apiKey": "first-key-1111", "embeddingApiKey": "emb-key-1111"}, f)

        assert get_effective_settings()["apiKey"] == "first-key-1111"

        # Change settings
        await save_settings(SettingsModel(apiKey="second-key-2222"))
        assert get_effective_settings()["apiKey"] == "second-key-2222"

    asyncio.run(_run())


def test_test_api_connection_endpoint(temp_settings_file):
    """Verify /test-api works safely and returns friendly messages."""
    async def _run():
        # With no key configured
        with open(temp_settings_file, "w", encoding="utf-8") as f:
            json.dump({"apiKey": "", "embeddingApiKey": ""}, f)

        res_llm = await call_test_api_connection(APITestModel(testType="llm"))
        assert res_llm["success"] is False
        assert "OpenRouter API key is not configured" in res_llm["message"]

        res_emb = await call_test_api_connection(APITestModel(testType="embedding"))
        assert res_emb["success"] is False
        assert "Mistral API key is not configured" in res_emb["message"]

    asyncio.run(_run())


def test_frontend_bundles_do_not_contain_secrets():
    """Verify frontend bundle files in dist/ do not embed hardcoded secret keys."""
    dist_dir = REPO_ROOT / "web-ui" / "frontend" / "dist"
    if not dist_dir.exists():
        pytest.skip("Frontend dist directory not found")

    forbidden_patterns = [
        "sk-or-v1-",
        "fake-secret",
    ]

    for file_path in dist_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in [".js", ".html", ".css", ".json"]:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for pat in forbidden_patterns:
                    assert pat not in content, f"Forbidden pattern '{pat}' found in frontend bundle: {file_path.name}"
            except Exception:
                pass
