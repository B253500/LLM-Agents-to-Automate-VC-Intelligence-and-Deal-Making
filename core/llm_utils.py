# core/llm_utils.py
import time
import re
from typing import Any
from openai import RateLimitError  # Correct import
from langchain_openai import ChatOpenAI


def _strip_fences(text: str) -> str:
    if text.startswith("```"):
        text = re.sub(r"^```[^\n]*\n", "", text, count=1)
        text = text.rsplit("```", 1)[0]
    return text


def invoke_with_fallback(
    prompt: str,
    *,
    primary_model="gpt-4o-mini",
    fallback_model="gpt-3.5-turbo",
    temperature=0.2,
    retries=2,
    backoff=2,
) -> Any:
    """
    Try primary_model, retry with exponential backoff on RateLimitError,
    then fall back to fallback_model.
    Returns the LLM response object.
    """
    # Try primary with retry
    for i in range(retries):
        try:
            llm = ChatOpenAI(model=primary_model, temperature=temperature)
            return llm.invoke(prompt)
        except RateLimitError:
            wait = backoff**i
            print(f"[Rate-limit on {primary_model}, retrying in {wait}s…]")
            time.sleep(wait)
        except Exception as e:
            # Some OpenAI wrappers wrap the error differently
            if "rate limit" in str(e).lower():
                wait = backoff**i
                print(f"[Rate-limit on {primary_model}, retrying in {wait}s…]")
                time.sleep(wait)
            else:
                raise

    # Final fallback attempt
    print(f"[Falling back to {fallback_model}]")
    llm = ChatOpenAI(model=fallback_model, temperature=temperature)
    return llm.invoke(prompt)
