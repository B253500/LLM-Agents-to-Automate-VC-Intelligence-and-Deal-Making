import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context
from core.perplexity_utils import search_perplexity

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

def web_search_market_context(company_name, sector):
    if not company_name and not sector:
        return ""
    query = f"Latest market size, growth rate, and trends for {company_name or 'the company'} in the {sector or ''} sector. Provide TAM, SAM, SOM if available, and cite sources."
    result = search_perplexity(query)
    return result or ""

SYSTEM = """
You are a market research analyst for venture capital.
For the given company and sector, provide a detailed, structured market analysis including:
- Challenges: A bulleted list of the main pain points and obstacles in the market.
- Drivers: A bulleted list of growth drivers and positive trends.
- Size: A narrative paragraph with the latest available numbers (TAM, SAM, SOM if possible), growth rates (CAGR), and sources. If specific data is unavailable, explain why and provide the closest relevant market size.
Leave the current Discussion logic in place.
Return your answer as a multi-section, multi-bullet, multi-paragraph analysis suitable for a VC investment memo.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Company & sector info:\n{context}\nWeb search context:\n{web_context}\n")
])


def run_market_sizing_chain(profile: StartupProfile) -> StartupProfile:
    context = get_hybrid_context(
        profile, "market size OR TAM OR SAM OR SOM OR industry", 3, 3
    )
    web_context = web_search_market_context(profile.name, profile.sector)
    prompt_vars = {"context": context, "web_context": web_context}
    template_strs = []
    for msg in getattr(PROMPT, 'messages', []):
        if hasattr(msg, 'prompt'):
            template_strs.append(str(msg.prompt))
        elif hasattr(msg, 'template'):
            template_strs.append(str(msg.template))
        else:
            template_strs.append(str(msg))
    template_str = ' '.join(template_strs)
    txt = llm.invoke(PROMPT.format(**prompt_vars)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        if data.get("TAM") is not None and data.get("TAM", 0) > 0:
            profile.TAM = float(data.get("TAM"))
        if data.get("SAM") is not None and data.get("SAM", 0) > 0:
            profile.SAM = float(data.get("SAM"))
        if data.get("SOM") is not None and data.get("SOM", 0) > 0:
            profile.SOM = float(data.get("SOM"))
        if data.get("summary"):
            profile.market_summary = data.get("summary")
        # Store original strings and reasoning if present
        if data.get("TAM_original"):
            profile.TAM_original = data["TAM_original"]
        if data.get("SAM_original"):
            profile.SAM_original = data["SAM_original"]
        if data.get("SOM_original"):
            profile.SOM_original = data["SOM_original"]
        if data.get("reasoning"):
            profile.market_reasoning = data["reasoning"]
    except Exception as e:
        print(f"[Market Sizing Parsing Error] {e}")
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile

def run_market_sizing_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    context = full_text[:5000]
    web_context = web_search_market_context(profile.name, profile.sector)
    txt = llm.invoke(PROMPT.format(context=context, web_context=web_context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        if data.get("TAM") is not None and data.get("TAM", 0) > 0:
            profile.TAM = float(data.get("TAM"))
        if data.get("SAM") is not None and data.get("SAM", 0) > 0:
            profile.SAM = float(data.get("SAM"))
        if data.get("SOM") is not None and data.get("SOM", 0) > 0:
            profile.SOM = float(data.get("SOM"))
        if data.get("summary"):
            profile.market_summary = data.get("summary")
        # Store original strings and reasoning if present
        if data.get("TAM_original"):
            profile.TAM_original = data["TAM_original"]
        if data.get("SAM_original"):
            profile.SAM_original = data["SAM_original"]
        if data.get("SOM_original"):
            profile.SOM_original = data["SOM_original"]
        if data.get("reasoning"):
            profile.market_reasoning = data["reasoning"]
    except Exception as e:
        print(f"[Market Sizing Parsing Error] {e}")
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile
