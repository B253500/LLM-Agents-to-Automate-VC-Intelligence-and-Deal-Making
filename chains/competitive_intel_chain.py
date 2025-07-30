import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile, Competitor
from core.hybrid_context import get_hybrid_context
import sys
sys.path.append('.')  # Ensure root is in path for import
from core.perplexity_utils import search_perplexity

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

def web_search_competitive_context(company_name, sector):
    """
    Use Perplexity to get up-to-date product/technology descriptions for top competitors in the sector.
    """
    if not company_name and not sector:
        return ""
    query = f"List 3-4 direct competitors to {company_name or 'the company'} in the {sector or ''} sector. For each, provide a concise description of their main product, technology, and differentiator."
    result = search_perplexity(query)
    return result or ""

SYSTEM = """
You are a VC analyst mapping the competitive landscape.
For each of the top 3-5 direct competitors, return:
- name
- website (official URL, always try to find it)
- total funding (if available)
- product_offering (2-3 sentence description)
- traction (major customers, partnerships, or market presence)
- differentiator (what makes them unique)
Use web search context if available. Return as a JSON array 'top_competitors'.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Sector context:\n{context}\nWeb search context:\n{web_context}\n")
])

def run_competitive_intel_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    context = full_text[:5000]
    web_context = web_search_competitive_context(profile.name, profile.sector)
    txt = llm.invoke(PROMPT.format(context=context, web_context=web_context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        competitors = data.get("top_competitors", [])
        if competitors:
            profile.top_competitors = [Competitor(**c) for c in competitors[:3]]
            print(f"[Competitive Intel] Found {len(profile.top_competitors)} competitors")
        else:
            print(f"[Competitive Intel] No competitors in JSON response")
        if data.get("summary"):
            profile.competitive_summary = data.get("summary")
    except Exception as e:
        print(f"[Competitive Intel] JSON parsing failed: {e}")
        print(f"[Competitive Intel] Raw response: {txt[:500]}...")
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile

def run_competitive_intel_chain(profile: StartupProfile) -> StartupProfile:
    # Build a context string from the profile fields for competitive analysis
    context = f"""
Company: {getattr(profile, 'name', '')}
Sector: {getattr(profile, 'sector', '')}
Product: {getattr(profile, 'tech_stack', '')}
"""
    txt = llm.invoke(PROMPT.format(context=context, web_context="")).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        competitors = data.get("top_competitors", [])
        if competitors:
            profile.top_competitors = [Competitor(**c) for c in competitors[:3]]
            print(f"[Competitive Intel] Found {len(profile.top_competitors)} competitors")
        else:
            print(f"[Competitive Intel] No competitors in JSON response")
        if data.get("summary"):
            profile.competitive_summary = data.get("summary")
    except Exception as e:
        print(f"[Competitive Intel] JSON parsing failed: {e}")
        print(f"[Competitive Intel] Raw response: {txt[:500]}...")
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile

def enrich_competitor_details(competitors):
    enriched = []
    for comp in competitors:
        # Enrich website if missing
        if not comp.get('website') and comp.get('name'):
            # Generic competitive intelligence queries that work for any sector
            query = f"What is the official website for {comp['name']} (technology company)?"
            website_result = search_perplexity(query, num_results=1)
            
            if website_result:
                # Extract website from the result
                website_match = re.search(r'https?://[^\s\)\]]+', website_result)
                if website_match:
                    comp['website'] = website_match.group(0)
            
            # Get product/technology information
            query = f"What is the main product or technology offering of {comp['name']}?"
            product_result = search_perplexity(query, num_results=1)
            if product_result:
                comp['product_offering'] = product_result.strip()
        enriched.append(comp)
    return enriched
