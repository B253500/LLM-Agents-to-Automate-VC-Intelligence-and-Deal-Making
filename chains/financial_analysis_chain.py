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
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

SYSTEM = """\
You are a VC financial analyst specializing in startup financial analysis.
Analyze the company's financial data and provide estimates in USD millions.

Return JSON with numeric fields:
  cash_burn_12m   – total cash burned in last 12 months (negative = profit)
  runway_months   – months until cash-out at current burn rate
  implied_valuation – simple post-money valuation if round info present
  revenue – current annual revenue
  projected_revenue – projected revenue for next year
  funding_sought – amount of funding being sought

If you cannot find reliable data for a field, set it to null instead of 0.
Provide realistic estimates based on the company's stage and sector.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Financial snippets:\n{context}\n")]
)


def run_financial_analysis_chain(profile: StartupProfile) -> StartupProfile:
    context = get_hybrid_context(
        profile, "funding OR revenue OR burn OR valuation", 3, 3
    )
    txt = llm.invoke(PROMPT.format(context=context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        # Only set values if they are not null/None and greater than 0 (except for burn which can be negative)
        if data.get("cash_burn_12m") is not None:
            profile.cash_burn_12m = float(data.get("cash_burn_12m"))
        if data.get("runway_months") is not None and data.get("runway_months", 0) > 0:
            profile.runway_months = float(data.get("runway_months"))
        if data.get("implied_valuation") is not None and data.get("implied_valuation", 0) > 0:
            profile.implied_valuation = float(data.get("implied_valuation"))
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[
            :10
        ]
    return profile

def run_financial_analysis_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    """Run financial analysis using extracted text as context."""
    context = full_text[:5000]  # Truncate if needed for prompt size
    txt = llm.invoke(PROMPT.format(context=context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        # Only set values if they are not null/None and greater than 0 (except for burn which can be negative)
        if data.get("cash_burn_12m") is not None:
            profile.cash_burn_12m = float(data.get("cash_burn_12m"))
        if data.get("runway_months") is not None and data.get("runway_months", 0) > 0:
            profile.runway_months = float(data.get("runway_months"))
        if data.get("implied_valuation") is not None and data.get("implied_valuation", 0) > 0:
            profile.implied_valuation = float(data.get("implied_valuation"))
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile
