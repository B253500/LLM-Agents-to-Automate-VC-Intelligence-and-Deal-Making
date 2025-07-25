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
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

def web_search_financial_context(company_name):
    # Placeholder: Integrate EXA, Perplexity, or other API here
    # Return a string with web search results
    return ""

SYSTEM = """
You are a VC financial analyst specializing in startup financial analysis.
Extract all available financial metrics from the following text, even if not in a table.
Return a JSON object with as many of the following fields as possible:
- revenue (by year if available)
- MRR (monthly recurring revenue)
- GMV (gross merchandise volume)
- gross_profit
- cash_burn_12m
- runway_months
- implied_valuation
- any other key financials
If a table is present, extract it as both markdown and JSON. If not, extract from running text.
If you cannot find reliable data for a field, set it to null. Do NOT guess, estimate, or hallucinate. Only extract numbers that are explicitly present in the text or tables. If a value is not explicitly stated, return null for that field. Never invent or infer values.
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
    # Optionally, add more fields as needed
    txt = llm.invoke(PROMPT.format(context=context, web_context="")).content.strip()
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
