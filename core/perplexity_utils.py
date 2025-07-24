import os
import requests
import re

def extract_snippet_and_url(perplexity_answer):
    """
    Extract the first snippet and URL from a Perplexity LLM answer (markdown or raw URL).
    Returns a dict: {"text": snippet, "url": url} or None if not found.
    """
    # Look for markdown links: [text](url)
    matches = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', perplexity_answer)
    if matches:
        return {"text": matches[0][0], "url": matches[0][1]}
    # Fallback: look for raw URLs
    urls = re.findall(r'(https?://[^\s\)\]]+)', perplexity_answer)
    if urls:
        return {"text": perplexity_answer, "url": urls[0]}
    return None

def search_perplexity(query, num_results=3, return_url=False):
    """
    General-purpose Perplexity web search utility. Returns the LLM's answer to the query.
    If return_url=True, returns a dict with 'answer', 'snippet', and 'url' (if found).
    """
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        print("[Warning] PERPLEXITY_API_KEY not set in environment.")
        return None
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "sonar-reasoning-pro",
        "messages": [
            {"role": "system", "content": "You are a helpful research assistant. Answer with up-to-date, factual, and cited information."},
            {"role": "user", "content": query}
        ],
        "max_tokens": 512,
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                answer = result["choices"][0]["message"]["content"]
                if return_url:
                    snippet_url = extract_snippet_and_url(answer)
                    return {"answer": answer, **(snippet_url or {})}
                return answer
            else:
                return result
        else:
            print(f"Perplexity API error: {response.status_code} {response.text}")
            return None
    except Exception as e:
        print(f"Perplexity API exception: {e}")
        return None 