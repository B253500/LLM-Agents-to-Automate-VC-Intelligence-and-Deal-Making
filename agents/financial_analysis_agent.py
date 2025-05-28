from crewai import Agent, Task
from langchain_openai import ChatOpenAI

from core.schemas import StartupProfile
from chains.financial_analysis_chain import run_financial_analysis_chain

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)


def build_financial_analysis_agent(profile: StartupProfile):
    fa = Agent(
        role="Financial analyst",
        goal="Estimate burn, runway, and implied valuation.",
        backstory="Ex-investment-banker who crunches numbers for VC deals.",
        verbose=True,
        llm=llm,
    )

    def _callback(*_):
        updated = run_financial_analysis_chain(profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Compute cash_burn_12m, runway_months, implied_valuation.",
        agent=fa,
        expected_output="JSON with the three financial fields",
        callback=_callback,
    )
    return fa, task
