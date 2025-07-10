import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)

def web_search_market_context(company_name, sector):
    # Placeholder: Integrate EXA, Perplexity, or other API here
    # Return a string with web search results
    return ""

SYSTEM = """
You are a market-research analyst specializing in market sizing for startups.
Analyze the company's sector and provide:
- Market size estimates in USD millions (TAM, SAM, SOM)
- A concise summary of the market opportunity
- Key drivers and challenges for this sector
- Any recent trends or news (use web search context if available)
- Attribute sources where possible
Return JSON with numeric fields and a 'summary' field.
If you cannot find reliable data for a field, set it to null instead of 0.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Company & sector info:\n{context}\nWeb search context:\n{web_context}\n")
])


def run_market_sizing_chain(profile: StartupProfile) -> StartupProfile:
    context = get_hybrid_context(
        profile, "market size OR TAM OR SAM OR SOM OR industry", 3, 3
    )
    # Provide all required variables for PROMPT
    prompt_vars = {"context": context}
    # Robustly check for required variables in PROMPT
    template_strs = []
    for msg in getattr(PROMPT, 'messages', []):
        if hasattr(msg, 'prompt'):
            template_strs.append(str(msg.prompt))
        elif hasattr(msg, 'template'):
            template_strs.append(str(msg.template))
        else:
            template_strs.append(str(msg))
    template_str = ' '.join(template_strs)
    if "{web_context}" in template_str:
        prompt_vars["web_context"] = ""
    # Add more variables as needed if template expects them
    txt = llm.invoke(PROMPT.format(**prompt_vars)).content.strip()
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
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile
