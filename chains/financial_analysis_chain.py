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
from core.hybrid_context import get_hybrid_context

# ------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

SYSTEM = """\
You are a VC financial analyst.
Return JSON with three numeric keys (USD millions):
  cash_burn_12m   – total cash burned (negative = profit)
  runway_months   – months until cash-out at current burn
  implied_valuation – simple post-money valuation if round info present
If a value is unknown, output 0.
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
        profile.cash_burn_12m = float(data.get("cash_burn_12m", 0))
        profile.runway_months = float(data.get("runway_months", 0))
        profile.implied_valuation = float(data.get("implied_valuation", 0))
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[
            :10
        ]
    return profile
