"""
CrewAI wrapper that hands off the heavy work to the LangChain pitch-deck chain.
Only the callback's return value is surfaced to the caller.
"""

from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from chains.pitch_deck_chain import run_pitch_deck_chain

llm = ChatOpenAI(model="gpt-4", temperature=0.2)


def build_deck_agent(pdf_path: str, trace_id=None):
    analyst = Agent(
        role="Pitch-deck analyst",
        goal="Extract basic metadata and key insights from a startup pitch deck PDF.",
        backstory=(
            "Former VC analyst who has reviewed 1,000+ decks and knows what matters in first-pass screening. Expert in extracting actionable insights from pitch decks."
        ),
        verbose=True,
        llm=llm,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    # CrewAI passes a TaskOutput object to the callback; we ignore it.
    def _callback(*_) -> str:
        profile = run_pitch_deck_chain(pdf_path)
        return profile.model_dump_json(indent=2)

    task = Task(
        description="Read the PDF and populate the basic StartupProfile fields and key insights.",
        agent=analyst,
        expected_output="JSON-serialised StartupProfile with key insights.",
        async_execution=False,
        callback=_callback,
    )

    return analyst, task


def run_crew(pdf_path: str, trace_id=None) -> str:
    """Run the crew and return the JSON string our callback produced."""
    agent, task = build_deck_agent(pdf_path, trace_id)
    crew = Crew(agents=[agent], tasks=[task])
    return crew.kickoff().raw  # <-- this holds the clean JSON
