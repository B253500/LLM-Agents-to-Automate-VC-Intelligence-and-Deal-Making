def truncate_to_chars(text: str, max_chars: int = 8000) -> str:
    """
    If text is longer than max_chars, cut it off at max_chars.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars]
