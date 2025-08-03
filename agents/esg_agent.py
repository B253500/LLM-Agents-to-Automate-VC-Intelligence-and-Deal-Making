"""
ESG Agent - CrewAI wrapper for ESG (Environmental, Social, Governance) analysis.
Handles LLM orchestration and calls the ESG chain for deterministic processing.
"""

from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path

from core.schemas import StartupProfile
from chains.memo_synthesis_chain import run_esg_section_chain

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)


def build_esg_agent(profile: StartupProfile, trace_id=None):
    """Build the ESG analysis agent."""
    analyst = Agent(
        role="ESG Analyst",
        goal="Analyze the startup's environmental, social, and governance practices and impact.",
        backstory=(
            "ESG specialist with 10+ years experience in sustainable investing, "
            "impact measurement, and corporate responsibility. Expert in climate tech, "
            "social impact startups, and governance best practices."
        ),
        verbose=True,
        llm=llm,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_) -> str:
        """Callback function that calls the ESG chain."""
        # Run ESG analysis using the chain
        result = run_esg_section_chain(profile)
        return result

    task = Task(
        description="Analyze the startup's environmental impact, social responsibility, and governance practices.",
        agent=analyst,
        expected_output="A comprehensive ESG analysis including environmental impact, social responsibility, and governance practices.",
        callback=_callback,
    )
    return analyst, task 