import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

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


def run_technical_dd_chain(profile: StartupProfile) -> StartupProfile:
    context = get_hybrid_context(
        profile, "technology stack OR product OR patents OR infrastructure", 3, 3
    )
    txt = llm.invoke(PROMPT.format(context=context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        # Flatten dicts if needed
        if isinstance(data.get("tech_maturity"), dict):
            data["tech_maturity"] = str(data["tech_maturity"])
        if isinstance(data.get("moat_strength"), dict):
            data["moat_strength"] = str(data["moat_strength"])
        profile.tech_maturity = data.get("tech_maturity")
        profile.moat_strength = data.get("moat_strength")
    except (ValueError, TypeError) as e:
        print(f"Error processing technical due diligence data: {e}")
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[
            :10
        ]
    return profile
