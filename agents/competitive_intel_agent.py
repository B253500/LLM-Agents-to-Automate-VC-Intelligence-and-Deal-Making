from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from crewai_tools import EXASearchTool
from core.schemas import StartupProfile
from chains.competitive_intel_chain import run_competitive_intel_chain

exa_search_tool = EXASearchTool(
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
        updated = run_competitive_intel_chain(profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Find the main AI startup competitors for the startup's sector. Identify 3-4 specific AI startup competitors by name, and provide company details and traction.",
        agent=scout,
        expected_output="A comprehensive competitor analysis including company names, details, and traction.",
        callback=_callback,
    )
    return scout, task
