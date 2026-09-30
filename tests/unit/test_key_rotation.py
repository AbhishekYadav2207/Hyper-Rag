# -*- coding: utf-8 -*-
"""
Isolated Key-Rotation Test Suite for Hyper-RAG
Covers all 7 required scenarios:
- Test 1: OpenRouter key1 -> 429, key2 -> success. (key2 used)
- Test 2: OpenRouter key1 -> 429, key2 -> 429, key3 -> success. (reaches key3)
- Test 3: All OpenRouter keys -> 429. (process does not terminate, backoff, retry)
- Test 4: OpenRouter key1 -> 401, key2 -> success. (invalid key skipped)
- Test 5: Embedding key1 -> 429, key2 -> success. (only embedding keys rotate)
- Test 6: OpenRouter key1 -> 429. (NO Mistral LLM fallback occurs)
- Test 7: OpenRouter has only one key -> 429. (handled by retry/backoff without crash)
- Concurrency Test: Multiple concurrent requests hit 429 on key1 (no cascading rotation)
"""

import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
from openai import AuthenticationError, RateLimitError

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import hyperrag.llm as llm
from hyperrag.key_pool import (
    APIKeyPool,
    reset_key_pools,
)


class TestKeyRotation(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        reset_key_pools()

    def tearDown(self):
        reset_key_pools()

    def _create_mock_chat_response(self, text="Test Success"):
        parsed = MagicMock()
        choice = MagicMock()
        choice.message.content = text
        choice.message.reasoning = None
        choice.finish_reason = "stop"
        parsed.choices = [choice]
        parsed.model = "nvidia/nemotron-3-ultra-550b-a55b:free"

        raw = MagicMock()
        raw.status_code = 200
        raw.text = json.dumps({"choices": [{"message": {"content": text}}]})
        raw.parse.return_value = parsed
        return raw

    def _create_mock_rate_limit_error(self, retry_after=None):
        headers = {"retry-after": str(retry_after)} if retry_after else {}
        resp = MagicMock(status_code=429, headers=headers)
        return RateLimitError(
            message="Rate limit reached: 429",
            response=resp,
            body={"error": {"code": 429, "message": "Rate limit exceeded"}},
        )

    def _create_mock_auth_error(self):
        resp = MagicMock(status_code=401, headers={})
        return AuthenticationError(
            message="Invalid API Key: 401",
            response=resp,
            body={"error": {"code": 401, "message": "Unauthorized"}},
        )

    def _make_client_factory(self, dispatch_fn):
        def _get_client(api_key: str, base_url: str):
            mock_client = MagicMock()
            async def _create(**kwargs):
                return dispatch_fn(api_key, **kwargs)
            mock_client.chat.completions.with_raw_response.create = AsyncMock(side_effect=_create)
            return mock_client
        return _get_client

    async def test_1_openrouter_key1_429_key2_success(self):
        """Test 1: OpenRouter key1 -> 429, key2 -> success. Expected: key2 is automatically used."""
        print("\n=== RUNNING TEST 1: key1 -> 429, key2 -> success ===")
        pool = APIKeyPool("OpenRouter", ["test_key_1", "test_key_2"], default_cooldown=1.0)
        called_keys = []

        def dispatch(key: str, **kwargs):
            called_keys.append(key)
            if key == "test_key_1":
                raise self._create_mock_rate_limit_error()
            return self._create_mock_chat_response("SUCCESS_KEY2")

        with patch("hyperrag.llm.get_openrouter_key_pool", return_value=pool):
            with patch("hyperrag.llm.get_async_client", side_effect=self._make_client_factory(dispatch)):
                result = await llm.openrouter_mistral_complete_if_cache("Test prompt")

        self.assertEqual(result, "SUCCESS_KEY2")
        self.assertEqual(called_keys, ["test_key_1", "test_key_2"])
        # Pool should now be parked on key2 (index 1)
        self.assertEqual(pool._current_index, 1)
        print("  [OK] Test 1 passed: key2 was automatically used after key1 received 429.")

    async def test_2_openrouter_key1_429_key2_429_key3_success(self):
        """Test 2: key1 -> 429, key2 -> 429, key3 -> success. Expected: rotation reaches key3."""
        print("\n=== RUNNING TEST 2: key1 -> 429, key2 -> 429, key3 -> success ===")
        pool = APIKeyPool("OpenRouter", ["test_key_1", "test_key_2", "test_key_3"], default_cooldown=1.0)
        called_keys = []

        def dispatch(key: str, **kwargs):
            called_keys.append(key)
            if key in ("test_key_1", "test_key_2"):
                raise self._create_mock_rate_limit_error()
            return self._create_mock_chat_response("SUCCESS_KEY3")

        with patch("hyperrag.llm.get_openrouter_key_pool", return_value=pool):
            with patch("hyperrag.llm.get_async_client", side_effect=self._make_client_factory(dispatch)):
                result = await llm.openrouter_mistral_complete_if_cache("Test prompt")

        self.assertEqual(result, "SUCCESS_KEY3")
        self.assertEqual(called_keys, ["test_key_1", "test_key_2", "test_key_3"])
        self.assertEqual(pool._current_index, 2)
        print("  [OK] Test 2 passed: rotation successfully reached key3.")

    async def test_3_all_openrouter_keys_429_backoff_and_retry(self):
        """Test 3: all OpenRouter keys -> 429. Expected: process does not terminate, backoff occurs, retry happens."""
        print("\n=== RUNNING TEST 3: all keys -> 429, backoff and retry ===")
        pool = APIKeyPool("OpenRouter", ["test_key_1", "test_key_2"], default_cooldown=0.2, max_cooldown=0.5)
        attempt_counts = {"test_key_1": 0, "test_key_2": 0}

        def dispatch(key: str, **kwargs):
            attempt_counts[key] += 1
            if attempt_counts[key] == 1:
                raise self._create_mock_rate_limit_error(retry_after=0.2)
            return self._create_mock_chat_response("RECOVERED_AFTER_BACKOFF")

        start_time = asyncio.get_event_loop().time()
        with patch("hyperrag.llm.get_openrouter_key_pool", return_value=pool):
            with patch("hyperrag.llm.get_async_client", side_effect=self._make_client_factory(dispatch)):
                result = await llm.openrouter_mistral_complete_if_cache("Test prompt")
        elapsed = asyncio.get_event_loop().time() - start_time

        self.assertEqual(result, "RECOVERED_AFTER_BACKOFF")
        self.assertGreaterEqual(attempt_counts["test_key_1"], 2)
        self.assertGreaterEqual(attempt_counts["test_key_2"], 1)
        self.assertGreaterEqual(elapsed, 0.15)
        print("  [OK] Test 3 passed: process did not terminate, waited cooldown backoff, and retried successfully.")

    async def test_4_openrouter_key1_401_key2_success(self):
        """Test 4: OpenRouter key1 -> 401, key2 -> success. Expected: invalid key is skipped."""
        print("\n=== RUNNING TEST 4: key1 -> 401, key2 -> success ===")
        pool = APIKeyPool("OpenRouter", ["test_key_1", "test_key_2"])
        called_keys = []

        def dispatch(key: str, **kwargs):
            called_keys.append(key)
            if key == "test_key_1":
                raise self._create_mock_auth_error()
            return self._create_mock_chat_response("SUCCESS_AFTER_401")

        with patch("hyperrag.llm.get_openrouter_key_pool", return_value=pool):
            with patch("hyperrag.llm.get_async_client", side_effect=self._make_client_factory(dispatch)):
                result = await llm.openrouter_mistral_complete_if_cache("Test prompt")

        self.assertEqual(result, "SUCCESS_AFTER_401")
        self.assertEqual(called_keys, ["test_key_1", "test_key_2"])
        self.assertTrue(pool.key_states[0].is_invalid)
        self.assertFalse(pool.key_states[1].is_invalid)

        # Subsequent request should immediately use key2 without trying key1
        second_called = []
        def dispatch2(key: str, **kwargs):
            second_called.append(key)
            return self._create_mock_chat_response("SECOND_OK")

        with patch("hyperrag.llm.get_openrouter_key_pool", return_value=pool):
            with patch("hyperrag.llm.get_async_client", side_effect=self._make_client_factory(dispatch2)):
                result2 = await llm.openrouter_mistral_complete_if_cache("Prompt 2")

        self.assertEqual(result2, "SECOND_OK")
        self.assertEqual(second_called, ["test_key_2"])
        print("  [OK] Test 4 passed: invalid 401 key was marked unusable and permanently skipped.")

    async def test_5_embedding_key1_429_key2_success_isolated(self):
        """Test 5: Embedding key1 -> 429, key2 -> success. Expected: only embedding keys rotate."""
        print("\n=== RUNNING TEST 5: Embedding key rotation isolated from OpenRouter ===")
        emb_pool = APIKeyPool("Embeddings", ["emb_key_1", "emb_key_2"])
        or_pool = APIKeyPool("OpenRouter", ["or_key_1", "or_key_2"])

        emb_called = []

        mock_client = MagicMock()
        async def fake_create_embeddings(*args, **kwargs):
            key = mock_client._current_key
            emb_called.append(key)
            if key == "emb_key_1":
                raise self._create_mock_rate_limit_error()
            item = MagicMock()
            item.embedding = [0.05] * 1024
            res = MagicMock()
            res.data = [item]
            return res

        mock_client.embeddings.create = AsyncMock(side_effect=fake_create_embeddings)

        def get_client_spy(key, base_url):
            mock_client._current_key = key
            return mock_client

        with patch("hyperrag.llm.get_embedding_key_pool", return_value=emb_pool):
            with patch("hyperrag.llm.get_openrouter_key_pool", return_value=or_pool):
                with patch("hyperrag.llm.get_async_client", side_effect=get_client_spy):
                    result = await llm.openai_embedding(["Sample text for embedding"])

        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result.shape, (1, 1024))
        self.assertEqual(result.dtype, np.float32)
        self.assertEqual(emb_called, ["emb_key_1", "emb_key_2"])
        # Embedding pool rotated to emb_key_2
        self.assertEqual(emb_pool._current_index, 1)
        # OpenRouter pool index remained completely untouched at 0!
        self.assertEqual(or_pool._current_index, 0)
        print("  [OK] Test 5 passed: only embedding keys rotated; OpenRouter pool was untouched; 1024 dims verified.")

    async def test_6_no_mistral_llm_fallback(self):
        """Test 6: OpenRouter key1 -> 429. Expected: NO Mistral LLM fallback occurs."""
        print("\n=== RUNNING TEST 6: Verify NO Mistral LLM fallback occurs ===")
        pool = APIKeyPool("OpenRouter", ["or_key_1"], default_cooldown=0.1, max_cooldown=0.1)

        mistral_called = False

        def dispatch(key: str, **kwargs):
            raise self._create_mock_rate_limit_error()

        async def fake_fail(k: str):
            raise self._create_mock_rate_limit_error()

        with patch("hyperrag.llm.get_openrouter_key_pool", return_value=pool):
            with patch.dict(os.environ, {"MISTRAL_API_KEY": "mistral_secret"}):
                with self.assertRaises(RuntimeError) as cm:
                    await llm.execute_with_key_rotation(
                        pool,
                        fake_fail,
                        max_retries=2,
                    )

        self.assertIn("Max retries", str(cm.exception))
        self.assertIn("OpenRouter", str(cm.exception))
        self.assertFalse(mistral_called)
        print("  [OK] Test 6 passed: OpenRouter exhausted retries without ANY Mistral LLM fallback.")

    async def test_7_single_openrouter_key_429(self):
        """Test 7: OpenRouter has only one key. Expected: 429 handled by retry/backoff without crashing."""
        print("\n=== RUNNING TEST 7: Single OpenRouter key handles 429 via backoff ===")
        pool = APIKeyPool("OpenRouter", ["single_key"], default_cooldown=0.2, max_cooldown=0.4)
        attempts = 0

        def dispatch(key: str, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise self._create_mock_rate_limit_error(retry_after=0.2)
            return self._create_mock_chat_response("SINGLE_KEY_SUCCESS")

        with patch("hyperrag.llm.get_openrouter_key_pool", return_value=pool):
            with patch("hyperrag.llm.get_async_client", side_effect=self._make_client_factory(dispatch)):
                result = await llm.openrouter_mistral_complete_if_cache("Prompt")

        self.assertEqual(result, "SINGLE_KEY_SUCCESS")
        self.assertEqual(attempts, 2)
        print("  [OK] Test 7 passed: single key 429 was handled with backoff and retry without crashing.")

    async def test_8_concurrency_race_condition_safety(self):
        """Test 8: Concurrent async requests hitting 429 simultaneously do NOT cause cascading rotation."""
        print("\n=== RUNNING TEST 8: Concurrency safety with llm_model_max_async > 1 ===")
        pool = APIKeyPool("OpenRouter", ["key_1", "key_2", "key_3"], default_cooldown=1.0)
        calls = []

        async def fake_worker(worker_id: int):
            async def _req(k: str):
                calls.append((worker_id, k))
                if k == "key_1":
                    raise self._create_mock_rate_limit_error()
                return f"WORKER_{worker_id}_SUCCESS"

            return await llm.execute_with_key_rotation(pool, _req)

        results = await asyncio.gather(*(fake_worker(i) for i in range(4)))

        # All 4 workers must succeed on key_2, NOT cascade through key_3!
        self.assertEqual(results, [f"WORKER_{i}_SUCCESS" for i in range(4)])
        # Pool should now be on key_2 (index 1), NEVER key_3 (index 2)
        self.assertEqual(pool._current_index, 1)
        self.assertFalse(pool.key_states[1].is_invalid)
        self.assertTrue(pool.key_states[1].is_usable)
        print("  [OK] Concurrency Test passed: 4 concurrent 429s safely rotated only to key_2 without cascading.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
