import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile, Competitor
from core.hybrid_context import get_hybrid_context

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

SYSTEM = """\
You are a VC analyst mapping the competitive landscape.
Return JSON:
  top_competitors – array of up to 3 objects {{name, differentiator}}
If unknown, return empty array.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Sector context:\n{context}\n")]
)


def run_competitive_intel_chain(profile: StartupProfile) -> StartupProfile:
    ctx = get_hybrid_context(profile, "competitor OR competition", k_local=3, k_web=3)
    txt = llm.invoke(PROMPT.format(context=ctx)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        profile.top_competitors = [
            Competitor(**c) for c in data.get("top_competitors", [])[:3]
        ]
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or ctx[:40]).encode()).hexdigest()[:10]
    return profile
