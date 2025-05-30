"""
Competitive-intelligence chain
• Returns list of top 3 competitors and one-line differentiation.
"""

import json
from hashlib import sha1
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile, Competitor
from core.vector_store import query_doc

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
    ctx = (
        "\n".join(query_doc(profile.startup_id, "competitor or competition", k=4))
        or "No competitive info."
    )

    txt = llm.invoke(PROMPT.format(context=ctx)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    data = json.loads(txt[first : last + 1])

    profile.top_competitors = [
        Competitor(**c) for c in data.get("top_competitors", [])[:3]
    ]

    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or ctx[:40]).encode()).hexdigest()[:10]

    return profile
