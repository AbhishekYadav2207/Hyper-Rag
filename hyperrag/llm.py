import os
import copy
import logging
from functools import lru_cache
import json
import aioboto3
import aiohttp
import numpy as np

from openai import (
    OpenAI,
    AsyncOpenAI,
    APIConnectionError,
    RateLimitError,
    Timeout,
    AsyncAzureOpenAI,
)

import base64
import struct

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from my_config import (
    OPENROUTER_BASE_URL,
    OPENROUTER_API_KEY,
    OPENROUTER_API_KEYS,
    OPENROUTER_MODEL,
    MISTRAL_BASE_URL,
    MISTRAL_API_KEY,
    MISTRAL_MODEL,
    EMB_BASE_URL,
    EMB_API_KEY,
    EMB_API_KEYS,
    EMB_MODEL,
    EMB_DIM,
)

from .key_pool import (
    APIKeyPool,
    get_openrouter_key_pool,
    get_embedding_key_pool,
    execute_with_key_rotation,
    execute_with_key_rotation_sync,
    get_async_client,
    get_sync_client,
    is_rate_limit_error,
    is_auth_error,
    is_permission_error,
    is_bad_request_error,
    is_transient_error,
    parse_retry_after,
)

from pydantic import BaseModel, Field
from typing import List, Dict, Callable, Any
from .base import BaseKVStorage
from .utils import compute_args_hash, wrap_embedding_func_with_attrs

logger = logging.getLogger("hyperrag.llm")

os.environ["TOKENIZERS_PARALLELISM"] = "false"


async def openai_complete_if_cache(
    model,
    prompt,
    system_prompt=None,
    history_messages=None,
    base_url=None,
    api_key=None,
    **kwargs,
) -> str:
    """
    OpenAI-compatible completion with caching.
    Uses OpenRouter key rotation pool when api_key is None and base_url is None.
    """
    if api_key is None and base_url is None:
        return await openrouter_mistral_complete_if_cache(
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            model=model,
            **kwargs,
        )

    client_kwargs = {"max_retries": 0}
    if api_key is not None:
        client_kwargs["api_key"] = api_key
    if base_url is not None:
        client_kwargs["base_url"] = base_url

    openai_async_client = AsyncOpenAI(**client_kwargs)

    hashing_kv: BaseKVStorage = kwargs.pop("hashing_kv", None)
    messages = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    if history_messages:
        messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    if hashing_kv is not None:
        args_hash = compute_args_hash(model, messages)
        if_cache_return = await hashing_kv.get_by_id(args_hash)
        if if_cache_return is not None:
            return if_cache_return["return"]

    response = await openai_async_client.chat.completions.create(
        model=model, messages=messages, **kwargs
    )

    if not getattr(response, "choices", None):
        raise RuntimeError(
            f"Provider returned no choices (model={getattr(response, 'model', model)})."
        )

    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError(
            f"Provider response has content=None (model={getattr(response, 'model', model)})."
        )

    if hashing_kv is not None:
        await hashing_kv.upsert(
            {args_hash: {"return": content, "model": model}}
        )
    return content


async def _execute_openrouter_completion(
    model: str,
    messages: list,
    max_tokens: int = 2000,
    **kwargs,
) -> str:
    """
    Internal runner for OpenRouter chat completion with automatic API-key rotation.
    NO fallback to Mistral LLM.
    """
    pool = get_openrouter_key_pool()
    base_url = kwargs.pop("base_url", None) or OPENROUTER_BASE_URL

    async def _send_request(api_key: str) -> str:
        client = get_async_client(api_key, base_url)
        raw_response = await client.chat.completions.with_raw_response.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            **kwargs,
        )
        status_code = raw_response.status_code
        if status_code != 200:
            msg = f"OpenRouter returned HTTP {status_code}: {raw_response.text}"
            if status_code == 429:
                raise RateLimitError(
                    msg, response=raw_response.http_response, body=raw_response.text
                )
            elif status_code == 401:
                raise AuthenticationError(
                    msg, response=raw_response.http_response, body=raw_response.text
                )
            elif status_code == 403:
                raise PermissionDeniedError(
                    msg, response=raw_response.http_response, body=raw_response.text
                )
            elif status_code == 400:
                raise BadRequestError(
                    msg, response=raw_response.http_response, body=raw_response.text
                )
            elif 500 <= status_code < 600:
                raise InternalServerError(
                    msg, response=raw_response.http_response, body=raw_response.text
                )
            else:
                raise RuntimeError(msg)

        try:
            raw_data = json.loads(raw_response.text)
        except Exception:
            raw_data = {}

        if "error" in raw_data and raw_data["error"]:
            err_info = raw_data["error"]
            err_code = err_info.get("code")
            msg = f"OpenRouter error payload: {err_info}"
            if err_code == 429 or "rate limit" in str(err_info).lower():
                raise RateLimitError(
                    msg, response=raw_response.http_response, body=raw_data
                )
            elif err_code == 401:
                raise AuthenticationError(
                    msg, response=raw_response.http_response, body=raw_data
                )
            raise RuntimeError(msg)

        parsed = raw_response.parse()
        choices = getattr(parsed, "choices", None)
        if not choices:
            raise RuntimeError(
                f"OpenRouter returned no choices (model={getattr(parsed, 'model', model)})."
            )

        choice = choices[0]
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None) if message else None

        if content is None:
            reasoning = getattr(message, "reasoning", None) if message else None
            if reasoning:
                content = reasoning
            else:
                finish_reason = getattr(choice, "finish_reason", "unknown")
                raise RuntimeError(
                    f"OpenRouter response contained no usable content "
                    f"(model={getattr(parsed, 'model', model)}, finish_reason={finish_reason})."
                )

        returned_model = getattr(parsed, "model", model)
        logger.info(f"OpenRouter response received (model: {returned_model})")
        return content

    return await execute_with_key_rotation(pool, _send_request)


async def openrouter_mistral_complete_if_cache(
    prompt,
    system_prompt=None,
    history_messages=None,
    **kwargs,
) -> str:
    """
    OpenRouter LLM completion with automatic API-key rotation.
    NO fallback to Mistral LLM.
    Function name preserved for backwards compatibility.
    """
    model = kwargs.pop("model", None) or OPENROUTER_MODEL
    hashing_kv: BaseKVStorage = kwargs.pop("hashing_kv", None)
    max_tokens = kwargs.pop("max_tokens", 2000)

    messages = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    if history_messages:
        messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    if hashing_kv is not None:
        args_hash = compute_args_hash(model, messages)
        cached = await hashing_kv.get_by_id(args_hash)
        if cached is not None:
            return cached["return"]

    content = await _execute_openrouter_completion(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        **kwargs,
    )

    if hashing_kv is not None:
        await hashing_kv.upsert({args_hash: {"return": content, "model": model}})

    return content


async def openrouter_nvidia_complete_if_cache(
    prompt,
    system_prompt=None,
    history_messages=None,
    **kwargs,
) -> str:
    """
    NVIDIA Nemotron 3 Ultra through OpenRouter with automatic API-key rotation.
    No Mistral fallback.
    """
    return await openrouter_mistral_complete_if_cache(
        prompt=prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        **kwargs,
    )


# Backwards compatibility alias
groq_mistral_complete_if_cache = openrouter_mistral_complete_if_cache


async def openai_complete_stream_if_cache(
    model,
    prompt,
    system_prompt=None,
    history_messages=None,
    base_url=None,
    api_key=None,
    chunk_size: int = 32,
    **kwargs,
):
    """
    OpenAI-compatible streaming output (async generator)
    - Cache hit: yields in chunk_size blocks
    - Cache miss: streams token-by-token and writes cache upon completion
    """
    client_kwargs = {"max_retries": 0}
    if api_key is not None:
        client_kwargs["api_key"] = api_key
    if base_url is not None:
        client_kwargs["base_url"] = base_url

    openai_async_client = AsyncOpenAI(**client_kwargs)

    hashing_kv: BaseKVStorage = kwargs.pop("hashing_kv", None)

    messages = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    if history_messages:
        messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    # 1) Cache hit: replay cached content
    if hashing_kv is not None:
        args_hash = compute_args_hash(model, messages)
        if_cache_return = await hashing_kv.get_by_id(args_hash)
        if if_cache_return is not None:
            cached = if_cache_return["return"] or ""
            for i in range(0, len(cached), chunk_size):
                yield cached[i : i + chunk_size]
            return

    # 2) Cache miss: stream from provider
    full_text = []
    stream = await openai_async_client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        **kwargs,
    )

    async for event in stream:
        delta = None
        if event.choices:
            delta = getattr(event.choices[0].delta, "content", None)
        if delta:
            full_text.append(delta)
            yield delta

    # 3) Write to cache
    if hashing_kv is not None:
        text = "".join(full_text)
        await hashing_kv.upsert({args_hash: {"return": text, "model": model}})


async def openrouter_mistral_stream_if_cache(
    prompt,
    system_prompt=None,
    history_messages=None,
    chunk_size: int = 32,
    **kwargs,
):
    """
    Streaming OpenRouter LLM routing with automatic API-key rotation before stream emission.
    NO fallback to Mistral LLM.
    Function name preserved for backwards compatibility.
    """
    model = kwargs.pop("model", None) or OPENROUTER_MODEL
    base_url = kwargs.pop("base_url", None) or OPENROUTER_BASE_URL
    hashing_kv: BaseKVStorage = kwargs.pop("hashing_kv", None)

    messages = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    if history_messages:
        messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    # 1) Cache hit: replay cached content
    if hashing_kv is not None:
        args_hash = compute_args_hash(model, messages)
        cached = await hashing_kv.get_by_id(args_hash)
        if cached is not None:
            cached_text = cached.get("return", "") or ""
            for i in range(0, len(cached_text), chunk_size):
                yield cached_text[i : i + chunk_size]
            return

    pool = get_openrouter_key_pool()
    retries_limit = max(10, pool.total * 3)
    attempt = 0
    stream = None
    active_key = None

    while attempt < retries_limit:
        attempt += 1
        ks = await pool.acquire_usable_key()
        active_key = ks.key

        log_msg = f"[{pool.name}] Using {ks.display_name}"
        print(log_msg, flush=True)
        logger.info(log_msg)

        try:
            client = get_async_client(active_key, base_url)
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                **kwargs,
            )
            break
        except Exception as e:
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
                    min(30.0, (2 ** (attempt - 1)) * 1.0)
                    + random.uniform(0.1, 0.5)
                )
                logger.warning(
                    f"[{pool.name}] Transient streaming error ({type(e).__name__}): {e}. Waiting {delay:.1f}s."
                )
                await asyncio.sleep(delay)
                continue
            raise

    if stream is None:
        raise RuntimeError(
            f"[{pool.name}] Failed to establish stream after {retries_limit} attempts."
        )

    full_text = []
    first_token = True
    try:
        async for event in stream:
            delta = None
            if event.choices:
                delta = getattr(event.choices[0].delta, "content", None)
            if delta:
                if first_token:
                    pool.mark_success(active_key)
                    success_msg = f"[{pool.name}] Request successful."
                    print(success_msg, flush=True)
                    logger.info(success_msg)
                    first_token = False
                full_text.append(delta)
                yield delta
        if first_token:
            pool.mark_success(active_key)
            success_msg = f"[{pool.name}] Request successful."
            print(success_msg, flush=True)
            logger.info(success_msg)
    except Exception as stream_err:
        logger.error(f"[{pool.name}] Error during active stream: {stream_err}")
        raise

    if hashing_kv is not None:
        text = "".join(full_text)
        await hashing_kv.upsert({args_hash: {"return": text, "model": model}})


# Backwards compatibility alias
groq_mistral_stream_if_cache = openrouter_mistral_stream_if_cache


def openrouter_mistral_complete_sync(
    prompt,
    system_prompt=None,
    history_messages=None,
    **kwargs,
) -> str:
    """
    Synchronous OpenRouter completion with automatic API-key rotation.
    NO fallback to Mistral LLM.
    Function name preserved for backwards compatibility.
    """
    model = kwargs.pop("model", None) or OPENROUTER_MODEL
    base_url = kwargs.pop("base_url", None) or OPENROUTER_BASE_URL
    max_tokens = kwargs.pop("max_tokens", 2000)

    messages = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    if history_messages:
        messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    def _send_sync(api_key: str) -> str:
        client = get_sync_client(api_key, base_url)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            **kwargs,
        )
        if not response.choices or response.choices[0].message is None:
            raise ValueError("OpenRouter returned empty response")
        choice = response.choices[0]
        content = choice.message.content
        if content is None:
            reasoning = getattr(choice.message, "reasoning", None)
            if reasoning:
                content = reasoning
            else:
                raise ValueError("OpenRouter response contained no usable content")
        return content

    pool = get_openrouter_key_pool()
    return execute_with_key_rotation_sync(pool, _send_sync)


# Backwards compatibility alias
groq_mistral_complete_sync = openrouter_mistral_complete_sync


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((RateLimitError, APIConnectionError, Timeout)),
)
async def azure_openai_complete_if_cache(
    model,
    prompt,
    system_prompt=None,
    history_messages=None,
    base_url=None,
    api_key=None,
    **kwargs,
):
    if api_key:
        os.environ["AZURE_OPENAI_API_KEY"] = api_key
    if base_url:
        os.environ["AZURE_OPENAI_ENDPOINT"] = base_url

    openai_async_client = AsyncAzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )

    hashing_kv: BaseKVStorage = kwargs.pop("hashing_kv", None)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history_messages:
        messages.extend(history_messages)
    if prompt is not None:
        messages.append({"role": "user", "content": prompt})
    if hashing_kv is not None:
        args_hash = compute_args_hash(model, messages)
        if_cache_return = await hashing_kv.get_by_id(args_hash)
        if if_cache_return is not None:
            return if_cache_return["return"]

    response = await openai_async_client.chat.completions.create(
        model=model, messages=messages, **kwargs
    )

    if hashing_kv is not None:
        await hashing_kv.upsert(
            {args_hash: {"return": response.choices[0].message.content, "model": model}}
        )
    return response.choices[0].message.content


class BedrockError(Exception):
    """Generic error for issues related to Amazon Bedrock"""


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, max=60),
    retry=retry_if_exception_type((BedrockError)),
)
async def bedrock_complete_if_cache(
    model,
    prompt,
    system_prompt=None,
    history_messages=None,
    aws_access_key_id=None,
    aws_secret_access_key=None,
    aws_session_token=None,
    **kwargs,
) -> str:
    os.environ["AWS_ACCESS_KEY_ID"] = os.environ.get(
        "AWS_ACCESS_KEY_ID", aws_access_key_id
    )
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.environ.get(
        "AWS_SECRET_ACCESS_KEY", aws_secret_access_key
    )
    os.environ["AWS_SESSION_TOKEN"] = os.environ.get(
        "AWS_SESSION_TOKEN", aws_session_token
    )

    history = history_messages if history_messages is not None else []
    messages = []
    for history_message in history:
        message = copy.copy(history_message)
        message["content"] = [{"text": message["content"]}]
        messages.append(message)

    messages.append({"role": "user", "content": [{"text": prompt}]})

    args = {"modelId": model, "messages": messages}

    if system_prompt:
        args["system"] = [{"text": system_prompt}]

    inference_params_map = {
        "max_tokens": "maxTokens",
        "top_p": "topP",
        "stop_sequences": "stopSequences",
    }
    if inference_params := list(
        set(kwargs) & set(["max_tokens", "temperature", "top_p", "stop_sequences"])
    ):
        args["inferenceConfig"] = {}
        for param in inference_params:
            args["inferenceConfig"][inference_params_map.get(param, param)] = (
                kwargs.pop(param)
            )

    hashing_kv: BaseKVStorage = kwargs.pop("hashing_kv", None)
    if hashing_kv is not None:
        args_hash = compute_args_hash(model, messages)
        if_cache_return = await hashing_kv.get_by_id(args_hash)
        if if_cache_return is not None:
            return if_cache_return["return"]

    session = aioboto3.Session()
    async with session.client("bedrock-runtime") as bedrock_async_client:
        try:
            response = await bedrock_async_client.converse(**args, **kwargs)
        except Exception as e:
            raise BedrockError(e)

        if hashing_kv is not None:
            await hashing_kv.upsert(
                {
                    args_hash: {
                        "return": response["output"]["message"]["content"][0]["text"],
                        "model": model,
                    }
                }
            )

        return response["output"]["message"]["content"][0]["text"]


async def gpt_4o_complete(
    prompt, system_prompt=None, history_messages=None, **kwargs
) -> str:
    """Retained for backwards compatibility: routes to openrouter_mistral_complete_if_cache"""
    return await openrouter_mistral_complete_if_cache(
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        **kwargs,
    )


async def gpt_4o_mini_complete(
    prompt, system_prompt=None, history_messages=None, **kwargs
) -> str:
    """Retained for backwards compatibility: routes to openrouter_mistral_complete_if_cache"""
    return await openrouter_mistral_complete_if_cache(
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        **kwargs,
    )


async def azure_openai_complete(
    prompt, system_prompt=None, history_messages=None, **kwargs
) -> str:
    return await azure_openai_complete_if_cache(
        "conversation-4o-mini",
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        **kwargs,
    )


async def bedrock_complete(
    prompt, system_prompt=None, history_messages=None, **kwargs
) -> str:
    return await bedrock_complete_if_cache(
        "anthropic.claude-3-haiku-20240307-v1:0",
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        **kwargs,
    )


@wrap_embedding_func_with_attrs(
    embedding_dim=1024,
    max_token_size=8192,
)
async def openai_embedding(
    texts: list[str],
    model: str = None,
    base_url: str = None,
    api_key: str = None,
) -> np.ndarray:
    """
    OpenAI-compatible embedding function using Mistral mistral-embed (1024 dimensions).
    Uses automatic API-key rotation via EMB_API_KEYS.
    Function name preserved for compatibility.
    """
    resolved_model = model or EMB_MODEL or "mistral-embed"
    resolved_base_url = base_url or EMB_BASE_URL or "https://api.mistral.ai/v1"

    pool = get_embedding_key_pool()

    async def _send_embedding(active_key: str) -> np.ndarray:
        client = get_async_client(active_key, resolved_base_url)
        response = await client.embeddings.create(
            model=resolved_model,
            input=texts,
            encoding_format="float",
        )
        return np.array(
            [item.embedding for item in response.data],
            dtype=np.float32,
        )

    # If caller specifically provided an override key not in pool
    if api_key and api_key not in pool.keys:
        temp_pool = APIKeyPool("Embeddings", [api_key])
        return await execute_with_key_rotation(temp_pool, _send_embedding)

    return await execute_with_key_rotation(pool, _send_embedding)


@wrap_embedding_func_with_attrs(embedding_dim=1536, max_token_size=8192)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((RateLimitError, APIConnectionError, Timeout)),
)
async def azure_openai_embedding(
    texts: list[str],
    model: str = "text-embedding-3-small",
    base_url: str = None,
    api_key: str = None,
) -> np.ndarray:
    if api_key:
        os.environ["AZURE_OPENAI_API_KEY"] = api_key
    if base_url:
        os.environ["AZURE_OPENAI_ENDPOINT"] = base_url

    openai_async_client = AsyncAzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )

    response = await openai_async_client.embeddings.create(
        model=model, input=texts, encoding_format="float"
    )
    return np.array([dp.embedding for dp in response.data])


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((RateLimitError, APIConnectionError, Timeout)),
)
async def siliconcloud_embedding(
    texts: list[str],
    model: str = "netease-youdao/bce-embedding-base_v1",
    base_url: str = "https://api.siliconflow.cn/v1/embeddings",
    max_token_size: int = 512,
    api_key: str = None,
) -> np.ndarray:
    if api_key and not api_key.startswith("Bearer "):
        api_key = "Bearer " + api_key

    headers = {"Authorization": api_key, "Content-Type": "application/json"}

    truncate_texts = [text[0:max_token_size] for text in texts]

    payload = {"model": model, "input": truncate_texts, "encoding_format": "base64"}

    base64_strings = []
    async with aiohttp.ClientSession() as session:
        async with session.post(base_url, headers=headers, json=payload) as response:
            content = await response.json()
            if "code" in content:
                raise ValueError(content)
            base64_strings = [item["embedding"] for item in content["data"]]

    embeddings = []
    for string in base64_strings:
        decode_bytes = base64.b64decode(string)
        n = len(decode_bytes) // 4
        float_array = struct.unpack("<" + "f" * n, decode_bytes)
        embeddings.append(float_array)
    return np.array(embeddings)


async def bedrock_embedding(
    texts: list[str],
    model: str = "amazon.titan-embed-text-v2:0",
    aws_access_key_id=None,
    aws_secret_access_key=None,
    aws_session_token=None,
) -> np.ndarray:
    os.environ["AWS_ACCESS_KEY_ID"] = os.environ.get(
        "AWS_ACCESS_KEY_ID", aws_access_key_id
    )
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.environ.get(
        "AWS_SECRET_ACCESS_KEY", aws_secret_access_key
    )
    os.environ["AWS_SESSION_TOKEN"] = os.environ.get(
        "AWS_SESSION_TOKEN", aws_session_token
    )

    session = aioboto3.Session()
    async with session.client("bedrock-runtime") as bedrock_async_client:
        if (model_provider := model.split(".")[0]) == "amazon":
            embed_texts = []
            for text in texts:
                if "v2" in model:
                    body = json.dumps(
                        {
                            "inputText": text,
                            "embeddingTypes": ["float"],
                        }
                    )
                elif "v1" in model:
                    body = json.dumps({"inputText": text})
                else:
                    raise ValueError(f"Model {model} is not supported!")

                response = await bedrock_async_client.invoke_model(
                    modelId=model,
                    body=body,
                    accept="application/json",
                    contentType="application/json",
                )

                response_body = await response.get("body").json()

                embed_texts.append(response_body["embedding"])
        elif model_provider == "cohere":
            body = json.dumps(
                {"texts": texts, "input_type": "search_document", "truncate": "NONE"}
            )

            response = await bedrock_async_client.invoke_model(
                model=model,
                body=body,
                accept="application/json",
                contentType="application/json",
            )

            response_body = json.loads(response.get("body").read())

            embed_texts = response_body["embeddings"]
        else:
            raise ValueError(f"Model provider '{model_provider}' is not supported!")

        return np.array(embed_texts)


class Model(BaseModel):
    gen_func: Callable[[Any], str] = Field(
        ...,
        description="A function that generates the response from the llm. The response must be a string",
    )
    kwargs: Dict[str, Any] = Field(
        ...,
        description="The arguments to pass to the callable function. Eg. the api key, model name, etc",
    )

    class Config:
        arbitrary_types_allowed = True


class MultiModel:
    def __init__(self, models: List[Model]):
        self._models = models
        self._current_model = 0

    def _next_model(self):
        self._current_model = (self._current_model + 1) % len(self._models)
        return self._models[self._current_model]

    async def llm_model_func(
        self, prompt, system_prompt=None, history_messages=None, **kwargs
    ) -> str:
        kwargs.pop("model", None)
        next_model = self._next_model()
        args = dict(
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            **kwargs,
            **next_model.kwargs,
        )

        return await next_model.gen_func(**args)


if __name__ == "__main__":
    import asyncio

    async def main():
        result = await gpt_4o_mini_complete("How are you?")
        print(result)

    asyncio.run(main())
