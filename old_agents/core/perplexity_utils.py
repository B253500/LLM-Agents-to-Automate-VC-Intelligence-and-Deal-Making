import os
import requests

def search_perplexity(query, num_results=3):
    """
    General-purpose Perplexity web search utility. Returns the LLM's answer to the query.
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
                return result["choices"][0]["message"]["content"]
            else:
                return result
        else:
            print(f"Perplexity API error: {response.status_code} {response.text}")
            return None
    except Exception as e:
        print(f"Perplexity API exception: {e}")
        return None 