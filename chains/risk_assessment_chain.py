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
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

SYSTEM = """\
You are an investment-risk officer specializing in startup risk assessment.
Analyze the startup profile and identify potential risk factors.

Return JSON with:
  risk_flags – array of short risk descriptions (≤5 words each)
  risk_summary – brief summary of key risks

Consider factors like:
- Market size and competition
- Team experience and track record
- Financial health and runway
- Technology maturity
- Regulatory risks
- Market timing

If insufficient data to assess risks, set risk_flags to empty array.
Note: Do not provide a numerical risk score as it would be unreliable without clear methodology.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Profile:\n```json\n{profile}\n```")]
)


def run_risk_assessment_chain(profile: StartupProfile) -> StartupProfile:
    # Truncate profile data if it's too large to avoid context length exceeded
    profile_json = profile.model_dump_json()
    if len(profile_json) > 10000:  # If profile is very large, use a summary
        # Create a simplified profile with key fields only
        simplified_profile = {
            "name": profile.name,
            "sector": profile.sector,
            "funding_stage": profile.funding_stage,
            "TAM": profile.TAM,
            "revenue": profile.revenue,
            "top_competitors": profile.top_competitors[:3] if profile.top_competitors else None,  # Limit competitors
            "executives": profile.executives[:5] if profile.executives else None  # Limit executives
        }
        profile_json = json.dumps(simplified_profile)
    
    txt = llm.invoke(PROMPT.format(profile=profile_json)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        profile.risk_flags = data.get("risk_flags", [])
        # Note: risk_score is intentionally not set as it's unreliable without clear methodology
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
        # Note: risk_score is intentionally not set as it's unreliable without clear methodology
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or "risk").encode()).hexdigest()[:10]
    return profile
