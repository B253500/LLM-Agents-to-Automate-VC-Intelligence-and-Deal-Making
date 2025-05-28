from crewai import Agent, Task
from langchain_openai import ChatOpenAI

from core.schemas import StartupProfile
from chains.competitive_intel_chain import run_competitive_intel_chain

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)


def build_competitive_intel_agent(profile: StartupProfile):
    scout = Agent(
        role="Competitive-intelligence scout",
        goal="List key competitors, highlight differentiation.",
        backstory="Ex-Gartner analyst specialising in market landscapes.",
        verbose=True,
        llm=llm,
    )

    def _callback(*_):
        updated = run_competitive_intel_chain(profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Produce top_competitors array.",
        agent=scout,
        expected_output="JSON with competitor list & differentiator",
        callback=_callback,
    )
    return scout, task
