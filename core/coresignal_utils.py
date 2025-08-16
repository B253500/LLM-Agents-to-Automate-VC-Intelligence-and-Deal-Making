import os
import requests

# Company mapping for direct access to known companies
COMPANY_MAPPING = {
    # Format: "search_name": {"company_id": id, "name": "Official Name"}
    "monzo": {"company_id": 10508195, "name": "Monzo Bank"},
    "monzo bank": {"company_id": 10508195, "name": "Monzo Bank"},
    "dropbox": {"company_id": 94064453, "name": "Dropbox Dash"},  # Correct ID from GUI
    "dropbox dash": {"company_id": 94064453, "name": "Dropbox Dash"},  # Correct ID from GUI
    "lunchbox": {"company_id": 98122914, "name": "Lunchbox"},  # Correct ID from GUI
    "snapchat": {"company_id": 3980663, "name": "Snapchat, Inc."},  # Correct ID from GUI
    "shopify": {"company_id": 29392321, "name": "SHOPIFY (USA) INC."},  # Correct ID from GUI
    # Added mappings provided by user
    "coinbase": {"company_id": 56407612, "name": "Coinbase, Inc."},
    "crunchbase": {"company_id": 1634413, "name": "Crunchbase"},
    "equity bee": {"company_id": 11708743, "name": "EquityBee"},
    "peloton": {"company_id": 10747243, "name": "Peloton"},
    "twine": {"company_id": 2860522, "name": "Twine"},
    # New mappings (user-provided)
    "airbnb": {"company_id": 98250174, "name": "Airbnb"},
    "aircall": {"company_id": 94700504, "name": "Aircall"},
    "almanac": {"company_id": 27892793, "name": "Almanac"},
    "capacity": {"company_id": 11910484, "name": "Capacity"},
    "databook": {"company_id": 11045609, "name": "DataBook"},
    "castle": {"company_id": 10134864, "name": "Castle"},
    "oscar health": {"company_id": 6044422, "name": "Oscar Health"},
    "oscar": {"company_id": 6044422, "name": "Oscar Health"},
    "kong": {"company_id": 11650204, "name": "Kong Inc."},
    "kong inc.": {"company_id": 11650204, "name": "Kong Inc."},
    "pendo": {"company_id": 7607159, "name": "Pendo.io"},
    "pendo-io": {"company_id": 7607159, "name": "Pendo.io"},
    "store.ai": {"company_id": 32035457, "name": "Store.ai"},
    "storeai": {"company_id": 32035457, "name": "Store.ai"},
    "tagmonkey": {"company_id": 2513003, "name": "TagMonkey"},
    "mixpanel": {"company_id": 5513025, "name": "Mixpanel"},
    "videopeel": {"company_id": 12105208, "name": "VideoPeel"},
    "winnie": {"company_id": 9752392, "name": "Winnie"},
    "zestful": {"company_id": 10636978, "name": "Zestful"},
}

# Global CoreSignal request budget per process (acts as per-memo cap in single-run workflows)
CORESIGNAL_MAX_CALLS = int(os.getenv("CORESIGNAL_MAX_CALLS", "3"))
_CORESIGNAL_CALLS_USED = 0

def _consume_budget() -> bool:
    """Returns True if a CoreSignal API call may proceed; False if budget exhausted."""
    global _CORESIGNAL_CALLS_USED
    if _CORESIGNAL_CALLS_USED >= CORESIGNAL_MAX_CALLS:
        print(f"[CoreSignal] Call budget exhausted ({_CORESIGNAL_CALLS_USED}/{CORESIGNAL_MAX_CALLS}). Skipping.")
        return False
    _CORESIGNAL_CALLS_USED += 1
    return True

def get_company_id_from_mapping(search_name: str):
    """Get company ID from mapping if available"""
    search_lower = search_name.lower().strip()
    
    # Try exact match first
    if search_lower in COMPANY_MAPPING:
        return COMPANY_MAPPING[search_lower]["company_id"]
    
    # Try partial matches
    for key, value in COMPANY_MAPPING.items():
        if search_lower in key or key in search_lower:
            return value["company_id"]
    
    return None

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
    if not _consume_budget():
        return []
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
    
    # The API returns company IDs directly, not full data
    company_ids = r.json()
    if isinstance(company_ids, list):
        # Convert company IDs to hit format for compatibility
        hits = []
        for company_id in company_ids:
            hits.append({"company_id": company_id})
        return hits
    else:
        print(f"[CoreSignal] Unexpected response format: {type(company_ids)}")
        return []

def _collect(url: str, company_id: int, fields=None):
    if not _consume_budget():
        return None
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
    
    # More flexible validation - accept companies that are similar or contain the search term
    from difflib import SequenceMatcher
    
    # Calculate similarity
    similarity = SequenceMatcher(None, search_name_lower, company_name).ratio()
    
    # Accept if:
    # 1. Exact match
    if search_name_lower == company_name:
        return True
    
    # 2. High similarity (>70%) - reasonable threshold
    if similarity > 0.7:
        return True
    
    # 3. Search term is contained in company name (but not too long)
    if search_name_lower in company_name and len(company_name) <= len(search_name_lower) + 15:
        return True
    
    # 4. Company name contains search term with common variations
    if any(variation in company_name for variation in [search_name_lower, search_name_lower.replace(' ', ''), search_name_lower.replace(' ', '-')]):
        return True
    
    # 5. Company name starts with search term (for companies like "Monzo Bank")
    if company_name.startswith(search_name_lower):
        return True
    
    # 6. Company name ends with search term (for companies like "Bank of Monzo")
    if company_name.endswith(search_name_lower):
        return True
    
    # Reject if company name contains words that suggest it's not the main company
    suspicious_words = ['maxdisplays', 'polaris', 'rns', 'woking', 'electronic', 'barsava']
    if any(word in company_name.lower() for word in suspicious_words):
        return False
    
    # Must not be an agency/partner
    if any(keyword in company_name for keyword in invalid_keywords):
        return False
    
    return False


def get_full_company_data(name_or_domain: str, fields=None, website=None):
    """
    Enhanced company search using website + name combination for better accuracy.
    Returns the company profile dict, list of posts, or None.
    """
    from difflib import SequenceMatcher
    
    # Check mapping first for known companies
    mapped_company_id = get_company_id_from_mapping(name_or_domain)
    if mapped_company_id:
        print(f"[CoreSignal] Found company in mapping: {name_or_domain} -> ID {mapped_company_id}")
        result = _collect(COLLECT_BASE, mapped_company_id, fields)
        if result:
            print(f"[CoreSignal] ✅ Retrieved mapped company: {result.get('name', 'Unknown')}")
            return result
        else:
            print(f"[CoreSignal] ❌ Failed to retrieve mapped company ID {mapped_company_id}")
    
    # Continue with normal search if not in mapping
    
    def calculate_similarity(str1, str2):
        """Calculate string similarity using SequenceMatcher"""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def find_best_match(hits, search_name):
        """Find the best match using intelligent ranking"""
        if not hits:
            return None, 0
        
        search_name_lower = search_name.lower()
        best_match = None
        best_score = 0
        
        for hit in hits:
            # Handle both company IDs and full company data
            if isinstance(hit, dict) and "company_id" in hit:
                # This is a company ID from search - we need to collect the data first
                company_id = hit.get("company_id")
                # For now, just return the first company ID as a simple approach
                return hit, 50  # Give it a reasonable score
            
            hit_name = hit.get("name", "").lower() if isinstance(hit, dict) else ""
            if not hit_name:
                continue
            
            # Calculate multiple similarity scores
            exact_match = hit_name == search_name_lower
            contains_search = search_name_lower in hit_name
            similarity = calculate_similarity(hit_name, search_name_lower)
            
            # Scoring system (higher is better)
            score = 0
            
            # Exact match gets highest score
            if exact_match:
                score = 100
            # Contains search term
            elif contains_search:
                score = 50 + similarity * 30
            # Similar names
            else:
                score = similarity * 40
            
            # Bonus for shorter names (prefer "Dropbox" over "Dropbox International Holdings")
            if contains_search:
                length_penalty = min(len(hit_name) - len(search_name_lower), 20)
                score -= length_penalty
            
            # Bonus for legal entity indicators
            legal_indicators = ['inc', 'corp', 'llc', 'ltd', 'limited', 'corporation']
            if any(indicator in hit_name for indicator in legal_indicators):
                score += 10
            
            # Penalty for suspicious words
            suspicious_words = ['maxdisplays', 'polaris', 'rns', 'woking', 'electronic', 'barsava']
            if any(word in hit_name for word in suspicious_words):
                score -= 50
            
            if score > best_score:
                best_score = score
                best_match = hit
        
        return best_match, best_score
    
    def search_by_domain(domain):
        """Search by domain for exact website match"""
        if not domain:
            return None
        
        # Clean domain (remove protocol, www, etc.)
        clean_domain = domain.lower()
        if clean_domain.startswith('http'):
            clean_domain = clean_domain.split('//')[-1]
        if clean_domain.startswith('www.'):
            clean_domain = clean_domain[4:]
        
        print(f"[CoreSignal] Searching by domain: {clean_domain}")
        
        # Try multiple domain variations
        domain_variations = [
            clean_domain,  # monzo.com
            f"www.{clean_domain}",  # www.monzo.com
            clean_domain.replace('www.', '')  # monzo.com (if already has www)
        ]
        
        for domain_var in domain_variations:
            print(f"[CoreSignal] Trying domain variation: {domain_var}")
            
            # Search by domain - try exact match first
            domain_query = {"query": {"term": {"domain.keyword": domain_var}}}
            
            # Also try website field
            website_query = {"query": {"term": {"website.keyword": domain_var}}}
            
            # Try Base Company first (more reliable)
            hits = _es_search(SEARCH_BASE, domain_query)
            if hits:
                print(f"[CoreSignal] Found {len(hits)} domain matches for {domain_var}")
                return hits[0]  # Return first match (should be unique for domain)
            
            # Try website field as fallback
            hits = _es_search(SEARCH_BASE, website_query)
            if hits:
                print(f"[CoreSignal] Found {len(hits)} website matches for {domain_var}")
                return hits[0]  # Return first match (should be unique for domain)
        
        return None
    

    
    # HIERARCHICAL APPROACH: Website first, then name-only if website fails
    
    # STRATEGY 1: Search by domain (most reliable)
    if website:
        print(f"[CoreSignal] Starting with website search: {website}")
        domain_result = search_by_domain(website)
        if domain_result:
            company_id = domain_result.get("company_id")
            if company_id:
                result = _collect(COLLECT_BASE, company_id)
                if result and is_valid_company_match(result, name_or_domain):
                    print(f"[CoreSignal] ✅ Found exact domain match: {result.get('name', 'Unknown')}")
                    return result
                else:
                    print(f"[CoreSignal] ❌ Domain match failed validation")
            else:
                print(f"[CoreSignal] ❌ No company ID found for domain")
        else:
            print(f"[CoreSignal] ❌ No domain matches found")
    
    # STRATEGY 2: Fallback to name-only search (only if website search failed)
    print(f"[CoreSignal] Website search failed, trying name-only search for: {name_or_domain}")
    
    # Try multiple search strategies from most specific to most general
    search_strategies = [
        # 1. Exact match (most specific)
        {"query": {"term": {"name.keyword": name_or_domain.lower()}}},
        # 2. Prefix match (starts with)
        {"query": {"prefix": {"name": name_or_domain.lower()}}},
        # 3. Wildcard match (contains)
        {"query": {"wildcard": {"name": f"*{name_or_domain.lower()}*"}}},
        # 4. Fuzzy match (fallback)
        {"query": {"match": {"name": name_or_domain.lower()}}}
    ]
    
    # Try each strategy until we find results
    hits = None
    strategy_used = None
    for i, strategy in enumerate(search_strategies):
        strategy_names = ["exact", "prefix", "wildcard", "fuzzy"]
        print(f"[CoreSignal] Trying {strategy_names[i]} search...")
        hits = _es_search(SEARCH_MULTI, strategy)
        if hits:  # Use any results we find
            strategy_used = strategy_names[i]
            print(f"[CoreSignal] Found {len(hits)} results with {strategy_used} search")
            break
    
    if not hits:
        print(f"[CoreSignal] No results found with any search strategy")
        hits = []
    if hits:
        print(f"[CoreSignal] Found {len(hits)} potential Multi-Source matches for '{name_or_domain}'")
        best_match, best_score = find_best_match(hits, name_or_domain)
        if best_match and best_score > 10:  # Even lower threshold to accept more companies
            cid = best_match.get("company_id") if isinstance(best_match, dict) else best_match
            if cid:
                result = _collect(COLLECT_MULTI, cid, fields)
                if result and is_valid_company_match(result, name_or_domain):
                    print(f"[CoreSignal] Found valid Multi-Source match: {result.get('name', 'Unknown')} (score: {best_score:.1f})")
                    return result
                elif result:
                    print(f"[CoreSignal] Skipping invalid Multi-Source match: {result.get('name', 'Unknown')} (score: {best_score:.1f})")
        else:
            print(f"[CoreSignal] No Multi-Source matches met the score threshold (best score: {best_score:.1f})")
    else:
        print(f"[CoreSignal] No potential Multi-Source matches found for '{name_or_domain}'")
    
    print(f"[CoreSignal] no valid Multi-Source match for '{name_or_domain}'")

    # 2. Base Company search & collect (FALLBACK - SINGLE API CALL)
    # Try the same search strategies for Base Company
    hits = None
    strategy_used = None
    for i, strategy in enumerate(search_strategies):
        strategy_names = ["exact", "prefix", "wildcard", "fuzzy"]
        print(f"[CoreSignal] Trying Base Company {strategy_names[i]} search...")
        hits = _es_search(SEARCH_BASE, strategy)
        if hits:  # Use any results we find
            strategy_used = strategy_names[i]
            print(f"[CoreSignal] Found {len(hits)} Base Company results with {strategy_used} search")
            break
    
    if not hits:
        print(f"[CoreSignal] No Base Company results found with any search strategy")
        hits = []
    if hits:
        print(f"[CoreSignal] Found {len(hits)} potential Base Company matches for '{name_or_domain}'")
        
        # Try multiple matches instead of just the best one
        from difflib import SequenceMatcher
        best_matches = []
        for hit in hits[:1]:  # Limit to the top match to reduce API calls
            if isinstance(hit, dict) and "company_id" in hit:
                cid = hit.get("company_id")
                if cid:
                    result = _collect(COLLECT_BASE, cid, fields)
                    if result:
                        company_name = result.get('name', 'Unknown')
                        similarity = SequenceMatcher(None, name_or_domain.lower(), company_name.lower()).ratio()
                        best_matches.append((result, similarity))
                        print(f"[CoreSignal] Checking: {company_name} (similarity: {similarity:.2f})")
        
        # Sort by similarity and try each one
        best_matches.sort(key=lambda x: x[1], reverse=True)
        for result, similarity in best_matches:
            if is_valid_company_match(result, name_or_domain):
                print(f"[CoreSignal] ✅ Found valid Base Company match: {result.get('name', 'Unknown')} (similarity: {similarity:.2f})")
                return result
            else:
                print(f"[CoreSignal] ❌ Skipping invalid Base Company match: {result.get('name', 'Unknown')} (similarity: {similarity:.2f})")
        
        print(f"[CoreSignal] No valid Base Company matches found after trying {len(best_matches)} companies")
    else:
        print(f"[CoreSignal] No potential Base Company matches found for '{name_or_domain}'")
    
    print(f"[CoreSignal] no valid company match for '{name_or_domain}'")
    return None 