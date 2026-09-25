# -*- coding: utf-8 -*-
"""
Reusable API Key Pool and Request Runner
Provides thread-safe and async-safe API key rotation with cooldown, exponential backoff,
jitter, and Retry-After header parsing for OpenRouter LLM and Mistral Embeddings.
"""

import asyncio
import logging
import random
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from openai import (
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    OpenAI,
    AsyncOpenAI,
    PermissionDeniedError,
    RateLimitError,
)

logger = logging.getLogger("hyperrag.key_pool")


class KeyState:
    """Represents the runtime state of a single API key."""

    def __init__(self, key: str, index: int, total: int):
        self.key: str = key
        self.index: int = index  # 0-indexed
        self.total: int = total
        self.display_name: str = f"key {index + 1}/{total}"
        self.is_invalid: bool = False  # Set to True on 401
        self.rate_limited_until: float = 0.0  # Monotonic timestamp
        self.failure_count: int = 0
        self.success_count: int = 0

    @property
    def is_usable(self) -> bool:
        """Returns True if the key is not invalid and cooldown has expired."""
        return (not self.is_invalid) and (time.monotonic() >= self.rate_limited_until)

    @property
    def remaining_cooldown(self) -> float:
        """Returns remaining cooldown in seconds, or 0.0 if ready."""
        return max(0.0, self.rate_limited_until - time.monotonic())


class APIKeyPool:
    """
    Thread-safe and async-safe pool of API keys with automatic rotation,
    rate limit tracking, invalidation, and cooldown recovery.
    """

    def __init__(
        self,
        name: str,
        keys: List[str],
        default_cooldown: float = 2.0,
        max_cooldown: float = 60.0,
    ):
        self.name = name
        cleaned_keys = [k.strip() for k in keys if k and k.strip()]
        if not cleaned_keys:
            raise ValueError(
                f"[{name}] APIKeyPool requires at least one non-empty API key."
            )

        self.keys = cleaned_keys
        self.total = len(cleaned_keys)
        self.key_states: List[KeyState] = [
            KeyState(k, i, self.total) for i, k in enumerate(cleaned_keys)
        ]
        self._key_map: Dict[str, KeyState] = {
            ks.key: ks for ks in self.key_states
        }
        self._current_index: int = 0
        self._lock = threading.RLock()
        self.default_cooldown = default_cooldown
        self.max_cooldown = max_cooldown

    def get_current_key(self) -> KeyState:
        """
        Returns the currently active usable key, or rotates to the next usable key.
        If all keys are rate-limited, returns the key with the earliest cooldown expiration.
        Raises RuntimeError if all keys are marked permanently invalid (401).
        """
        with self._lock:
            cur = self.key_states[self._current_index]
            if cur.is_usable:
                return cur

            # Search forward for any usable key
            for offset in range(1, self.total):
                idx = (self._current_index + offset) % self.total
                candidate = self.key_states[idx]
                if candidate.is_usable:
                    self._current_index = idx
                    return candidate

            # Check if all keys are invalid
            valid_keys = [ks for ks in self.key_states if not ks.is_invalid]
            if not valid_keys:
                raise RuntimeError(
                    f"[{self.name}] All configured API keys are invalid/unusable."
                )

            # Return key that recovers earliest
            earliest = min(valid_keys, key=lambda ks: ks.rate_limited_until)
            self._current_index = earliest.index
            return earliest

    async def acquire_usable_key(self) -> KeyState:
        """
        Asynchronously acquires a usable key. If all keys are rate-limited,
        waits for the earliest cooldown to expire before returning.
        """
        while True:
            with self._lock:
                ks = self.get_current_key()
                if ks.is_usable:
                    return ks
                remaining = ks.remaining_cooldown
                pool_name = self.name

            # Wait for cooldown
            wait_time = max(0.1, remaining)
            # Add small jitter
            wait_time += random.uniform(0.05, 0.25)
            wait_sec = max(1, int(round(wait_time)))
            log_msg = f"[{pool_name}] All keys are rate-limited. Waiting {wait_sec}s before retry."
            print(log_msg, flush=True)
            logger.warning(log_msg)
            await asyncio.sleep(wait_time)

    def acquire_usable_key_sync(self) -> KeyState:
        """
        Synchronously acquires a usable key. If all keys are rate-limited,
        sleeps for the earliest cooldown to expire before returning.
        """
        while True:
            with self._lock:
                ks = self.get_current_key()
                if ks.is_usable:
                    return ks
                remaining = ks.remaining_cooldown
                pool_name = self.name

            wait_time = max(0.1, remaining)
            wait_time += random.uniform(0.05, 0.25)
            wait_sec = max(1, int(round(wait_time)))
            log_msg = f"[{pool_name}] All keys are rate-limited. Waiting {wait_sec}s before retry."
            print(log_msg, flush=True)
            logger.warning(log_msg)
            time.sleep(wait_time)

    def mark_rate_limited(
        self, failed_key: str, retry_after: Optional[float] = None
    ) -> KeyState:
        """
        Marks the key as temporarily rate-limited and rotates to the next available key.
        Thread-safe: Prevents race conditions when multiple concurrent requests
        simultaneously receive 429 for the same key.
        """
        with self._lock:
            ks = self._key_map.get(failed_key)
            if ks is None:
                return self.get_current_key()

            now = time.monotonic()
            # If already marked as rate-limited recently by a concurrent request,
            # do not trigger another duplicate rotation or reset cooldown.
            already_marked = ks.rate_limited_until > now

            if not already_marked:
                if retry_after is not None and retry_after > 0:
                    cooldown = min(self.max_cooldown, float(retry_after))
                else:
                    base = min(
                        self.max_cooldown,
                        (2 ** ks.failure_count) * self.default_cooldown,
                    )
                    jitter = random.uniform(0.2, 1.0)
                    cooldown = min(self.max_cooldown, base + jitter)

                ks.failure_count += 1
                ks.rate_limited_until = now + cooldown

                log_msg = f"[{self.name}] Rate limit on {ks.display_name}. Rotating."
                print(log_msg, flush=True)
                logger.warning(log_msg)

                # Rotate current index to next usable key if available
                if self.total > 1:
                    rotated = False
                    for offset in range(1, self.total):
                        idx = (self._current_index + offset) % self.total
                        if self.key_states[idx].is_usable:
                            self._current_index = idx
                            rotated = True
                            break
                    if not rotated:
                        self._current_index = (self._current_index + 1) % self.total

            return self.get_current_key()

    def mark_invalid(self, failed_key: str) -> KeyState:
        """
        Marks a key permanently invalid (e.g. HTTP 401) and rotates away.
        """
        with self._lock:
            ks = self._key_map.get(failed_key)
            if ks is not None and not ks.is_invalid:
                ks.is_invalid = True
                log_msg = f"[{self.name}] Key {ks.display_name} is invalid (401). Marking unusable and rotating."
                print(log_msg, flush=True)
                logger.error(log_msg)

                # Advance to next usable key
                for offset in range(1, self.total):
                    idx = (self._current_index + offset) % self.total
                    if self.key_states[idx].is_usable:
                        self._current_index = idx
                        break

            return self.get_current_key()

    def mark_success(self, successful_key: str) -> None:
        """
        Marks key request as successful, resets failure count, and preserves current position.
        """
        with self._lock:
            ks = self._key_map.get(successful_key)
            if ks is not None:
                ks.failure_count = 0
                ks.success_count += 1
                self._current_index = ks.index

    def reset(self) -> None:
        """Resets all key states to clean initial state (for testing)."""
        with self._lock:
            self._current_index = 0
            for ks in self.key_states:
                ks.is_invalid = False
                ks.rate_limited_until = 0.0
                ks.failure_count = 0
                ks.success_count = 0


# ============================================================
# ERROR DETECTION & RETRY-AFTER PARSING HELPERS
# ============================================================


def is_rate_limit_error(e: Exception) -> bool:
    """Detect if an exception corresponds to HTTP 429 / Rate Limit."""
    if isinstance(e, RateLimitError):
        return True
    status = getattr(e, "status_code", None)
    if status == 429:
        return True
    msg = str(e).lower()
    return "429" in msg or "rate limit" in msg or "too many requests" in msg


def is_auth_error(e: Exception) -> bool:
    """Detect if an exception corresponds to HTTP 401 / Authentication Error."""
    if isinstance(e, AuthenticationError):
        return True
    status = getattr(e, "status_code", None)
    if status == 401:
        return True
    msg = str(e).lower()
    return "401" in msg or "unauthorized" in msg or "invalid api key" in msg


def is_permission_error(e: Exception) -> bool:
    """Detect if an exception corresponds to HTTP 403 / Access Denied."""
    if isinstance(e, PermissionDeniedError):
        return True
    status = getattr(e, "status_code", None)
    if status == 403:
        return True
    msg = str(e).lower()
    return "403" in msg or "forbidden" in msg or "permission denied" in msg


def is_bad_request_error(e: Exception) -> bool:
    """Detect if an exception corresponds to HTTP 400 / Bad Request."""
    if isinstance(e, BadRequestError):
        return True
    status = getattr(e, "status_code", None)
    if status == 400:
        return True
    msg = str(e).lower()
    return "400" in msg and "bad request" in msg


def is_transient_error(e: Exception) -> bool:
    """Detect transient network/server errors (5xx, timeouts, connection issues)."""
    if isinstance(
        e, (APIConnectionError, InternalServerError, TimeoutError, asyncio.TimeoutError)
    ):
        return True
    # Catch openai.Timeout if present
    name = type(e).__name__
    if "timeout" in name.lower() or "connection" in name.lower():
        return True
    status = getattr(e, "status_code", None)
    if status is not None and 500 <= status < 600:
        return True
    return False


def parse_retry_after(e: Exception) -> Optional[float]:
    """Extract Retry-After header or seconds from error message if present."""
    response = getattr(e, "response", None)
    if response is not None:
        headers = getattr(response, "headers", None)
        if headers and hasattr(headers, "get"):
            for h in ["retry-after", "Retry-After", "x-ratelimit-reset"]:
                val = headers.get(h)
                if val:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        pass

    # Inspect message string
    msg = str(e)
    match = re.search(
        r"(?:retry after|try again in|wait)\s*([0-9]+(?:\.[0-9]+)?)\s*s",
        msg,
        re.I,
    )
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            pass

    return None


# ============================================================
# CLIENT POOLING / REUSE (max_retries=0)
# ============================================================

_async_client_cache: Dict[Tuple[str, str], AsyncOpenAI] = {}
_sync_client_cache: Dict[Tuple[str, str], OpenAI] = {}
_client_cache_lock = threading.Lock()


def get_async_client(api_key: str, base_url: str) -> AsyncOpenAI:
    """Returns or creates a cached AsyncOpenAI client with max_retries=0."""
    key = (api_key, base_url)
    with _client_cache_lock:
        if key not in _async_client_cache:
            _async_client_cache[key] = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                max_retries=0,
            )
        return _async_client_cache[key]


def get_sync_client(api_key: str, base_url: str) -> OpenAI:
    """Returns or creates a cached OpenAI sync client with max_retries=0."""
    key = (api_key, base_url)
    with _client_cache_lock:
        if key not in _sync_client_cache:
            _sync_client_cache[key] = OpenAI(
                api_key=api_key,
                base_url=base_url,
                max_retries=0,
            )
        return _sync_client_cache[key]


# ============================================================
# REQUEST EXECUTION RUNNERS WITH ROTATION & BACKOFF
# ============================================================


async def execute_with_key_rotation(
    pool: APIKeyPool,
    request_func: Callable[[str], Any],
    max_retries: Optional[int] = None,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> Any:
    """
    Asynchronously executes request_func(api_key) with automatic key rotation,
    exponential backoff with jitter on 429 / 5xx / timeouts / connection errors,
    and invalidation on 401. Never falls back to any secondary provider.
    """
    retries_limit = max_retries or max(10, pool.total * 3)
    attempt = 0
    last_error = None

    while attempt < retries_limit:
        attempt += 1
        ks = await pool.acquire_usable_key()
        active_key = ks.key

        log_msg = f"[{pool.name}] Using {ks.display_name}"
        print(log_msg, flush=True)
        logger.info(log_msg)

        try:
            result = await request_func(active_key)
            pool.mark_success(active_key)
            success_msg = f"[{pool.name}] Request successful."
            print(success_msg, flush=True)
            logger.info(success_msg)
            return result
        except Exception as e:
            last_error = e

            if is_rate_limit_error(e):
                retry_after = parse_retry_after(e)
                pool.mark_rate_limited(active_key, retry_after)
                continue

            if is_auth_error(e):
                pool.mark_invalid(active_key)
                continue

            if is_permission_error(e):
                # Check if other valid keys exist
                valid_left = [
                    k
                    for k in pool.key_states
                    if not k.is_invalid and k.key != active_key
                ]
                if valid_left:
                    pool.mark_invalid(active_key)
                    continue
                # Authorization issue with no alternate keys: do not retry indefinitely
                raise

            if is_bad_request_error(e):
                # 400 Bad Request: request itself is invalid, do not rotate keys
                raise

            if is_transient_error(e):
                delay = (
                    min(max_delay, (2 ** (attempt - 1)) * base_delay)
                    + random.uniform(0.1, 0.5)
                )
                logger.warning(
                    f"[{pool.name}] Transient error ({type(e).__name__}): {e}. Waiting {delay:.1f}s before retry."
                )
                await asyncio.sleep(delay)
                continue

            # Any unhandled exception: re-raise
            raise

    raise RuntimeError(
        f"[{pool.name}] Max retries ({retries_limit}) exceeded without success. Last error: {last_error}"
    ) from last_error


def execute_with_key_rotation_sync(
    pool: APIKeyPool,
    request_func: Callable[[str], Any],
    max_retries: Optional[int] = None,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> Any:
    """
    Synchronously executes request_func(api_key) with automatic key rotation.
    """
    retries_limit = max_retries or max(10, pool.total * 3)
    attempt = 0
    last_error = None

    while attempt < retries_limit:
        attempt += 1
        ks = pool.acquire_usable_key_sync()
        active_key = ks.key

        log_msg = f"[{pool.name}] Using {ks.display_name}"
        print(log_msg, flush=True)
        logger.info(log_msg)

        try:
            result = request_func(active_key)
            pool.mark_success(active_key)
            success_msg = f"[{pool.name}] Request successful."
            print(success_msg, flush=True)
            logger.info(success_msg)
            return result
        except Exception as e:
            last_error = e

            if is_rate_limit_error(e):
                retry_after = parse_retry_after(e)
                pool.mark_rate_limited(active_key, retry_after)
                continue

            if is_auth_error(e):
                pool.mark_invalid(active_key)
                continue

            if is_permission_error(e):
                valid_left = [
                    k
                    for k in pool.key_states
                    if not k.is_invalid and k.key != active_key
                ]
                if valid_left:
                    pool.mark_invalid(active_key)
                    continue
                raise

            if is_bad_request_error(e):
                raise

            if is_transient_error(e):
                delay = (
                    min(max_delay, (2 ** (attempt - 1)) * base_delay)
                    + random.uniform(0.1, 0.5)
                )
                logger.warning(
                    f"[{pool.name}] Transient error ({type(e).__name__}): {e}. Waiting {delay:.1f}s before retry."
                )
                time.sleep(delay)
                continue

            raise

    raise RuntimeError(
        f"[{pool.name}] Max retries ({retries_limit}) exceeded without success. Last error: {last_error}"
    ) from last_error


# ============================================================
# SINGLETON KEY POOL MANAGEMENT
# ============================================================

_openrouter_pool: Optional[APIKeyPool] = None
_embedding_pool: Optional[APIKeyPool] = None
_pool_lock = threading.Lock()


def get_openrouter_key_pool(force_reload: bool = False) -> APIKeyPool:
    """Returns the singleton OpenRouter APIKeyPool."""
    global _openrouter_pool
    with _pool_lock:
        if _openrouter_pool is None or force_reload:
            import my_config

            keys = my_config.OPENROUTER_API_KEYS
            if not keys:
                # Fallback to singular or env
                sing = my_config.OPENROUTER_API_KEY
                keys = [sing] if sing else []
            _openrouter_pool = APIKeyPool(
                name="OpenRouter",
                keys=keys,
                default_cooldown=3.0,
                max_cooldown=60.0,
            )
        return _openrouter_pool


def get_embedding_key_pool(force_reload: bool = False) -> APIKeyPool:
    """Returns the singleton Mistral Embedding APIKeyPool."""
    global _embedding_pool
    with _pool_lock:
        if _embedding_pool is None or force_reload:
            import my_config

            keys = my_config.EMB_API_KEYS
            if not keys:
                sing = my_config.EMB_API_KEY
                keys = [sing] if sing else []
            _embedding_pool = APIKeyPool(
                name="Embeddings",
                keys=keys,
                default_cooldown=3.0,
                max_cooldown=60.0,
            )
        return _embedding_pool


def reset_key_pools() -> None:
    """Resets key pools (for testing or reconfiguration)."""
    global _openrouter_pool, _embedding_pool
    with _pool_lock:
        _openrouter_pool = None
        _embedding_pool = None
