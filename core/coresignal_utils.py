import os
import requests

BASE = "https://api.coresignal.com/cdapi/v2"
SEARCH_MULTI = f"{BASE}/company_multi_source/search/es_dsl"
COLLECT_MULTI = f"{BASE}/company_multi_source/collect"
SEARCH_BASE = f"{BASE}/company_base/search/es_dsl"
COLLECT_BASE = f"{BASE}/company_base/collect"

def get_headers():
    api_key = os.getenv("CORESIGNAL_API_KEY")
    if not api_key:
        raise RuntimeError("CORESIGNAL_API_KEY not set in environment.")
    return {
        "apikey": api_key,
        "accept": "application/json",
        "content-type": "application/json",
    }

def _es_search(url: str, body: dict):
    headers = get_headers()
    r = requests.post(url, json=body, headers=headers, timeout=30)
    if r.status_code == 422:
        print(f"[CoreSignal] search 422 for body: {body} at {url}")
        return []
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print(f"[CoreSignal] search error {r.status_code}: {r.text}")
        return []
    return r.json()

def _collect(url: str, company_id: int, fields=None):
    headers = get_headers()
    full_url = f"{url}/{company_id}"
    if fields:
        full_url += f"?fields={','.join(fields)}"
    try:
        r = requests.get(full_url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[CoreSignal] collect error: {e}")
        return None

def is_valid_company_match(company_data, search_name):
    """Validate if the company match is legitimate (not an agency/partner)"""
    if not company_data or not isinstance(company_data, dict):
        return False
    
    company_name = company_data.get('name', '').lower()
    search_name_lower = search_name.lower()
    
    # Skip agencies, partners, and service providers
    invalid_keywords = ['agency', 'agentur', 'partner', 'services', 'consulting', 'solutions']
    if any(keyword in company_name for keyword in invalid_keywords):
        return False
    
    # For well-known companies, be more strict
    if search_name_lower in ['shopify', 'tesla', 'uber', 'airbnb']:
        # Must contain the exact company name
        if search_name_lower not in company_name:
            return False
        # Must not be an agency/partner
        if any(keyword in company_name for keyword in invalid_keywords):
            return False
    
    return True


def get_full_company_data(name_or_domain: str, fields=None):
    """
    Attempt Multi-Source first, then Base if no match.
    Returns the company profile dict, list of posts, or None.
    """
    # Enhanced search queries for better company matching
    queries = [
        {"query": {"match_phrase": {"name": name_or_domain}}},
        {"query": {"wildcard": {"name.keyword": f"*{name_or_domain.lower()}*"}}},
        # Add exact match for well-known companies
        {"query": {"term": {"name.keyword": name_or_domain}}},
    ]
    
    # Add domain-based search if it looks like a domain
    if "." in name_or_domain:
        queries.append({"query": {"term": {"domain.keyword": name_or_domain.lower()}}})
    
    # Add company name variations for better matching
    if name_or_domain.lower() == "shopify":
        queries.extend([
            {"query": {"match_phrase": {"name": "Shopify Inc"}}},
            {"query": {"match_phrase": {"name": "Shopify.com"}}},
            {"query": {"term": {"domain.keyword": "shopify.com"}}},
            {"query": {"match_phrase": {"name": "Shopify"}}},
            # Add more specific queries to avoid agencies/partners
            {"query": {"bool": {"must": [{"match_phrase": {"name": "Shopify"}}, {"bool": {"must_not": [{"wildcard": {"name": "*Agency*"}}, {"wildcard": {"name": "*Agentur*"}}, {"wildcard": {"name": "*Partner*"}}]}}]}}},
        ])
    elif name_or_domain.lower() == "tesla":
        queries.extend([
            {"query": {"match_phrase": {"name": "Tesla Inc"}}},
            {"query": {"match_phrase": {"name": "Tesla Motors"}}},
            {"query": {"match_phrase": {"name": "Tesla"}}},
        ])
    elif name_or_domain.lower() == "uber":
        queries.extend([
            {"query": {"match_phrase": {"name": "Uber Technologies"}}},
            {"query": {"match_phrase": {"name": "Uber"}}},
        ])
    elif name_or_domain.lower() == "airbnb":
        queries.extend([
            {"query": {"match_phrase": {"name": "Airbnb Inc"}}},
            {"query": {"match_phrase": {"name": "Airbnb"}}},
        ])

    # 1. Multi-Source search & collect
    for q in queries:
        hits = _es_search(SEARCH_MULTI, q)
        if hits:
            # Filter for the most relevant match
            best_match = hits[0]
            for hit in hits:
                hit_name = hit.get("name", "").lower() if isinstance(hit, dict) else ""
                if name_or_domain.lower() in hit_name and len(hit_name) < len(best_match.get("name", "")):
                    best_match = hit
            
            cid = best_match.get("company_id") if isinstance(best_match, dict) else best_match
            if cid:
                result = _collect(COLLECT_MULTI, cid, fields)
                if result and is_valid_company_match(result, name_or_domain):
                    print(f"[CoreSignal] Found valid Multi-Source match: {result.get('name', 'Unknown')}")
                    return result
                elif result:
                    print(f"[CoreSignal] Skipping invalid Multi-Source match: {result.get('name', 'Unknown')}")
    print(f"[CoreSignal] no valid Multi-Source match for '{name_or_domain}'")

    # 2. Base Company search & collect fallback
    for q in queries:
        hits = _es_search(SEARCH_BASE, q)
        if hits:
            best_match = hits[0]
            for hit in hits:
                hit_name = hit.get("name", "").lower() if isinstance(hit, dict) else ""
                if name_or_domain.lower() in hit_name and len(hit_name) < len(best_match.get("name", "")):
                    best_match = hit
            
            cid = best_match.get("company_id") if isinstance(best_match, dict) else best_match
            if cid:
                result = _collect(COLLECT_BASE, cid, fields)
                if result and is_valid_company_match(result, name_or_domain):
                    print(f"[CoreSignal] Found valid Base Company match: {result.get('name', 'Unknown')}")
                    return result
                elif result:
                    print(f"[CoreSignal] Skipping invalid Base Company match: {result.get('name', 'Unknown')}")
    print(f"[CoreSignal] no valid Base Company match for '{name_or_domain}'")
    return None 