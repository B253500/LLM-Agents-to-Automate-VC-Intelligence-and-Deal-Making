"""
CrewAI wrapper that hands off the heavy work to the LangChain pitch-deck chain.
Only the callback's return value is surfaced to the caller.
"""

from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI

from chains.pitch_deck_chain import run_pitch_deck_chain

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)


def build_deck_agent(pdf_path: str):
    analyst = Agent(
        role="Pitch-deck analyst",
        goal="Extract basic metadata from a startup pitch deck PDF.",
        backstory=(
            "Former VC analyst who has reviewed 1 000+ decks and knows "
            "what matters in first-pass screening."
        ),
        verbose=True,
        llm=llm,
    )

    # CrewAI passes a TaskOutput object to the callback; we ignore it.
    def _callback(*_) -> str:
        profile = run_pitch_deck_chain(pdf_path)
        return profile.model_dump_json(indent=2)

    task = Task(
        description="Read the PDF and populate the basic StartupProfile fields.",
        agent=analyst,
        expected_output="JSON-serialised StartupProfile",
        async_execution=False,
        callback=_callback,
    )

    return analyst, task


def run_crew(pdf_path: str) -> str:
    """Run the crew and return the JSON string our callback produced."""
    agent, task = build_deck_agent(pdf_path)
    crew = Crew(agents=[agent], tasks=[task])
    return crew.kickoff().raw  # <-- this holds the clean JSON
