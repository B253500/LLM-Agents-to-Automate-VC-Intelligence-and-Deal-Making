import os
import requests
from core.perplexity_utils import search_perplexity

# --- EXA Search Tool ---
def exa_search_competitors(query, num_results=5):
    """
    Use EXA API to search for competitors or company info.
    Returns a list of dicts with relevant info.
    """
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        print("[Warning] EXA_API_KEY not set in environment.")
        return []
    url = "https://api.exa.ai/search"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "query": query,
        "numResults": num_results,
        "category": "company"
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json().get("results", [])
        else:
            print(f"EXA API error: {response.status_code} {response.text}")
            return []
    except Exception as e:
        print(f"EXA API exception: {e}")
        return []

# --- Proxycurl LinkedIn Enrichment ---
def proxycurl_linkedin_profile(name, company=None):
    """
    Use Proxycurl to fetch LinkedIn profile data for a person (optionally at a company).
    Returns a dict with profile info or None.
    """
    api_key = os.getenv("PROXYCURL_API_KEY")
    if not api_key:
        print("[Warning] PROXYCURL_API_KEY not set in environment.")
        return None
    url = "https://nubela.co/proxycurl/api/v2/linkedin/person"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"first_name": name.split()[0], "last_name": name.split()[-1]}
    if company:
        params["company"] = company
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Proxycurl error: {response.status_code} {response.text}")
            return None
    except Exception as e:
        print(f"Proxycurl exception: {e}")
        return None

def is_website_match(website_url, company_name, context_snippet=None):
    """
    Fetch the homepage and check if the company name or context appears in the text.
    Returns True if a match is found, else False.
    """
    import requests
    try:
        resp = requests.get(website_url, timeout=8)
        if resp.status_code == 200:
            text = resp.text.lower()
            if company_name and company_name.lower() in text:
                return True
            if context_snippet and context_snippet.lower() in text:
                return True
    except Exception as e:
        print(f"[Website Match] Error fetching {website_url}: {e}")
    return False

# Update find_company_website to use is_website_match

def find_company_website(company_name, founder_name=None, sector=None, deck_text=None):
    import re
    from time import sleep
    # 1. Try to extract from deck text
    if deck_text:
        urls = re.findall(r"https?://[\w./-]+", deck_text)
        urls = [u for u in urls if not any(x in u for x in ["linkedin.com", "twitter.com", "facebook.com", "crunchbase.com"])]
        for url in urls:
            if is_website_match(url, company_name, sector):
                return url
    # 2. Try LLM prompt
    try:
        from langchain_openai import ChatOpenAI
        prompt = (
            f"You are a research analyst. Find the official website for the company '{company_name}'."
            f"{' The founder is ' + founder_name + '.' if founder_name else ''}"
            f"{' The sector is ' + sector + '.' if sector else ''}"
            " Use Google or web search if needed. Return only the official website URL. If ambiguous, explain your reasoning."
        )
        llm = ChatOpenAI(model='gpt-4')
        result = llm.invoke(prompt).content.strip()
        url_matches = re.findall(r"https?://[\w./-]+", result)
        for url in url_matches:
            if is_website_match(url, company_name, sector):
                return url
    except Exception as e:
        print(f"[WebsiteFinder] LLM error: {e}")
    # 3. Try Perplexity
    try:
        query = f"What is the official website for {company_name}?"
        result = search_perplexity(query)
        url_matches = re.findall(r"https?://[\w./-]+", result or "")
        for url in url_matches:
            if is_website_match(url, company_name, sector):
                return url
            sleep(1)  # avoid hammering Perplexity
    except Exception as e:
        print(f"[WebsiteFinder] Perplexity error: {e}")
    return None 