from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from chains.pitch_deck_chain import run_pitch_deck_chain

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)


def build_deck_agent():
    analyser = Agent(
        role="Pitch-deck analyst",
        goal="Extract basic metadata from a startup pitch deck PDF.",
        backstory=(
            "Former VC analyst who has reviewed 1 000+ start-up decks and knows what "
            "investors need in the first pass."
        ),
        verbose=True,
        llm=llm,
    )

    task = Task(
        description="Read the PDF, populate StartupProfile fields (name, sector, etc.)",
        agent=analyser,
        expected_output="JSON serialised StartupProfile",
        async_execution=False,
        callback=run_pitch_deck_chain,  # here's the hybrid bit
    )
    return analyser, task


def run_crew(pdf_path: str):
    agent, task = build_deck_agent()
    crew = Crew(agents=[agent], tasks=[task])
    return crew.kickoff({"pdf_path": pdf_path})
