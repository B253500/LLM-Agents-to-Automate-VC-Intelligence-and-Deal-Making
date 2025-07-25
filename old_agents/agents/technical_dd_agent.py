from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from core.schemas import StartupProfile
from chains.technical_dd_chain import run_technical_dd_chain

llm = ChatOpenAI(model="gpt-4", temperature=0.2)


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
        updated = run_technical_dd_chain(profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Analyze tech stack, rate maturity, summarize moat, and assess technology risks.",
        agent=ctto,
        expected_output="A detailed technical due diligence report including tech maturity, moat strength, and risks.",
        callback=_callback,
    )
    return ctto, task
