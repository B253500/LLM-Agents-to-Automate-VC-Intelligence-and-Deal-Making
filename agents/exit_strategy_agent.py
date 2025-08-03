"""
Exit Strategy Agent - CrewAI wrapper for exit strategy analysis.
Handles LLM orchestration and calls the exit strategy chain for deterministic processing.
"""

from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path

from core.schemas import StartupProfile
from chains.memo_synthesis_chain import run_exit_strategies_chain

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)


def build_exit_strategy_agent(profile: StartupProfile, trace_id=None):
    """Build the exit strategy analysis agent."""
    analyst = Agent(
        role="Exit Strategy Analyst",
        goal="Analyze potential exit strategies and acquisition scenarios for the startup.",
        backstory=(
            "M&A specialist with 18+ years experience in startup exits, acquisitions, "
            "and strategic partnerships. Expert in IPO preparation, strategic acquisitions, "
            "and private equity exits."
        ),
        verbose=True,
        llm=llm,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_) -> str:
        """Callback function that calls the exit strategy chain."""
        # Run exit strategy analysis using the chain
        result = run_exit_strategies_chain(profile)
        return result

    task = Task(
        description="Analyze potential exit strategies, acquisition scenarios, and IPO potential for the startup.",
        agent=analyst,
        expected_output="A comprehensive exit strategy analysis including potential acquirers, IPO scenarios, and strategic partnerships.",
        callback=_callback,
    )
    return analyst, task 