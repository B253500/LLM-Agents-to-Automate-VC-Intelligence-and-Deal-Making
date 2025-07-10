import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile, Competitor
from core.hybrid_context import get_hybrid_context

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)

def web_search_competitive_context(company_name, sector):
    # Placeholder: Integrate EXA, Perplexity, or other API here
    # Return a string with web search results
    return ""

SYSTEM = """
You are a VC analyst mapping the competitive landscape.
Analyze the company's sector and provide:
- Up to 3 direct competitors (name, differentiator)
- A concise summary of the competitive landscape
- Key competitive threats and opportunities
- Any recent news or changes (use web search context if available)
- Attribute sources where possible
Return JSON with a 'top_competitors' array and a 'summary' field.
If unknown, return empty array.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Sector context:\n{context}\nWeb search context:\n{web_context}\n")
])

def run_competitive_intel_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    context = full_text[:5000]
    web_context = web_search_competitive_context(profile.name, profile.sector)
    txt = llm.invoke(PROMPT.format(context=context, web_context=web_context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        profile.top_competitors = [Competitor(**c) for c in data.get("top_competitors", [])[:3]]
        if data.get("summary"):
            profile.competitive_summary = data.get("summary")
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile

def run_competitive_intel_chain(profile: StartupProfile) -> StartupProfile:
    # Build a context string from the profile fields for competitive analysis
    context = f"""
Company: {getattr(profile, 'name', '')}
Sector: {getattr(profile, 'sector', '')}
Product: {getattr(profile, 'tech_stack', '')}
"""
    txt = llm.invoke(PROMPT.format(context=context, web_context="")).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        profile.top_competitors = [
            Competitor(**c) for c in data.get("top_competitors", [])[:3]
        ]
        if data.get("summary"):
            profile.competitive_summary = data.get("summary")
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile
