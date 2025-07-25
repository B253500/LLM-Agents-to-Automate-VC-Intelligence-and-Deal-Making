"""
Financial-analysis chain
• Extracts annual burn, runway, implied valuation.
"""

import json
from hashlib import sha1
from pathlib import Path

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
    # Placeholder: Integrate EXA, Perplexity, or other API here
    # Return a string with web search results
    return ""

SYSTEM = """
You are a VC financial analyst specializing in startup financial analysis.
Analyze the company's financial data and provide:
- Key metrics (burn, runway, valuation, revenue, funding sought)
- A concise summary of financial health and risks
- Commentary on missing data and red flags
- Any recent financial news (use web search context if available)
- Attribute sources where possible
Return JSON with numeric fields and a 'summary' field.
If you cannot find reliable data for a field, set it to null instead of 0.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Financial snippets:\n{context}\nWeb search context:\n{web_context}\n")
])

def run_financial_analysis_chain(profile: StartupProfile) -> StartupProfile:
    # Build a context string from the profile fields for financial analysis
    context = f"""
Funding: {getattr(profile, 'funding_stage', '')}
Revenue: {getattr(profile, 'revenue', '')}
Prior Exits: {getattr(profile, 'prior_exits', '')}
Sector: {getattr(profile, 'sector', '')}
"""
    # Optionally, add more fields as needed
    txt = llm.invoke(PROMPT.format(context=context, web_context="")).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        if data.get("cash_burn_12m") is not None:
            profile.cash_burn_12m = float(data.get("cash_burn_12m"))
        if data.get("runway_months") is not None and data.get("runway_months", 0) > 0:
            profile.runway_months = float(data.get("runway_months"))
        if data.get("implied_valuation") is not None and data.get("implied_valuation", 0) > 0:
            profile.implied_valuation = float(data.get("implied_valuation"))
        if data.get("summary"):
            profile.financial_summary = data.get("summary")
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile
