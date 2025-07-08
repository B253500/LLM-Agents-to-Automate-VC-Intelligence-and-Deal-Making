from crewai import Agent, Task
from langchain_openai import ChatOpenAI

from core.schemas import StartupProfile
from chains.risk_assessment_chain import run_risk_assessment_chain

llm = ChatOpenAI(model="gpt-4", temperature=0.2)


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
        updated = run_risk_assessment_chain(profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Flag risks, score overall risk, and provide a risk assessment summary for the startup.",
        agent=officer,
        expected_output="A detailed risk assessment report including risk flags, risk score, and mitigation suggestions.",
        callback=_callback,
    )
    return officer, task
