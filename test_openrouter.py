# -*- coding: utf-8 -*-
"""
Verification script: sends a test completion directly to OpenRouter.
Verifies the OpenRouter primary LLM endpoint and model.
Does not print secrets or credentials.
"""
import sys
import asyncio
from openai import AsyncOpenAI
from my_config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
)


async def main():
    print(f"Testing OpenRouter primary LLM ({OPENROUTER_MODEL})...")
    client = AsyncOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        max_retries=0,
    )

    try:
        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly: OpenRouter works",
                }
            ],
        )

        content = (response.choices[0].message.content or "").strip()
        print("Response received:")
        print(content)
        assert len(content) > 0, "Empty response from OpenRouter"
        print("\n[OK] OpenRouter direct test passed.")
    except Exception as e:
        print(f"\n[FAIL] OpenRouter test failed: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())