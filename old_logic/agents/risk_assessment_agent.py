from crewai import Agent, Task
from langchain_openai import ChatOpenAI

from core.schemas import StartupProfile
from chains.risk_assessment_chain import run_risk_assessment_chain
from core.perplexity_utils import search_perplexity

llm = ChatOpenAI(model="gpt-4", temperature=0.2)


def get_recent_risk_news(company_name):
    if not company_name:
        return None
    query = f"Recent risk-related news, controversies, or red flags for {company_name} (past 12 months)."
    return search_perplexity(query)


def build_risk_assessment_agent(profile: StartupProfile, trace_id=None):
    officer = Agent(
        role="Risk-assessment officer",
        goal="Identify red-flags, compute risk score, and assess overall risk profile of the startup.",
        backstory="Former credit-risk VP now in VC. Expert in risk modeling, red-flag detection, and startup risk assessment.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        # 1. Run the core risk assessment chain
        updated = run_risk_assessment_chain(profile)
        # 2. Enrich: web search for recent risk-related news
        news = get_recent_risk_news(profile.name)
        updated.risk_news = news
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Flag risks, score overall risk, provide a risk assessment summary, and enrich with recent risk-related news.",
        agent=officer,
        expected_output="A detailed risk assessment report including risk flags, risk score, mitigation suggestions, and recent risk-related news.",
        callback=_callback,
    )
    return officer, task
