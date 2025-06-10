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
You are an investment-risk officer.
Given a JSON StartupProfile, return JSON:
  risk_flags – array of short strings (≤5 words)
  risk_score – float 0-1 (higher = riskier)
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
        profile.risk_score = float(data.get("risk_score", 0.0))
    except (ValueError, TypeError) as e:
        print(f"Error processing risk assessment data: {e}")
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or "risk").encode()).hexdigest()[:10]
    return profile
