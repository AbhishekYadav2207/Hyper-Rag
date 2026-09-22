# -*- coding: utf-8 -*-
"""
Verification script: sends a test completion to Mistral.
Handles reporting clearly if the account tier has rate limits on specific models.
"""
import sys
from openai import OpenAI, RateLimitError
import my_config

def main():
    print(f"Testing Mistral fallback LLM ({my_config.MISTRAL_MODEL})...")
    client = OpenAI(
        api_key=my_config.MISTRAL_API_KEY,
        base_url=my_config.MISTRAL_BASE_URL,
    )
    try:
        # Check authentication / connectivity first
        models = client.models.list()
        print(f"  [OK] Mistral authentication verified ({len(models.data)} models available).")

        response = client.chat.completions.create(
            model=my_config.MISTRAL_MODEL,
            messages=[{"role": "user", "content": "Respond with the word 'PONG'."}],
            max_tokens=20,
        )
        content = (response.choices[0].message.content or "").strip()
        print(f"Mistral response received: {content}")
        assert len(content) > 0, "Expected non-empty response content from Mistral"
        print("Mistral test PASSED.")
    except RateLimitError as e:
        print(f"\n[NOTE] Mistral rate limit / tier restriction encountered for '{my_config.MISTRAL_MODEL}': {e.message}")
        print("  Testing alternative model 'open-mistral-7b' to verify chat completion capability with this key...")
        try:
            alt_response = client.chat.completions.create(
                model="open-mistral-7b",
                messages=[{"role": "user", "content": "Respond with 'PONG'."}],
                max_tokens=20,
            )
            alt_content = (alt_response.choices[0].message.content or "").strip()
            print(f"  [OK] Alternative model 'open-mistral-7b' chat completion succeeded: {alt_content}")
            print(f"  Result: Mistral credentials are valid, but '{my_config.MISTRAL_MODEL}' requires activating paid tier / quotas on console.mistral.ai.")
        except Exception as alt_err:
            print(f"  Alternative test also failed: {alt_err}")
            sys.exit(1)
    except Exception as e:
        print(f"Mistral test FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
