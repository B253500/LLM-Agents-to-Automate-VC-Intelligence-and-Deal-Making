from crewai import Agent, Task
from langchain_openai import ChatOpenAI

from core.schemas import StartupProfile
from chains.risk_assessment_chain import run_risk_assessment_chain

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)


def build_risk_assessment_agent(profile: StartupProfile):
    officer = Agent(
        role="Risk-assessment officer",
        goal="Identify red-flags and compute risk score.",
        backstory="Former credit-risk VP now in VC.",
        verbose=True,
        llm=llm,
    )

    def _callback(*_):
        updated = run_risk_assessment_chain(profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Flag risks and score overall risk.",
        agent=officer,
        expected_output="JSON with risk_flags & risk_score",
        callback=_callback,
    )
    return officer, task
