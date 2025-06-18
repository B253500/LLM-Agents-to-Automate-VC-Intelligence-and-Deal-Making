from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from core.schemas import StartupProfile
from chains.technical_dd_chain import run_technical_dd_chain

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)


def build_technical_dd_agent(profile: StartupProfile):
    ctto = Agent(
        role="Technical due-diligence lead",
        goal="Assess technical maturity and moat of the startup product.",
        backstory="25-year CTO who has evaluated 500+ VC deals.",
        llm=llm,
        verbose=True,
    )

    def _callback(*_):
        updated = run_technical_dd_chain(profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Analyse tech stack, rate maturity, summarise moat.",
        agent=ctto,
        expected_output="JSON with tech_maturity & moat_strength",
        callback=_callback,
    )
    return ctto, task
