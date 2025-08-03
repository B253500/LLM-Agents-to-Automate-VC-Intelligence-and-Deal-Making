from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from crewai_tools import EXASearchTool
from core.schemas import StartupProfile
from chains.competitive_intel_chain import run_competitive_intel_chain
from core.perplexity_utils import search_perplexity
from dotenv import load_dotenv
import os
from pathlib import Path
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
exa_api_key = os.getenv("EXA_API_KEY")

exa_search_tool = EXASearchTool(
    api_key=exa_api_key,
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

llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

# Competitive landscape generation moved to chains/competitive_intel_chain.py

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
        # Call the competitive intelligence chain - let the chain handle all analysis
        from chains.competitive_intel_chain import run_competitive_intel_chain
        from core.hybrid_context import get_hybrid_context
        
        # Get comprehensive context including all extracted data
        comprehensive_context = get_hybrid_context(profile, "competitive analysis competitors", use_reports=False)
        
        print("[Competitive Intel] Running comprehensive competitive intelligence chain...")
        updated = run_competitive_intel_chain(profile, comprehensive_context)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Find the main AI startup competitors for the startup's sector. Identify exactly 3 specific AI startup competitors by name, and provide company details and traction.",
        agent=scout,
        expected_output="A comprehensive competitor analysis including company names, details, and traction.",
        callback=_callback,
    )
    return scout, task
