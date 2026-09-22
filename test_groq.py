# -*- coding: utf-8 -*-
"""
Verification script: sends a tiny test completion directly to Groq.
"""
import sys
from openai import OpenAI
import my_config

def main():
    print(f"Testing Groq primary LLM ({my_config.GROQ_MODEL})...")
    client = OpenAI(
        api_key=my_config.GROQ_API_KEY,
        base_url=my_config.GROQ_BASE_URL,
    )
    try:
        response = client.chat.completions.create(
            model=my_config.GROQ_MODEL,
            messages=[{"role": "user", "content": "Respond with the word 'PONG'."}],
            max_tokens=100,
        )
        content = (response.choices[0].message.content or "").strip()
        print(f"Groq response received: {content}")
        assert len(content) > 0, "Expected non-empty response content from Groq"
        print("Groq test PASSED.")
    except Exception as e:
        print(f"Groq test FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
