from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from crewai_tools import EXASearchTool
from core.schemas import StartupProfile
from chains.competitive_intel_chain import run_competitive_intel_chain
from core.perplexity_utils import search_perplexity
import re
import os

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

    def _callback(*_):
        # 1. Run the core competitive intel chain
        updated = run_competitive_intel_chain(profile)
        # 2. Enrich competitor details
        if hasattr(updated, 'top_competitors') and updated.top_competitors:
            enriched = enrich_competitor_details([c for c in updated.top_competitors])
            updated.enriched_top_competitors = enriched
        return updated.model_dump_json(indent=2)

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
