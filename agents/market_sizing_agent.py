from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from crewai_tools import EXASearchTool
from core.schemas import StartupProfile
from dotenv import load_dotenv
import os
import json
import re
from hashlib import sha1
from core.hybrid_context import get_hybrid_context
from core.perplexity_utils import search_perplexity
from typing import Optional
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

SYSTEM = """
You are a market research analyst for venture capital.
For the given company and sector, provide a detailed, structured market analysis including:
- Challenges: A bulleted list of the main pain points and obstacles in the market.
- Drivers: A bulleted list of growth drivers and positive trends.
- Size: A narrative paragraph with the latest available numbers (TAM, SAM, SOM if possible), growth rates (CAGR), and sources. If specific data is unavailable, explain why and provide the closest relevant market size.
Leave the current Discussion logic in place.
Return your answer as a multi-section, multi-bullet, multi-paragraph analysis suitable for a VC investment memo.
"""

from langchain.prompts import ChatPromptTemplate
PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Company & sector info:\n{context}\nWeb search context:\n{web_context}\n")
])

def extract_technical_data_from_text(text):
    """Extract technical specifications and performance data from deck text."""
    if not text:
        return {}
    
    import re
    
    tech_data = {}
    
    # Extract performance metrics
    performance_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(wh|watt|mhz|ghz|gb|mb|tb|fps|ms)', text.lower())
    if performance_matches:
        tech_data['performance_metrics'] = performance_matches[:3]  # Top 3 metrics
    
    # Extract efficiency metrics
    efficiency_matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', text.lower())
    if efficiency_matches:
        tech_data['efficiency_metrics'] = efficiency_matches[:3]  # Top 3 percentages
    
    # Extract time-based metrics
    time_matches = re.findall(r'(\d+)\s*(min|minutes|sec|seconds|ms)', text.lower())
    if time_matches:
        tech_data['time_metrics'] = time_matches[:3]  # Top 3 time metrics
    
    # Extract capacity/volume metrics
    capacity_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(gb|mb|tb|wh|ah|l)', text.lower())
    if capacity_matches:
        tech_data['capacity_metrics'] = capacity_matches[:3]  # Top 3 capacity metrics
    
    # Extract year references (prioritize recent years)
    year_matches = re.findall(r'(\d{4})', text)
    if year_matches:
        # Filter for reasonable years (2000-2030)
        valid_years = [int(y) for y in year_matches if 2000 <= int(y) <= 2030]
        if valid_years:
            tech_data['target_year'] = str(max(valid_years))  # Use the most recent year
        else:
            tech_data['target_year'] = '2023'  # Default to 2023 if no valid years found
    
    return tech_data

def build_market_sizing_agent(profile: StartupProfile, trace_id=None, evaluator: Optional[object] = None):
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
        # Call the market sizing chain - let the chain handle all extraction
        from chains.market_sizing_chain import run_market_sizing_chain
        
        print("[Market Sizing] Running comprehensive market sizing chain...")
        updated_profile = run_market_sizing_chain(profile, evaluator=evaluator)
        return updated_profile.model_dump_json(indent=2)

    task = Task(
        description="Analyze the market size and expected growth rate for the startup's sector. Estimate TAM, SAM, SOM, and provide supporting data and sources.",
        agent=analyst,
        expected_output="A detailed market analysis report including TAM, SAM, SOM, growth rates, and sources.",
        callback=_callback,
    )
    return analyst, task
