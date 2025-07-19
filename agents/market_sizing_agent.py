from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from crewai_tools import EXASearchTool
from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context
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

    def _callback(context, *args, **kwargs):
        # In hierarchical mode, ignore incoming context and start fresh
        profile = StartupProfile()
        if deck_payload:
            print(f"[market_sizing_agent] Deck text (first 200 chars): {deck_payload.get('text', '')[:200]}")
        else:
            print(f"[market_sizing_agent] No deck_payload provided.")
        # Build context and prompt
        from core.hybrid_context import safe_truncate
        ctx = get_hybrid_context(profile, "market OR TAM OR SAM OR SOM OR opportunity", 3, 3)
        ctx = safe_truncate(ctx, max_chars=2000)
        deck_text = safe_truncate(deck_payload.get('text', '') if deck_payload else '', max_chars=2000)
        prompt_context = f"{ctx}\n\nFull Deck Text:\n{deck_text}"
        print(f"[market_sizing_agent] LLM prompt context (first 300 chars): {prompt_context[:300]}")
        raw = llm.invoke(PROMPT.format(context=prompt_context)).content.strip()
        print(f"[market_sizing_agent] LLM raw output (first 300 chars): {raw[:300]}")
        # 1. Use EXA search tool for additional market context
        exa_context = None
        if profile.name or profile.sector:
            query = f"Latest market size, growth rate, and trends for {profile.name or 'the company'} in the {profile.sector or ''} sector. Provide TAM, SAM, SOM if available, and cite sources."
            exa_context = exa_search_tool.run(query)
        # 2. Run the core market sizing logic (LLM-based extraction)
        first, last = raw.find("{"), raw.rfind("}")
        if first != -1 and last != -1:
            try:
                data = json.loads(raw[first : last + 1])
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
        if not profile.startup_id:
            profile.startup_id = sha1((profile.name or ctx[:40]).encode()).hexdigest()[:10]
        # 3. Attach EXA context to profile
        profile.exa_market_context = exa_context
        print(f"[market_sizing_agent] Output profile: {profile.model_dump()}")
        output = profile.model_dump()
        print(f"[market_sizing_agent] Output type: {type(output)}")
        print(f"[market_sizing_agent] Output keys: {list(output.keys()) if isinstance(output, dict) else 'N/A'}")
        return output

    task = Task(
        description="Analyze the market size and expected growth rate for the startup's sector. Estimate TAM, SAM, SOM, and provide supporting data and sources, including EXA search enrichment.",
        agent=analyst,
        expected_output="A detailed market analysis report including TAM, SAM, SOM, growth rates, sources, and EXA context.",
        callback=_callback,
    )
    return analyst, task

def build_market_chain_agent(profile):
    def chain_callback(*_):
        from chains.market_sizing_chain import run_market_sizing_chain
        updated_profile = run_market_sizing_chain(profile)
        return updated_profile.model_dump()
    agent = Agent(
        role="Market Sizing Extractor",
        goal="Extract market sizing and growth data from the deck.",
        backstory="A specialized agent for extracting market sizing and growth data from pitch decks.",
        verbose=True
    )
    task = Task(
        description="Extract market sizing and growth data from the deck.",
        agent=agent,
        callback=chain_callback,
        args=[profile.model_dump()],
        expected_output="Profile with market sizing fields extracted."
    )
    return agent, task
