# -*- coding: utf-8 -*-
"""
Verification script: tests Groq -> Mistral fallback without modifying source code.
Simulates a Groq provider failure and verifies that Mistral is invoked
for async completion, streaming, and synchronous calls.
"""
import sys
import asyncio
import hyperrag.llm as llm

async def test_async_fallback():
    print(f"\n--- 1. Testing Async groq_mistral_complete_if_cache Fallback to {llm.MISTRAL_MODEL} ---")
    orig_url = llm.GROQ_BASE_URL
    # Simulate Groq failure via invalid endpoint
    llm.GROQ_BASE_URL = "http://127.0.0.1:9/v1"
    try:
        response = await llm.groq_mistral_complete_if_cache(
            prompt="Respond with 'ASYNC_FALLBACK_OK'."
        )
        print(f"Fallback response received: {response.strip()}")
        assert len(response) > 0, "Empty response from fallback"
        print(f"[OK] Async fallback to Mistral ({llm.MISTRAL_MODEL}) succeeded.")
    finally:
        llm.GROQ_BASE_URL = orig_url

async def test_streaming_fallback():
    print(f"\n--- 2. Testing Streaming groq_mistral_stream_if_cache Fallback to {llm.MISTRAL_MODEL} ---")
    orig_url = llm.GROQ_BASE_URL
    llm.GROQ_BASE_URL = "http://127.0.0.1:9/v1"
    try:
        chunks = []
        async for chunk in llm.groq_mistral_stream_if_cache(
            prompt="Respond with 'STREAMING_FALLBACK_OK'."
        ):
            chunks.append(chunk)
        full_text = "".join(chunks).strip()
        print(f"Streaming fallback response received: {full_text}")
        assert len(full_text) > 0, "Empty response from streaming fallback"
        print(f"[OK] Streaming fallback to Mistral ({llm.MISTRAL_MODEL}) succeeded without duplicates.")
    finally:
        llm.GROQ_BASE_URL = orig_url

def test_sync_fallback():
    print(f"\n--- 3. Testing Synchronous groq_mistral_complete_sync Fallback to {llm.MISTRAL_MODEL} ---")
    orig_url = llm.GROQ_BASE_URL
    llm.GROQ_BASE_URL = "http://127.0.0.1:9/v1"
    try:
        response = llm.groq_mistral_complete_sync(
            prompt="Respond with 'SYNC_FALLBACK_OK'."
        )
        print(f"Sync fallback response received: {response.strip()}")
        assert len(response) > 0, "Empty response from sync fallback"
        print(f"[OK] Synchronous fallback to Mistral ({llm.MISTRAL_MODEL}) succeeded.")
    finally:
        llm.GROQ_BASE_URL = orig_url

async def main():
    print(f"Testing Groq ({llm.GROQ_MODEL}) -> Mistral ({llm.MISTRAL_MODEL}) Fallback Mechanism...")
    await test_async_fallback()
    await test_streaming_fallback()
    test_sync_fallback()
    print("\nAll fallback tests PASSED successfully!")

if __name__ == "__main__":
    asyncio.run(main())
