"""
Financial-analysis chain
• Extracts annual burn, runway, implied valuation.
"""

import json
from hashlib import sha1
from pathlib import Path
import re

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.vector_store import query_doc
from core.hybrid_context import get_hybrid_context

# ------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)

def web_search_financial_context(company_name):
    """Search for company financial data and valuation information with source attribution."""
    try:
        from core.perplexity_utils import search_perplexity
        
        # Search for company valuation and financial data
        search_queries = [
            f"What is the current valuation of {company_name}? Include the most recent funding rounds and valuation data.",
            f"What are the latest financial metrics for {company_name}? Include revenue, funding, and key financial indicators.",
            f"What is the funding history and valuation of {company_name}? Include all funding rounds and post-money valuations."
        ]
        
        web_data = []
        sources = []
        
        for query in search_queries:
            try:
                result = search_perplexity(query)
                if result and len(result.strip()) > 50:
                    web_data.append(result.strip())
                    # Extract URLs from the result
                    import re
                    urls = re.findall(r'https?://[^\s]+', result)
                    sources.extend(urls[:2])  # Limit to first 2 URLs per query
            except Exception as e:
                print(f"[Financial Analysis] Web search error for query '{query}': {e}")
                continue
        
        if web_data:
            combined_data = "\n\n".join(web_data)
            # Remove duplicate sources
            unique_sources = list(set(sources))
            source_links = "\n".join([f"Source: {url}" for url in unique_sources[:5]])  # Limit to 5 sources
            
            return f"""
Web Search Results for {company_name}:
{combined_data}

Sources:
{source_links}
"""
        else:
            return ""
            
    except Exception as e:
        print(f"[Financial Analysis] Web search error: {e}")
        return ""

# Simple cache for Crunchbase API calls to avoid repeated requests
_crunchbase_cache = {}

def fetch_crunchbase_funding_data(crunchbase_url):
    """Fetch funding and valuation data from Crunchbase URL with caching"""
    global _crunchbase_cache
    
    # Check cache first
    if crunchbase_url in _crunchbase_cache:
        print(f"[Financial Analysis] Using cached data for: {crunchbase_url}")
        return _crunchbase_cache[crunchbase_url]
    
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(crunchbase_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract funding information
            funding_data = {}
            
            # Look for valuation information
            valuation_selectors = [
                'span[data-test="valuation"]',
                '.valuation',
                '[data-test="post-money-valuation"]',
                '.post-money-valuation'
            ]
            
            for selector in valuation_selectors:
                elements = soup.select(selector)
                if elements:
                    funding_data['valuation'] = elements[0].get_text().strip()
                    break
            
            # Look for funding amount
            amount_selectors = [
                'span[data-test="money-raised"]',
                '.money-raised',
                '[data-test="funding-amount"]',
                '.funding-amount'
            ]
            
            for selector in amount_selectors:
                elements = soup.select(selector)
                if elements:
                    funding_data['funding_amount'] = elements[0].get_text().strip()
                    break
            
            # Look for round type
            round_selectors = [
                'span[data-test="round-type"]',
                '.round-type',
                '[data-test="funding-round"]',
                '.funding-round'
            ]
            
            for selector in round_selectors:
                elements = soup.select(selector)
                if elements:
                    funding_data['round_type'] = elements[0].get_text().strip()
                    break
            
            # Look for date
            date_selectors = [
                'span[data-test="funding-date"]',
                '.funding-date',
                '[data-test="date"]',
                '.date'
            ]
            
            for selector in date_selectors:
                elements = soup.select(selector)
                if elements:
                    funding_data['funding_date'] = elements[0].get_text().strip()
                    break
            
            # Cache the result
            _crunchbase_cache[crunchbase_url] = funding_data
            return funding_data
            
    except Exception as e:
        print(f"[Crunchbase Fetch Error] {e}")
        # Cache empty result to avoid repeated failed requests
        _crunchbase_cache[crunchbase_url] = {}
        return {}
    
    # Cache empty result
    _crunchbase_cache[crunchbase_url] = {}
    return {}

SYSTEM = """
You are a VC financial analyst specializing in startup financial analysis.
Extract all available financial metrics from the following text, even if not in a table.

IMPORTANT: 
1. If Crunchbase funding data is provided in the web_context, prioritize that data for valuation and funding information. Crunchbase data is authoritative and should be used for:
   - implied_valuation (from post-money valuation)
   - funding amounts
   - round types and dates

2. If web search results are provided, extract financial data from those sources and include the source URLs in your analysis. Web search data can provide:
   - Current valuation information
   - Recent funding rounds
   - Revenue estimates
   - Financial metrics from news articles and reports

Return a JSON object with as many of the following fields as possible:
- revenue (by year if available)
- MRR (monthly recurring revenue)
- GMV (gross merchandise volume)
- gross_profit
- cash_burn_12m
- runway_months
- implied_valuation (especially from Crunchbase data or web search)
- any other key financials

If a table is present, extract it as both markdown and JSON. If not, extract from running text.
If you cannot find reliable data for a field, set it to null. Do NOT guess, estimate, or hallucinate. Only extract numbers that are explicitly present in the text, tables, Crunchbase data, or web search results. If a value is not explicitly stated, return null for that field. Never invent or infer values.

When Crunchbase data is available, use it as the primary source for valuation and funding information. When web search data is available, use it to supplement and validate other financial information.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Financial snippets:\n{context}\nWeb search context:\n{web_context}\n")
])

def parse_money_string(s):
    s = s.replace(",", "").strip()
    match = re.match(r"\$?([\d\.]+)\s*([KMB]?)", s, re.IGNORECASE)
    if not match:
        return None
    num, suffix = match.groups()
    try:
        num = float(num)
    except (ValueError, TypeError):
        return None
    multiplier = {"": 1, "K": 1e3, "M": 1e6, "B": 1e9}
    return num * multiplier.get(suffix.upper(), 1)

def extract_financials_from_text(text):
    patterns = [
        (r"revenue[^\d$]*\$?([\d\.]+)\s*([KMB]?)", "revenue"),
        (r"MRR[^\d$]*\$?([\d\.]+)\s*([KMB]?)", "mrr"),
        (r"GMV[^\d$]*\$?([\d\.]+)\s*([KMB]?)", "gmv"),
        (r"gross profit[^\d$]*\$?([\d\.]+)\s*([KMB]?)", "gross_profit"),
        (r"cash burn[^\d$]*\$?([\d\.]+)\s*([KMB]?)", "cash_burn_12m"),
        (r"runway[^\d$]*([\d\.]+)\s*(months|mo|month)(?:\s|$)", "runway_months"),
        (r"implied valuation[^\d$]*\$?([\d\.]+)\s*([KMB]?)", "implied_valuation"),
    ]
    
    # Additional validation: exclude technical specifications
    technical_indicators = ['wh/l', 'wh/kg', 'watt', 'voltage', 'current', 'capacity', 'density', 'energy density']
    
    results = {}
    for pat, field in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            # Get the full matched text for context validation
            full_match = match.group(0)
            
            # Skip if the match contains technical indicators
            if any(indicator in full_match.lower() for indicator in technical_indicators):
                continue
                
            if field == "runway_months":
                num = match.group(1)
                results[field] = float(num)
            else:
                num, suffix = match.groups()[:2]
                results[field] = parse_money_string(num + (suffix or ""))
    return results

def value_in_text(value, text):
    """Check if the numeric value (as string) appears in the text (case-insensitive, ignoring commas)."""
    if value is None:
        return False
    if isinstance(value, float) or isinstance(value, int):
        value_str = f"{value:,.0f}".replace(",", "")
        return value_str in text.replace(",", "")
    return str(value) in text

def run_financial_analysis_chain(profile: StartupProfile, financial_context: str = "") -> StartupProfile:
    # If financial_context is provided, use it; otherwise, build from profile fields
    if financial_context and financial_context.strip():
        context = financial_context
    else:
        context = f"""
Funding: {getattr(profile, 'funding_stage', '')}
Revenue: {getattr(profile, 'revenue', '')}
Prior Exits: {getattr(profile, 'prior_exits', '')}
Sector: {getattr(profile, 'sector', '')}
"""
    
    # Check if we have CoreSignal funding data with Crunchbase URLs
    crunchbase_data = ""
    if hasattr(profile, 'funding_rounds') and profile.funding_rounds:
        try:
            import json
            funding_rounds = json.loads(profile.funding_rounds) if isinstance(profile.funding_rounds, str) else profile.funding_rounds
            
            print(f"[Financial Analysis] Found {len(funding_rounds)} funding rounds to process")
            
            # Find the most recent significant funding round with a Crunchbase URL
            # Only process the first 3 rounds with valid URLs to avoid excessive API calls
            processed_count = 0
            max_rounds_to_process = 3
            
            for round_data in funding_rounds:
                if processed_count >= max_rounds_to_process:
                    print(f"[Financial Analysis] Reached limit of {max_rounds_to_process} rounds, stopping...")
                    break
                if isinstance(round_data, dict) and round_data.get('cb_url'):
                    cb_url = round_data['cb_url']
                    print(f"[Financial Analysis] Fetching data from Crunchbase: {cb_url}")
                    
                    # Fetch data from Crunchbase
                    funding_data = fetch_crunchbase_funding_data(cb_url)
                    processed_count += 1
                    if funding_data:
                        crunchbase_data = f"""
Crunchbase Funding Data:
- Round Type: {funding_data.get('round_type', 'Unknown')}
- Funding Amount: {funding_data.get('funding_amount', 'Unknown')}
- Valuation: {funding_data.get('valuation', 'Unknown')}
- Date: {funding_data.get('funding_date', 'Unknown')}
- Source: {cb_url}
"""
                        print(f"[Financial Analysis] Found Crunchbase data: {funding_data}")
                        break  # Only process the first successful round
                    else:
                        print(f"[Financial Analysis] No data found for {cb_url}, trying next round...")
                        continue
        except Exception as e:
            print(f"[Financial Analysis] Error processing funding rounds: {e}")
    
    # Add web search data for company valuation and financial information
    web_search_data = ""
    web_sources = []
    company_name = getattr(profile, 'name', '')
    if company_name and company_name.strip():
        print(f"[Financial Analysis] Searching web for financial data on {company_name}")
        web_search_data = web_search_financial_context(company_name)
        if web_search_data:
            print(f"[Financial Analysis] Found web search data for {company_name}")
            # Extract URLs from web search data
            import re
            urls = re.findall(r'https?://[^\s]+', web_search_data)
            web_sources = list(set(urls))  # Remove duplicates
            # Store web sources in profile
            profile.web_sources = web_sources
        else:
            print(f"[Financial Analysis] No web search data found for {company_name}")
    
    # Combine all context data
    combined_context = f"{context}\n\n{crunchbase_data}\n\n{web_search_data}"
    
    # Optionally, add more fields as needed
    txt = llm.invoke(PROMPT.format(context=context, web_context=combined_context)).content.strip()
    print("[Financial Chain] LLM raw output:", txt)
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        print("[Financial Chain] Parsed JSON:", data)
        # Only assign values if they are present in the original text/tables
        for field in ["cash_burn_12m", "runway_months", "implied_valuation", "revenue", "mrr", "gmv", "gross_profit"]:
            val = data.get(field)
            if val is not None and value_in_text(val, context):
                setattr(profile, field, float(val))
        if data.get("summary"):
            profile.financial_summary = data.get("summary")
        if data.get("financials_table"):
            profile.financials_table = data.get("financials_table")
        if data.get("financials_by_year"):
            profile.financials_by_year = data.get("financials_by_year")
    except Exception as e:
        print(f"[Financial Chain Parsing Error] {e}")
        pass
    # Regex fallback: extract from summary text if present
    summary_text = txt if isinstance(txt, str) else ""
    extracted = extract_financials_from_text(summary_text)
    print("[Financial Chain] Regex extracted:", extracted)
    if extracted:
        print("[Financial Chain] Context for extraction:", summary_text[:500] + "..." if len(summary_text) > 500 else summary_text)
    for k, v in extracted.items():
        if hasattr(profile, k) and v and value_in_text(v, context):
            setattr(profile, k, v)
    if not profile.startup_id:
        from hashlib import sha1
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile
