"""
Market-sizing chain
• Estimates TAM/SAM/SOM (USD millions)
"""

import json
from hashlib import sha1
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.vector_store import query_doc

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

SYSTEM = """\
You are a market-research analyst.
Return JSON with numeric fields (USD millions):
  TAM SAM SOM
If unknown, output 0 for that field.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Company & sector info:\n{context}\n")]
)


def run_market_sizing_chain(profile: StartupProfile) -> StartupProfile:
    context = "\n".join(query_doc(profile.startup_id, "market size or sector", k=4))

    raw = llm.invoke(PROMPT.format(context=context)).content.strip()
    first, last = raw.find("{"), raw.rfind("}")
    data = json.loads(raw[first : last + 1])

    profile.TAM = float(data.get("TAM", 0))
    profile.SAM = float(data.get("SAM", 0))
    profile.SOM = float(data.get("SOM", 0))

    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[
            :10
        ]

    return profile
