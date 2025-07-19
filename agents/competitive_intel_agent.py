from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from crewai_tools import EXASearchTool
from core.schemas import StartupProfile, Competitor
from core.perplexity_utils import search_perplexity
from core.hybrid_context import get_hybrid_context
import re
import os
import json
from hashlib import sha1

exa_search_tool = EXASearchTool(
    api_key=os.environ["EXA_API_KEY"],
    type='neural',
    use_autoprompt=True,
    category='company',
    startPublishedDate='2021-10-01T00:00:00.000Z',
    excludeText=[
        'OpenAI', 'Anthropic', 'Google', 'Mistral', 'Microsoft', 'Nvidia',
        'general AI market', 'overall AI industry', 'IBM', 'Mistral'
    ],
    numResults=20
)

llm = ChatOpenAI(model="gpt-4", temperature=0.2)

SYSTEM = """
You are a VC analyst mapping the competitive landscape.
For each of the top 3-5 direct competitors, return:
- name
- website (official URL, always try to find it)
- total funding (if available)
- product_offering (2-3 sentence description)
- traction (major customers, partnerships, or market presence)
- differentiator (what makes them unique)
Use web search context if available. Return as a JSON array 'top_competitors'.
"""
PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Sector context:\n{context}\nWeb search context:\n{web_context}\n")
])

def enrich_competitor_details(competitors):
    enriched = []
    for comp in competitors:
        # Convert to dict if it's a Pydantic model
        if hasattr(comp, 'dict'):
            comp = comp.dict()
        # Enrich website if missing
        if not comp.get('website') and comp.get('name'):
            query = f"What is the official website for {comp['name']} (battery technology company)?"
            website = search_perplexity(query)
            if website and 'http' in website:
                match = re.search(r"https?://[\w./-]+", website)
                if match:
                    comp['website'] = match.group(0)
        # Enrich product_offering if missing
        if not comp.get('product_offering') and comp.get('name'):
            query = f"What is the main product or technology offering of {comp['name']} in battery technology?"
            product = search_perplexity(query)
            if product:
                comp['product_offering'] = product.strip()
        enriched.append(comp)
    return enriched


def build_competitive_intel_agent(profile: StartupProfile, trace_id=None):
    scout = Agent(
        role="AI Startup Intelligence Specialist",
        goal="Identify and analyze relevant AI startups within specific AI subsegment markets.",
        backstory="Expert in mapping competitive landscapes for specific AI verticals. Specialized in identifying real, named emerging startups and scale-ups rather than tech giants. Known for finding verifiable information about startups' funding, technology, and market focus.",
        tools=[exa_search_tool],
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(context, *args, **kwargs):
        # In hierarchical mode, ignore incoming context and start fresh
        profile = StartupProfile()
        if deck_payload:
            print(f"[competitive_intel_agent] Deck text (first 200 chars): {deck_payload.get('text', '')[:200]}")
        else:
            print(f"[competitive_intel_agent] No deck_payload provided.")
        # Build context and prompt
        from core.hybrid_context import safe_truncate
        ctx = get_hybrid_context(profile, "competitor OR competitive OR landscape OR comparison", 3, 3)
        ctx = safe_truncate(ctx, max_chars=1500)
        deck_text = safe_truncate(deck_payload.get('text', '') if deck_payload else '', max_chars=1500)
        prompt_context = f"{ctx}\n\nFull Deck Text:\n{deck_text}"
        print(f"[competitive_intel_agent] LLM prompt context (first 300 chars): {prompt_context[:300]}")
        raw = llm.invoke(PROMPT.format(context=prompt_context)).content.strip()
        print(f"[competitive_intel_agent] LLM raw output (first 300 chars): {raw[:300]}")
        # --- Chain logic inlined here ---
        context_str = f"""
Company: {getattr(profile, 'name', '')}
Sector: {getattr(profile, 'sector', '')}
Product: {getattr(profile, 'tech_stack', '')}
"""
        txt = llm.invoke(PROMPT.format(context=context_str, web_context="")).content.strip()
        first, last = txt.find("{"), txt.rfind("}")
        if first != -1 and last != -1:
            try:
                data = json.loads(txt[first : last + 1])
                profile.top_competitors = [Competitor(**c) for c in data.get("top_competitors", [])[:3]]
                if data.get("summary"):
                    profile.competitive_summary = data.get("summary")
            except Exception as e:
                print(f"[Competitive Intel Parsing Error] {e}")
        if not profile.startup_id:
            profile.startup_id = sha1((profile.name or ctx[:40]).encode()).hexdigest()[:10]
        # 2. Enrich competitor details
        if hasattr(profile, 'top_competitors') and profile.top_competitors:
            enriched = enrich_competitor_details([c for c in profile.top_competitors])
            profile.enriched_top_competitors = enriched
        print(f"[competitive_intel_agent] Output profile: {profile.model_dump()}")
        output = profile.model_dump()
        print(f"[competitive_intel_agent] Output type: {type(output)}")
        print(f"[competitive_intel_agent] Output keys: {list(output.keys()) if isinstance(output, dict) else 'N/A'}")
        return output

    task = Task(
        description="Find the main AI startup competitors for the startup's sector. Identify 3-4 specific AI startup competitors by name, provide company details and traction, and enrich with web search.",
        agent=scout,
        expected_output="A comprehensive competitor analysis including company names, details, traction, and web-enriched data.",
        callback=_callback,
    )
    return scout, task


def build_competitive_chain_agent(profile):
    def chain_callback(*_):
        from chains.competitive_intel_chain import run_competitive_intel_chain
        updated_profile = run_competitive_intel_chain(profile)
        return updated_profile.model_dump()
    agent = Agent(
        role="Competitive Intel Extractor",
        goal="Extract competitive intelligence data from the deck.",
        backstory="A specialized agent for extracting competitive intelligence data from pitch decks.",
        verbose=True
    )
    task = Task(
        description="Extract competitive intelligence data from the deck.",
        agent=agent,
        callback=chain_callback,
        args=[profile.model_dump()],
        expected_output="Profile with competitive intelligence fields extracted."
    )
    return agent, task
