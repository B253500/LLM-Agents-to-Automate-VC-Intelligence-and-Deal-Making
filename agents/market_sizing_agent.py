from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from crewai_tools import EXASearchTool
from core.schemas import StartupProfile
from chains.market_sizing_chain import run_market_sizing_chain
from dotenv import load_dotenv
import os
load_dotenv()
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

llm = ChatOpenAI(model="gpt-4", temperature=0.2)

def build_market_sizing_agent(profile: StartupProfile, trace_id=None):
    analyst = Agent(
        role="Market size Research Analyst",
        goal="Research and analyze the market size TAM of AI subsegment markets focusing on specialized market sizes and growth rates.",
        backstory="Expert in doing research and calculating the market size TAM of specific subsegments of the AI market, and growth rates. Also search for sector-specific growth drivers. Known for providing granular market insights rather than general AI market statistics like the overall size of AI market which is irrelevant.",
        tools=[exa_search_tool],
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        updated = run_market_sizing_chain(profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Analyze the market size and expected growth rate for the startup's sector. Estimate TAM, SAM, SOM, and provide supporting data and sources.",
        agent=analyst,
        expected_output="A detailed market analysis report including TAM, SAM, SOM, growth rates, and sources.",
        callback=_callback,
    )
    return analyst, task
