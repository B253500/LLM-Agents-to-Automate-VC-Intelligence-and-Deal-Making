from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from crewai_tools import EXASearchTool
from core.schemas import StartupProfile
from dotenv import load_dotenv
import os
import json
from hashlib import sha1
from core.hybrid_context import get_hybrid_context
from core.perplexity_utils import search_perplexity
from pathlib import Path

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

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)

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

def web_search_market_context(company_name, sector):
    if not company_name and not sector:
        return ""
    query = f"Latest market size, growth rate, and trends for {company_name or 'the company'} in the {sector or ''} sector. Provide TAM, SAM, SOM if available, and cite sources."
    result = search_perplexity(query)
    return result or ""

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
        # --- Hybrid context and web search ---
        context = get_hybrid_context(
            profile, "market size OR TAM OR SAM OR SOM OR industry", 3, 3
        )
        web_context = web_search_market_context(profile.name, profile.sector)
        prompt_vars = {"context": context, "web_context": web_context}
        txt = llm.invoke(PROMPT.format(**prompt_vars)).content.strip()
        first, last = txt.find("{"), txt.rfind("}")
        if first == -1 or last == -1:
            return profile.model_dump_json(indent=2)
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
        return profile.model_dump_json(indent=2)

    task = Task(
        description="Analyze the market size and expected growth rate for the startup's sector. Estimate TAM, SAM, SOM, and provide supporting data and sources.",
        agent=analyst,
        expected_output="A detailed market analysis report including TAM, SAM, SOM, growth rates, and sources.",
        callback=_callback,
    )
    return analyst, task
