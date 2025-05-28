"""
Technical Due-Diligence chain

1. Pulls relevant deck text from Chroma
2. Prompts GPT-4o-mini to rate tech maturity & moat
3. Updates the StartupProfile
"""

import json
from hashlib import sha1
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.vector_store import query_doc

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

SYSTEM = """\
You are a senior CTO performing technical due-diligence for VC deals.
Return JSON with exactly two keys:
  tech_maturity  – one of ["prototype","beta","production","enterprise"]
  moat_strength  – ≤25-word description of defensible IP / moat
If you find no clues, set both values to "unknown".
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Startup info:\n{context}\n")]
)


# ------------------------------------------------------------------
# Chain
# ------------------------------------------------------------------
def run_technical_dd_chain(profile: StartupProfile) -> StartupProfile:
    # 1 Gather context (deck text snippets)
    chunks = query_doc(profile.startup_id, "technology stack or architecture", k=4)
    context = "\n---\n".join(chunks) if chunks else "No additional context provided."

    # 2 LLM call
    response = LLM.invoke(PROMPT.format(context=context))
    raw = response.content.strip()

    # 3 Robust JSON extraction: take text between first '{' and last '}'
    first, last = raw.find("{"), raw.rfind("}")
    if first == -1 or last == -1 or last < first:
        raise ValueError("Could not locate JSON in LLM response")
    json_str = raw[first : last + 1]
    data = json.loads(json_str)

    # 4 Populate profile
    profile.tech_maturity = data.get("tech_maturity")
    profile.moat_strength = data.get("moat_strength")

    # 5 Guarantee deterministic ID (if missing)
    if not profile.startup_id:
        src = profile.name or context[:40]
        profile.startup_id = sha1(src.encode()).hexdigest()[:10]

    return profile
