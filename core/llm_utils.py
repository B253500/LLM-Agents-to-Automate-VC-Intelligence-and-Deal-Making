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
    primary_model="gpt-4o",
    fallback_model="gpt-4o",
    temperature=0.2,
    retries=2,
    backoff=2,
    section_name="unknown",  # Add section name for tracking
    agent_name="unknown",    # Add agent name for tracking
    evaluator=None,  # Add evaluator for token tracking
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
            response = llm.invoke(prompt)
            
            # Track token usage if evaluator is provided
            if evaluator and hasattr(response, 'usage'):
                input_tokens = getattr(response.usage, 'prompt_tokens', 0)
                output_tokens = getattr(response.usage, 'completion_tokens', 0)
                
                # Track both section and agent tokens
                if section_name != "unknown":
                    evaluator.log_section_tokens(section_name, input_tokens, output_tokens, primary_model)
                if agent_name != "unknown":
                    evaluator.log_agent_tokens(agent_name, input_tokens, output_tokens, primary_model)
            
            return response
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
    response = llm.invoke(prompt)
    
    # Track token usage for fallback too
    if evaluator and hasattr(response, 'usage'):
        input_tokens = getattr(response.usage, 'prompt_tokens', 0)
        output_tokens = getattr(response.usage, 'completion_tokens', 0)
        
        # Track both section and agent tokens
        if section_name != "unknown":
            evaluator.log_section_tokens(section_name, input_tokens, output_tokens, fallback_model)
        if agent_name != "unknown":
            evaluator.log_agent_tokens(agent_name, input_tokens, output_tokens, fallback_model)
    
    return response
