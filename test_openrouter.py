import asyncio

from openai import AsyncOpenAI
from my_config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
)


async def main():
    client = AsyncOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        max_retries=0,
    )

    response = await client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: OpenRouter works",
            }
        ],
    )

    print(response.choices[0].message.content)


asyncio.run(main())