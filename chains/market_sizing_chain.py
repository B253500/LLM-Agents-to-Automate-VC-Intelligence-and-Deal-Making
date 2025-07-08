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
You are a market-research analyst specializing in market sizing for startups.
Analyze the company's sector and provide market size estimates in USD millions.

Return JSON with numeric fields:
  TAM (Total Addressable Market)
  SAM (Serviceable Available Market) 
  SOM (Serviceable Obtainable Market)

If you cannot find reliable data for a field, set it to null instead of 0.
Provide realistic estimates based on the company's sector and target market.
Include growth_rate if available.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Company & sector info:\n{context}\n")]
)


def run_market_sizing_chain(profile: StartupProfile) -> StartupProfile:
    context = get_hybrid_context(
        profile, "market size OR TAM OR SAM OR SOM OR industry", 3, 3
    )
    txt = llm.invoke(PROMPT.format(context=context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        # Only set values if they are not null/None and greater than 0
        if data.get("TAM") is not None and data.get("TAM", 0) > 0:
            profile.TAM = float(data.get("TAM"))
        if data.get("SAM") is not None and data.get("SAM", 0) > 0:
            profile.SAM = float(data.get("SAM"))
        if data.get("SOM") is not None and data.get("SOM", 0) > 0:
            profile.SOM = float(data.get("SOM"))
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[
            :10
        ]
    return profile

def run_market_sizing_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    """Run market sizing using extracted text as context."""
    context = full_text[:5000]  # Truncate if needed for prompt size
    txt = llm.invoke(PROMPT.format(context=context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        # Only set values if they are not null/None and greater than 0
        if data.get("TAM") is not None and data.get("TAM", 0) > 0:
            profile.TAM = float(data.get("TAM"))
        if data.get("SAM") is not None and data.get("SAM", 0) > 0:
            profile.SAM = float(data.get("SAM"))
        if data.get("SOM") is not None and data.get("SOM", 0) > 0:
            profile.SOM = float(data.get("SOM"))
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile
