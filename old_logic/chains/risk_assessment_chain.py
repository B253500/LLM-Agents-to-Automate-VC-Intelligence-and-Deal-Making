"""
Risk-assessment chain
Aggregates red-flags across all profile fields.
"""

import json
from pathlib import Path
from hashlib import sha1

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

SYSTEM = """\
You are an investment-risk officer specializing in startup risk assessment.
Analyze the startup profile and identify potential risk factors.

Return JSON with:
  risk_flags – array of short risk descriptions (≤5 words each)
  risk_score – float 0-1 (0 = low risk, 1 = high risk)
  risk_summary – brief summary of key risks

Consider factors like:
- Market size and competition
- Team experience and track record
- Financial health and runway
- Technology maturity
- Regulatory risks
- Market timing

If insufficient data to assess risks, set risk_score to null and risk_flags to empty array.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Profile:\n```json\n{profile}\n```")]
)


def run_risk_assessment_chain(profile: StartupProfile) -> StartupProfile:
    txt = llm.invoke(PROMPT.format(profile=profile.model_dump_json())).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        profile.risk_flags = data.get("risk_flags", [])
        risk_score = data.get("risk_score")
        if risk_score is not None:
            profile.risk_score = float(risk_score)
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or "risk").encode()).hexdigest()[:10]
    return profile

def run_risk_assessment_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    """Run risk assessment using extracted text as context."""
    context = full_text[:5000]  # Truncate if needed for prompt size
    # Use the same prompt but replace the profile with the context
    txt = llm.invoke(PROMPT.format(profile=context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        profile.risk_flags = data.get("risk_flags", [])
        risk_score = data.get("risk_score")
        if risk_score is not None:
            profile.risk_score = float(risk_score)
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or "risk").encode()).hexdigest()[:10]
    return profile
