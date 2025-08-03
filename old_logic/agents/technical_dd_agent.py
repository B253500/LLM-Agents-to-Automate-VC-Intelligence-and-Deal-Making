from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from core.schemas import StartupProfile
from chains.technical_dd_chain import run_technical_dd_chain
from core.perplexity_utils import search_perplexity

llm = ChatOpenAI(model="gpt-4", temperature=0.2)


def get_recent_tech_news(company_name):
    if not company_name:
        return None
    query = f"Recent technical news, product launches, or technology updates for {company_name} (past 12 months)."
    return search_perplexity(query)


def build_technical_dd_agent(profile: StartupProfile, trace_id=None):
    ctto = Agent(
        role="Technical due-diligence lead",
        goal="Assess technical maturity, product moat, and technology risks of the startup.",
        backstory="25-year CTO who has evaluated 500+ VC deals. Expert in technical due diligence, product evaluation, and technology risk assessment.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        # 1. Run the core technical DD chain
        updated = run_technical_dd_chain(profile)
        # 2. Enrich: web search for recent technical news
        news = get_recent_tech_news(profile.name)
        updated.tech_news = news
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Analyze tech stack, rate maturity, summarize moat, assess technology risks, and enrich with recent technical news.",
        agent=ctto,
        expected_output="A detailed technical due diligence report including tech maturity, moat strength, risks, and recent technical news.",
        callback=_callback,
    )
    return ctto, task
