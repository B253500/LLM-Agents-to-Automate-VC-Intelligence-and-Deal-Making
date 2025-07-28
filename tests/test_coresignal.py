# coresignal_utils.py
"""
Utility module for interacting with the CoreSignal v2 Company APIs.
"""
import os
import time
import logging
import json
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv

# Load environment variables once
dotenv_loaded = load_dotenv()
API_KEY = os.getenv("CORESIGNAL_API_KEY") or ""
if not API_KEY:
    raise RuntimeError("CORESIGNAL_API_KEY missing in .env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CoreSignal v2 endpoints
BASE_URL = "https://api.coresignal.com/cdapi/v2"
SEARCH_MULTI = f"{BASE_URL}/company_multi_source/search/es_dsl"
COLLECT_MULTI = f"{BASE_URL}/company_multi_source/collect"
SEARCH_BASE = f"{BASE_URL}/company_base/search/es_dsl"
COLLECT_BASE = f"{BASE_URL}/company_base/collect"

# Reusable session for connection pooling and headers
session = requests.Session()
session.headers.update({
    "apikey": API_KEY,
    "accept": "application/json",
    "content-type": "application/json",
})

def _es_search(url: str, body: Dict) -> List[Dict]:
    """
    Perform an ES-DSL search against the given URL.
    Returns list of hits, or [] on no-match / unprocessable (422) / retryable rate-limit.
    """
    r = session.post(url, json=body, timeout=30)
    if r.status_code == 422:
        logger.debug("search 422 Unprocessable Entity: %s at %s", body, url)
        return []
    if r.status_code == 429:
        logger.warning("search rate limited, backing off and retrying")
        time.sleep(1)
        return _es_search(url, body)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        logger.error("search error %s: %s", r.status_code, r.text)
        return []
    return r.json()


def _collect(url: str, company_id: int, fields: Optional[List[str]] = None) -> Optional[Dict]:
    """
    Collect the full profile from the given URL + company_id.
    Optionally restrict to a list of `fields`.
    Returns dict on success, None on error.
    """
    full_url = f"{url}/{company_id}"
    params = {"fields": ",".join(fields)} if fields else {}
    r = session.get(full_url, params=params, timeout=30)
    if r.status_code == 429:
        logger.warning("collect rate limited, backing off and retrying")
        time.sleep(1)
        return _collect(url, company_id, fields)
    try:
        r.raise_for_status()
        return r.json()
    except requests.HTTPError:
        logger.error("collect error %s: %s", r.status_code, r.text)
        return None


def get_full_company_data(name_or_domain: str,
                          fields: Optional[List[str]] = None) -> Optional[Dict]:
    """
    Attempt Multi-Source search first, then fall back to Base Company.
    Queries performed: exact match_phrase, wildcard, domain term.
    Returns full company profile dict or None if not found.
    """
    queries = [
        {"query": {"match_phrase": {"name": name_or_domain}}},
        {"query": {"wildcard": {"name.keyword": f"*{name_or_domain.lower()}*"}}},
    ]
    if "." in name_or_domain:
        queries.append({"query": {"term": {"domain.keyword": name_or_domain.lower()}}})

    # Multi-Source
    for q in queries:
        hits = _es_search(SEARCH_MULTI, q)
        if hits:
            candidate = hits[0]
            cid = candidate.get("company_id") if isinstance(candidate, dict) else candidate
            if cid:
                return _collect(COLLECT_MULTI, cid, fields)
    logger.info("no Multi-Source match for '%s'", name_or_domain)

    # Base Company fallback
    for q in queries:
        hits = _es_search(SEARCH_BASE, q)
        if hits:
            candidate = hits[0]
            cid = candidate.get("company_id") if isinstance(candidate, dict) else candidate
            if cid:
                return _collect(COLLECT_BASE, cid, fields)
    logger.info("no Base Company match for '%s'", name_or_domain)
    return None


# --------------------------------------------------
# test_coresignal.py
# --------------------------------------------------
import argparse

from core.coresignal_utils import get_full_company_data

def map_data_explorer_to_api(manual: Dict) -> Dict:
    """Map Data Explorer JSON columns into CoreSignal API field names."""
    return {
        "company_id": manual.get("id"),
        "name": manual.get("company_name"),
        "legal_name": manual.get("company_legal_name"),
        "shorthand_name": manual.get("company_shorthand_name"),
        "description": manual.get("description"),
        "industry": manual.get("industry"),
        "domain": manual.get("website"),
        "size_range": manual.get("size"),
        "founded_year": int(manual.get("founded")) if manual.get("founded") else None,
        "status": manual.get("type"),
        "hq_city": manual.get("headquarters_city") 
                     or manual.get("headquarters_new_address", "").split(",")[0].strip(),
        "hq_country_iso2": manual.get("headquarters_country_restored"),
        "office_locations": manual.get("company_locations_collection"),
        "linkedin_followers": manual.get("followers"),
        "news_features": manual.get("company_updates_collection"),
        "funding_rounds": manual.get("company_funding_rounds_collection"),
        "acquisitions": manual.get("acquisition_list_source_1"),
        "competitors": manual.get("company_similar_collection"),
        "emails": manual.get("company_emails"),
        "phones": manual.get("company_phone_numbers"),
        "linkedin": manual.get("canonical_url"),
    }


def main():
    parser = argparse.ArgumentParser(description="Test CoreSignal data extraction and mapping")
    parser.add_argument("company", help="Company name or domain to lookup")
    parser.add_argument("--manual", help="Path to Data Explorer JSON file for manual mapping", default=None)
    parser.add_argument("--fields", nargs="*", help="Fields to fetch via API (optional)", default=None)
    args = parser.parse_args()

    # API lookup
    profile = get_full_company_data(args.company, args.fields)
    if profile:
        print(json.dumps(profile, indent=2, ensure_ascii=False))
    else:
        print("API lookup returned no data for", args.company)

    # Manual mapping test
    if args.manual:
        with open(args.manual) as f:
            manual = json.load(f)
        mapping = map_data_explorer_to_api(manual)
        print("\n[Manual Mapping Test]")
        print(json.dumps(mapping, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
