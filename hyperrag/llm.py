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
    OPENROUTER_MODEL,
    MISTRAL_BASE_URL,
    MISTRAL_API_KEY,
    MISTRAL_MODEL,
    EMB_BASE_URL,
    EMB_API_KEY,
    EMB_MODEL,
    EMB_DIM,
)

from pydantic import BaseModel, Field
from typing import List, Dict, Callable, Any
from .base import BaseKVStorage
from .utils import compute_args_hash, wrap_embedding_func_with_attrs

logger = logging.getLogger("hyperrag.llm")

os.environ["TOKENIZERS_PARALLELISM"] = "false"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((APIConnectionError, Timeout)),
)
async def openai_complete_if_cache(
    model,
    prompt,
    system_prompt=None,
    history_messages=None,
    base_url=None,
    api_key=None,
    **kwargs,
) -> str:
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

    if hashing_kv is not None:
        await hashing_kv.upsert(
            {args_hash: {"return": response.choices[0].message.content, "model": model}}
        )
    return response.choices[0].message.content


async def openrouter_mistral_complete_if_cache(
    prompt,
    system_prompt=None,
    history_messages=None,
    **kwargs,
) -> str:
    """
    Primary LLM: OpenRouter (OPENROUTER_MODEL, OPENROUTER_BASE_URL)
    Fallback LLM: Mistral (MISTRAL_MODEL, MISTRAL_BASE_URL)
    Preserves caching and retry logic via openai_complete_if_cache.
    """
    history = history_messages if history_messages is not None else []

    # 1) Try OpenRouter (Primary)
    try:
        return await openai_complete_if_cache(
            model=OPENROUTER_MODEL,
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            **kwargs.copy(),
        )
    except Exception as openrouter_error:
        msg = f"[OpenRouter failed] {type(openrouter_error).__name__}: {openrouter_error}\n[Fallback] Switching to Mistral..."
        logger.warning(msg)
        print(msg, flush=True)

    # 2) Try Mistral (Fallback)
    try:
        return await openai_complete_if_cache(
            model=MISTRAL_MODEL,
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history,
            api_key=MISTRAL_API_KEY,
            base_url=MISTRAL_BASE_URL,
            **kwargs.copy(),
        )
    except Exception as mistral_error:
        raise RuntimeError(
            f"Both OpenRouter primary LLM and Mistral fallback LLM failed. Mistral error: {mistral_error}"
        ) from mistral_error


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
    Streaming LLM routing: OpenRouter first, Mistral fallback.
    - If OpenRouter fails BEFORE producing output, falls back to Mistral.
    - If OpenRouter has already emitted part of the response, does NOT append Mistral response.
    - Preserves cache replay and chunked streaming behavior.
    """
    history = history_messages if history_messages is not None else []
    yielded_any = False
    openrouter_failed_before_yield = False

    try:
        async for tok in openai_complete_stream_if_cache(
            model=OPENROUTER_MODEL,
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            chunk_size=chunk_size,
            **kwargs.copy(),
        ):
            yielded_any = True
            yield tok
    except Exception as e:
        if not yielded_any:
            openrouter_failed_before_yield = True
            msg = f"[OpenRouter failed] {type(e).__name__}: {e}\n[Fallback] Switching to Mistral..."
            logger.warning(msg)
            print(msg, flush=True)
        else:
            logger.error(
                f"OpenRouter streaming failed after emitting output ({type(e).__name__}: {e}). "
                "Aborting stream to prevent duplicate response."
            )
            print(
                f"[OpenRouter streaming failed after emitting output] {type(e).__name__}: {e}",
                flush=True,
            )
            raise

    if openrouter_failed_before_yield:
        try:
            async for tok in openai_complete_stream_if_cache(
                model=MISTRAL_MODEL,
                prompt=prompt,
                system_prompt=system_prompt,
                history_messages=history,
                api_key=MISTRAL_API_KEY,
                base_url=MISTRAL_BASE_URL,
                chunk_size=chunk_size,
                **kwargs.copy(),
            ):
                yield tok
        except Exception as mistral_err:
            raise RuntimeError(
                f"Both OpenRouter and Mistral streaming failed. Mistral error: {mistral_err}"
            ) from mistral_err


# Backwards compatibility alias
groq_mistral_stream_if_cache = openrouter_mistral_stream_if_cache


def openrouter_mistral_complete_sync(
    prompt,
    system_prompt=None,
    history_messages=None,
    **kwargs,
) -> str:
    """
    Synchronous LLM routing: OpenRouter first, Mistral fallback.
    """
    messages = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    if history_messages:
        messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    try:
        client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            max_retries=0,
        )
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            **kwargs,
        )
        if not response.choices or response.choices[0].message is None:
            raise ValueError("OpenRouter returned empty response")
        return response.choices[0].message.content
    except Exception as openrouter_error:
        msg = f"[OpenRouter failed] {type(openrouter_error).__name__}: {openrouter_error}\n[Fallback] Switching to Mistral..."
        logger.warning(msg)
        print(msg, flush=True)

    try:
        client = OpenAI(
            api_key=MISTRAL_API_KEY,
            base_url=MISTRAL_BASE_URL,
            max_retries=0,
        )
        response = client.chat.completions.create(
            model=MISTRAL_MODEL,
            messages=messages,
            **kwargs,
        )
        if not response.choices or response.choices[0].message is None:
            raise ValueError("Mistral returned empty response")
        return response.choices[0].message.content
    except Exception as mistral_error:
        raise RuntimeError(
            f"Both OpenRouter and Mistral synchronous calls failed. Mistral error: {mistral_error}"
        ) from mistral_error


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
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(
        (RateLimitError, APIConnectionError, Timeout)
    ),
)
async def openai_embedding(
    texts: list[str],
    model: str = None,
    base_url: str = None,
    api_key: str = None,
) -> np.ndarray:
    """
    OpenAI-compatible embedding function using Mistral mistral-embed (1024 dimensions).
    Function name preserved for compatibility.
    """
    resolved_model = model or EMB_MODEL or "mistral-embed"
    resolved_base_url = base_url or EMB_BASE_URL or "https://api.mistral.ai/v1"
    resolved_api_key = api_key or EMB_API_KEY or MISTRAL_API_KEY

    client = AsyncOpenAI(
        api_key=resolved_api_key,
        base_url=resolved_base_url,
    )

    response = await client.embeddings.create(
        model=resolved_model,
        input=texts,
        encoding_format="float",
    )

    return np.array(
        [item.embedding for item in response.data],
        dtype=np.float32,
    )


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
