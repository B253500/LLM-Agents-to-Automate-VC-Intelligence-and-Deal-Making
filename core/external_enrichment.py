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
            
            # Check for company name (more flexible matching)
            if company_name:
                company_lower = company_name.lower()
                # Check exact match first
                if company_lower in text:
                    return True
                # Check for partial matches (e.g., "lunchbox" in "lunchbox.io")
                if company_lower.replace(' ', '') in text.replace(' ', ''):
                    return True
                # Check for domain name match
                if company_lower in website_url.lower():
                    return True
            
            # Check for sector/context keywords
            if context_snippet:
                context_lower = context_snippet.lower()
                if context_lower in text:
                    return True
                
    except Exception as e:
        print(f"[Website Match] Error fetching {website_url}: {e}")
    return False

# Update find_company_website to use is_website_match

def find_company_website(company_name, founder_name=None, sector=None, deck_text=None):
    import re
    from time import sleep
    
    # 1. Try to extract from deck text first
    if deck_text:
        urls = re.findall(r"https?://[\w./-]+", deck_text)
        # Filter out social media, admin pages, and subdomain URLs
        filtered_urls = []
        for url in urls:
            # Skip social media and admin URLs
            if any(x in url for x in ["linkedin.com", "twitter.com", "facebook.com", "crunchbase.com", "/admin", "/login", "myshopify.com"]):
                continue
            # Skip URLs that are clearly not company websites (e.g., store admin pages)
            if any(x in url for x in ["admin", "login", "dashboard", "myshopify.com", "shopify.com/admin"]):
                continue
            filtered_urls.append(url)
        
        for url in filtered_urls:
            if is_website_match(url, company_name, sector):
                return url
    
    # 2. Try sector-specific Perplexity search
    try:
        if sector:
            query = f"What is the official website for {company_name} ({sector} company)?"
        else:
            query = f"What is the official website for {company_name}?"
        
        result = search_perplexity(query)
        url_matches = re.findall(r"https?://[\w./-]+", result or "")
        
        # Validate each URL found
        for url in url_matches:
            if is_website_match(url, company_name, sector):
                return url
            sleep(1)  # avoid hammering Perplexity
    except Exception as e:
        print(f"[WebsiteFinder] Perplexity error: {e}")
    
    # 3. Try LLM prompt with better context
    try:
        from langchain_openai import ChatOpenAI
        
        # Build context for better disambiguation
        context_parts = []
        if sector:
            context_parts.append(f"sector: {sector}")
        if founder_name:
            context_parts.append(f"founder: {founder_name}")
        
        context_str = f" ({', '.join(context_parts)})" if context_parts else ""
        
        prompt = (
            f"You are a research analyst. Find the official, public-facing company website (homepage) for '{company_name}'{context_str}."
            " Return ONLY the official website URL. If not found, return 'unknown'."
            " Do NOT return internal, admin, login, or example URLs (such as /admin, /login, or subdomains like myshopify.com)."
            " Be specific and accurate - if there are multiple companies with similar names, choose the one that matches the sector/context."
        )
        
        llm = ChatOpenAI(model='gpt-4o', temperature=0.1)
        result = llm.invoke(prompt).content.strip()
        
        # Extract URLs from LLM response
        url_matches = re.findall(r"https?://[\w./-]+", result)
        for url in url_matches:
            if is_website_match(url, company_name, sector):
                return url
    except Exception as e:
        print(f"[WebsiteFinder] LLM error: {e}")
    
    return None 