"""
Follow-up Agent - CrewAI wrapper for follow-up analysis.
Handles LLM orchestration and calls the follow-up chain for deterministic processing.
"""

from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path

from core.schemas import StartupProfile
from chains.memo_synthesis_chain import run_followup_section_chain

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)


def build_follow_up_agent(profile: StartupProfile, trace_id=None):
    """Build the follow-up analysis agent."""
    analyst = Agent(
        role="Follow-up Analyst",
        goal="Generate follow-up questions and due diligence requirements for the startup.",
        backstory=(
            "Due diligence specialist with 15+ years experience in investment research, "
            "risk assessment, and deal structuring. Expert in identifying key questions "
            "and requirements for investment decisions."
        ),
        verbose=True,
        llm=llm,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_) -> str:
        """Callback function that calls the follow-up chain."""
        # Run follow-up analysis using the chain
        result = run_followup_section_chain(profile)
        return result

    task = Task(
        description="Generate follow-up questions and due diligence requirements for the startup investment decision.",
        agent=analyst,
        expected_output="A comprehensive list of follow-up questions and due diligence requirements.",
        callback=_callback,
    )
    return analyst, task 