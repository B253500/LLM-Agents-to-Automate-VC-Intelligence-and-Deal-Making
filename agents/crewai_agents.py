# CrewAI agent and tool definitions, ported from memo_generator/agents.py
import os
from pathlib import Path
from dotenv import load_dotenv
from crewai import Agent
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from crewai_tools import EXASearchTool
import requests
from chains.technical_dd_chain import run_technical_dd_chain
from agents.founder_profiling_agent import run_founder_profiling_chain
from chains.market_sizing_chain import run_market_sizing_chain
from chains.financial_analysis_chain import run_financial_analysis_chain
from chains.competitive_intel_chain import run_competitive_intel_chain
from chains.risk_assessment_chain import run_risk_assessment_chain
from core.schemas import StartupProfile
import json

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Update environment variable lookups to use old names
# Portkey, fallback to direct OpenAI if not available
try:
    from portkey_ai import createHeaders, PORTKEY_GATEWAY_URL
    PORTKEY_AVAILABLE = True
except ImportError:
    PORTKEY_AVAILABLE = False
    print("Portkey not available, falling back to direct OpenAI usage")

def vc_get_portkey_llm(trace_id=None, span_id=None, agent_name=None):
    if PORTKEY_AVAILABLE:
        headers = createHeaders(
            provider="openai",
            api_key=os.getenv("Portkey_KEY"),
            trace_id=trace_id,
        )
        if span_id:
            headers['x-portkey-span-id'] = span_id
        if agent_name:
            headers['x-portkey-span-name'] = f'Agent: {agent_name}'

        return ChatOpenAI(
            model="gpt-4o",
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=headers,
            api_key=os.getenv("OpenAI_KEY")
        )
    else:
        # Fallback to direct OpenAI usage
        return ChatOpenAI(
            model="gpt-4",
            api_key=os.getenv("OPENAI_API_KEY")
        )

# EXA Search tool
class CustomEXASearchTool(EXASearchTool):
    def __init__(self):
        super().__init__(
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

exa_search_tool = CustomEXASearchTool()

# Market Size tool
def vc_estimate_market_size(data: str) -> str:
    return f"Estimated market size based on: {data}"

market_size_tool = Tool(
    name="Market Size Estimator",
    func=vc_estimate_market_size,
    description="Estimates market size based on provided data."
)

# CAGR calculator tool

def vc_calculate_cagr(args: dict) -> float:
    initial_value = args.get('initial_value')
    final_value = args.get('final_value')
    num_years = args.get('num_years')
    if not (initial_value and final_value and num_years):
        return "Missing required arguments."
    try:
        cagr = (float(final_value) / float(initial_value)) ** (1 / float(num_years)) - 1
        return cagr
    except Exception as e:
        return f"Error calculating CAGR: {e}"

cagr_tool = Tool(
    name="CAGR Calculator",
    func=vc_calculate_cagr,
    description="Calculates CAGR given a dictionary with keys 'initial_value', 'final_value', and 'num_years'."
)

# --- Website finder tool with disambiguation ---
def find_company_website(company_name, founder_name=None, sector=None):
    # Compose a reasoning prompt for the LLM
    prompt = (
        f"You are a research analyst. Find the official website for the company '{company_name}'."
        f"{' The founder is ' + founder_name + '.' if founder_name else ''}"
        f"{' The sector is ' + sector + '.' if sector else ''}"
        " Use Google or web search if needed. Return only the official website URL. If ambiguous, explain your reasoning."
    )
    llm = ChatOpenAI(model='gpt-4', api_key=os.getenv('OPENAI_API_KEY'))
    result = llm.invoke(prompt).content.strip()
    return result

website_finder_tool = Tool(
    name="Company Website Finder",
    func=find_company_website,
    description="Finds the official website for a given company name, using founder and sector for disambiguation."
)

# --- LLM-based classic analysis tools ---
def technical_dd_tool(profile_json: str) -> str:
    profile = StartupProfile(**json.loads(profile_json))
    updated = run_technical_dd_chain(profile)
    return f"Technical Due Diligence: maturity={updated.tech_maturity}, moat={updated.moat_strength}"

technical_dd_crewai_tool = Tool(
    name="Technical Due Diligence",
    func=technical_dd_tool,
    description="Performs technical due diligence using the classic extraction chain. Input: StartupProfile as JSON string."
)

def founder_profiling_tool(profile_json: str) -> str:
    profile = StartupProfile(**json.loads(profile_json))
    updated = run_founder_profiling_chain(profile)
    return f"Founder Profiling: fit_score={updated.founder_fit_score}, prior_exits={updated.prior_exits}"

founder_profiling_crewai_tool = Tool(
    name="Founder Profiling",
    func=founder_profiling_tool,
    description="Performs founder profiling using the classic extraction chain. Input: StartupProfile as JSON string."
)

def market_sizing_tool(profile_json: str) -> str:
    profile = StartupProfile(**json.loads(profile_json))
    updated = run_market_sizing_chain(profile)
    return f"Market Sizing: TAM={updated.TAM}, SAM={updated.SAM}, SOM={updated.SOM}"

market_sizing_crewai_tool = Tool(
    name="Market Sizing",
    func=market_sizing_tool,
    description="Performs market sizing using the classic extraction chain. Input: StartupProfile as JSON string."
)

def financial_analysis_tool(profile_json: str) -> str:
    profile = StartupProfile(**json.loads(profile_json))
    updated = run_financial_analysis_chain(profile)
    return f"Financial Analysis: burn={updated.cash_burn_12m}, runway={updated.runway_months}, valuation={updated.implied_valuation}"

financial_analysis_crewai_tool = Tool(
    name="Financial Analysis",
    func=financial_analysis_tool,
    description="Performs financial analysis using the classic extraction chain. Input: StartupProfile as JSON string."
)

def competitive_intel_tool(profile_json: str) -> str:
    profile = StartupProfile(**json.loads(profile_json))
    updated = run_competitive_intel_chain(profile)
    competitors = ", ".join([c.name for c in updated.top_competitors])
    return f"Competitive Intelligence: competitors={competitors}"

competitive_intel_crewai_tool = Tool(
    name="Competitive Intelligence",
    func=competitive_intel_tool,
    description="Performs competitive intelligence using the classic extraction chain. Input: StartupProfile as JSON string."
)

def risk_assessment_tool(profile_json: str) -> str:
    profile = StartupProfile(**json.loads(profile_json))
    updated = run_risk_assessment_chain(profile)
    return f"Risk Assessment: score={updated.risk_score}, flags={updated.risk_flags}"

risk_assessment_crewai_tool = Tool(
    name="Risk Assessment",
    func=risk_assessment_tool,
    description="Performs risk assessment using the classic extraction chain. Input: StartupProfile as JSON string."
)

# --- Financial research tool with disambiguation ---
def financial_research_tool(company_name: str, founder_name: str = None, sector: str = None) -> str:
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return "[Financial Research] No Perplexity API key configured."
    query = f"What is the latest funding, valuation, and revenue for {company_name}"
    if founder_name:
        query += f" founded by {founder_name}"
    if sector:
        query += f" in {sector} sector"
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "sonar-reasoning-pro",
        "messages": [
            {"role": "system", "content": "You are a helpful research assistant. Answer with up-to-date, factual, and cited information."},
            {"role": "user", "content": query}
        ],
        "max_tokens": 512,
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                # Simple check: if founder or sector not in result, warn
                warn = False
                if founder_name and founder_name.lower() not in content.lower():
                    warn = True
                if sector and sector.lower() not in content.lower():
                    warn = True
                if warn:
                    content += "\nWarning: Financial data could not be confidently matched to the founder/sector; manual review recommended."
                return content
            else:
                return "[Financial Research] No results found."
        else:
            return f"[Financial Research] Perplexity API error: {response.status_code} {response.text}"
    except Exception as e:
        return f"[Financial Research] Exception: {e}"

financial_research_crewai_tool = Tool(
    name="Company Financial Research",
    func=financial_research_tool,
    description="Finds the latest funding, valuation, and revenue for a given company name using Perplexity AI, using founder and sector for disambiguation."
)

# Agents
def vc_create_agent(role, goal, backstory, tools, trace_id=None, agent_name=None):
    span_id = os.urandom(16).hex() if trace_id else None
    llm = vc_get_portkey_llm(trace_id, span_id, agent_name)

    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=3,
        max_execution_time=300
    )

def vc_get_market_analyst(trace_id=None):
    return vc_create_agent(
        role='Market size Research Analyst',
        goal='Research and analyze the market size TAM of AI subsegment markets focusing on specialized market sizes and growth rates',
        backstory='Expert in doing research and calculating the market size TAM of specific subsegments of the AI market, and growth rates. Also search for sector-specific growth drivers. Known for providing granular market insights rather than general AI market statistics like the overall size of AI market which is irrelevant.',
        tools=[exa_search_tool, market_size_tool, cagr_tool],
        trace_id=trace_id,
        agent_name='market_analyst'
    )

def vc_get_competitor_analyst(trace_id=None):
    return vc_create_agent(
        role='AI Startup Intelligence Specialist',
        goal='Identify and analyze relevant AI startups within specific AI subsegment markets',
        backstory="""Expert in mapping competitive landscapes for specific AI verticals. 
        Specialized in identifying real, named emerging startups and scale-ups rather than tech giants like IBM, OpenAI, Google, META, Anthropic, HuggingFace. Known for finding verifiable information about startups' funding, technology, and market focus.""",
        tools=[exa_search_tool],
        trace_id=trace_id,
        agent_name='competitor_analyst'
    )

def vc_get_strategy_advisor(trace_id=None):
    return vc_create_agent(
        role='Project Manager',
        goal='Efficiently manage the crew and ensure high-quality task completion with a focus on ensuring that the results are very specific and relevant and not generic and too zoom out',
        backstory="""You're an experienced project manager, skilled in overseeing complex projects and guiding teams to success. Your role is to coordinate the efforts of the crew members, ensuring that each task is completed on time and that the results are relevant and specific to the market.""",
        tools=[],
        trace_id=trace_id,
        agent_name='strategy_advisor'
    )

def get_website_finder_agent(trace_id=None):
    return vc_create_agent(
        role='Company Website Finder',
        goal='Find the official website for the company, using founder and sector for disambiguation.',
        backstory='Expert in web research and company validation.',
        tools=[website_finder_tool],
        trace_id=trace_id,
        agent_name='website_finder_agent'
    )

# --- CrewAI agent creators for classic tasks ---
def get_technical_dd_agent(trace_id=None):
    return vc_create_agent(
        role='Technical Due Diligence Lead',
        goal='Assess technical maturity, product moat, and technology risks of the startup.',
        backstory='25-year CTO who has evaluated 500+ VC deals. Expert in technical due diligence, product evaluation, and technology risk assessment.',
        tools=[technical_dd_crewai_tool],
        trace_id=trace_id,
        agent_name='technical_dd_agent'
    )

def get_founder_profiling_agent(trace_id=None):
    return vc_create_agent(
        role='Founder-profiling Partner',
        goal="Evaluate founders' track-record, fit, and entrepreneurial experience.",
        backstory='20-year VC who focuses on team quality, founder-market fit, and leadership potential. Expert in assessing founder backgrounds and prior exits.',
        tools=[founder_profiling_crewai_tool],
        trace_id=trace_id,
        agent_name='founder_profiling_agent'
    )

def get_market_sizing_agent(trace_id=None):
    return vc_create_agent(
        role='Market Sizing Analyst',
        goal='Analyze the market size and expected growth rate for the startup sector.',
        backstory='Expert in market research and sizing for startups.',
        tools=[market_sizing_crewai_tool],
        trace_id=trace_id,
        agent_name='market_sizing_agent'
    )

def get_financial_analysis_agent(trace_id=None):
    return vc_create_agent(
        role='Financial Analyst',
        goal='Estimate burn, runway, implied valuation, and analyze financial health of the startup.',
        backstory='Ex-investment-banker who crunches numbers for VC deals. Expert in financial modeling, cash flow analysis, and startup valuation.',
        tools=[financial_analysis_crewai_tool],
        trace_id=trace_id,
        agent_name='financial_analysis_agent'
    )

def get_competitive_intel_agent(trace_id=None):
    return vc_create_agent(
        role='Competitive Intelligence Specialist',
        goal='Identify and analyze relevant competitors for the startup.',
        backstory='Expert in mapping competitive landscapes for startups.',
        tools=[competitive_intel_crewai_tool],
        trace_id=trace_id,
        agent_name='competitive_intel_agent'
    )

def get_risk_assessment_agent(trace_id=None):
    return vc_create_agent(
        role='Risk Assessment Officer',
        goal='Identify red-flags, compute risk score, and assess overall risk profile of the startup.',
        backstory='Former credit-risk VP now in VC. Expert in risk modeling, red-flag detection, and startup risk assessment.',
        tools=[risk_assessment_crewai_tool],
        trace_id=trace_id,
        agent_name='risk_assessment_agent'
    )

def get_financial_research_agent(trace_id=None):
    return vc_create_agent(
        role='Company Financial Researcher',
        goal='Find the latest available financial data for the company from the internet, using founder and sector for disambiguation.',
        backstory='Expert in web research and financial data extraction.',
        tools=[financial_research_crewai_tool],
        trace_id=trace_id,
        agent_name='financial_research_agent'
    )

__all__ = [
    'vc_get_market_analyst', 'vc_get_competitor_analyst', 'vc_get_strategy_advisor', 'get_website_finder_agent',
    'get_technical_dd_agent', 'get_founder_profiling_agent', 'get_market_sizing_agent',
    'get_financial_analysis_agent', 'get_competitive_intel_agent', 'get_risk_assessment_agent',
    'get_financial_research_agent'
] 