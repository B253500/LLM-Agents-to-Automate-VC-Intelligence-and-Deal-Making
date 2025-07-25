from crewai import Agent, Task
from langchain_openai import ChatOpenAI

from core.schemas import StartupProfile
from chains.founder_profiling_chain import run_founder_profiling_chain

llm = ChatOpenAI(model="gpt-4", temperature=0.2)


def build_founder_profiling_agent(profile: StartupProfile, trace_id=None):
    partner = Agent(
        role="Founder-profiling partner",
        goal="Evaluate founders' track-record, fit, and entrepreneurial experience.",
        backstory="20-year VC who focuses on team quality, founder-market fit, and leadership potential. Expert in assessing founder backgrounds and prior exits.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        updated = run_founder_profiling_chain(profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Score founder fit, count prior exits, and provide a summary of founder experience and leadership.",
        agent=partner,
        expected_output="A detailed founder profile including fit score, prior exits, and relevant experience.",
        callback=_callback,
    )
    return partner, task
