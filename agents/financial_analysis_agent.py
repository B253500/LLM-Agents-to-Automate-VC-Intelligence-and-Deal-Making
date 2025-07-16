from crewai import Agent, Task
from langchain_openai import ChatOpenAI

from core.schemas import StartupProfile
from chains.financial_analysis_chain import run_financial_analysis_chain
from core.perplexity_utils import search_perplexity

llm = ChatOpenAI(model="gpt-4", temperature=0.2)


def get_recent_financial_news(company_name):
    if not company_name:
        return None
    query = f"Recent financial news, funding rounds, or valuation updates for {company_name} (past 12 months)."
    return search_perplexity(query)


def build_financial_analysis_agent(profile: StartupProfile, trace_id=None):
    fa = Agent(
        role="Financial analyst",
        goal="Estimate burn, runway, implied valuation, and analyze financial health of the startup.",
        backstory="Ex-investment-banker who crunches numbers for VC deals. Expert in financial modeling, cash flow analysis, and startup valuation.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        # 1. Run the core financial analysis chain
        updated = run_financial_analysis_chain(profile)
        # 2. Enrich: web search for recent financial news
        news = get_recent_financial_news(profile.name)
        updated.financial_news = news
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Compute cash burn, runway, implied valuation, provide a financial health summary, and enrich with recent financial news.",
        agent=fa,
        expected_output="A detailed financial analysis report including cash burn, runway, valuation, key financial metrics, and recent financial news.",
        callback=_callback,
    )
    return fa, task
