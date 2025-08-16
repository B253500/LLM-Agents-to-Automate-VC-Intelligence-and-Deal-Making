from typing import Any, Optional


def _extract_usage(message: Any) -> Optional[dict]:
    """Best-effort extraction of token usage from a LangChain AIMessage or SDK response.
    Returns a dict with keys: input_tokens, output_tokens, total_tokens when available.
    """
    if message is None:
        return None
    # LangChain AIMessage.usage_metadata
    usage = getattr(message, "usage_metadata", None)
    if isinstance(usage, dict) and ("input_tokens" in usage or "output_tokens" in usage):
        return {
            "input_tokens": int(usage.get("input_tokens", 0) or 0),
            "output_tokens": int(usage.get("output_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        }
    # Some providers attach token usage under response_metadata
    rmeta = getattr(message, "response_metadata", None)
    if isinstance(rmeta, dict):
        # Common keys
        token_usage = rmeta.get("token_usage") or rmeta.get("usage_metadata")
        if isinstance(token_usage, dict):
            input_tokens = (
                token_usage.get("prompt_tokens")
                or token_usage.get("input_tokens")
                or 0
            )
            output_tokens = (
                token_usage.get("completion_tokens")
                or token_usage.get("output_tokens")
                or 0
            )
            total_tokens = (
                token_usage.get("total_tokens")
                or (int(input_tokens or 0) + int(output_tokens or 0))
            )
            return {
                "input_tokens": int(input_tokens or 0),
                "output_tokens": int(output_tokens or 0),
                "total_tokens": int(total_tokens or 0),
            }
    return None


def log_usage_from_message(evaluator: Any, agent_name: str, message: Any, model: str = "gpt-4o") -> None:
    """If usage is present on message, log exact tokens for the given agent.
    Safe no-op if evaluator is None or usage not found.
    """
    if evaluator is None or message is None:
        return
    usage = _extract_usage(message)
    if not usage:
        return
    evaluator.log_agent_tokens(
        agent_name=agent_name,
        input_tokens=int(usage.get("input_tokens", 0) or 0),
        output_tokens=int(usage.get("output_tokens", 0) or 0),
        model=model,
    )

