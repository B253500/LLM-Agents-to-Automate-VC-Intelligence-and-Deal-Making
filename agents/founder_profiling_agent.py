from crewai import Agent, Task
from langchain_openai import ChatOpenAI

from core.schemas import StartupProfile
from chains.founder_profiling_chain import run_founder_profiling_chain

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)


def build_founder_profiling_agent(profile: StartupProfile):
    partner = Agent(
        role="Founder-profiling partner",
        goal="Evaluate founders’ track-record and fit.",
        backstory="20-year VC who focuses on team quality.",
        verbose=True,
        llm=llm,
    )

    def _callback(*_):
        updated = run_founder_profiling_chain(profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Score founder fit and count prior exits.",
        agent=partner,
        expected_output="JSON with founder_fit_score & prior_exits",
        callback=_callback,
    )
    return partner, task
