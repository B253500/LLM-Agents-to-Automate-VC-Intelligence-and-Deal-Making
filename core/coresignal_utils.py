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

def get_full_company_data(name_or_domain: str, fields=None):
    """
    Attempt Multi-Source first, then Base if no match.
    Returns the company profile dict, list of posts, or None.
    """
    queries = [
        {"query": {"match_phrase": {"name": name_or_domain}}},
        {"query": {"wildcard": {"name.keyword": f"*{name_or_domain.lower()}*"}}},
    ]
    if "." in name_or_domain:
        queries.append({"query": {"term": {"domain.keyword": name_or_domain.lower()}}})

    # 1. Multi-Source search & collect
    for q in queries:
        hits = _es_search(SEARCH_MULTI, q)
        if hits:
            first = hits[0]
            cid = first.get("company_id") if isinstance(first, dict) else first
            if cid:
                return _collect(COLLECT_MULTI, cid, fields)
    print(f"[CoreSignal] no Multi-Source match for '{name_or_domain}'")

    # 2. Base Company search & collect fallback
    for q in queries:
        hits = _es_search(SEARCH_BASE, q)
        if hits:
            first = hits[0]
            cid = first.get("company_id") if isinstance(first, dict) else first
            if cid:
                return _collect(COLLECT_BASE, cid, fields)
    print(f"[CoreSignal] no Base Company match for '{name_or_domain}'")
    return None 