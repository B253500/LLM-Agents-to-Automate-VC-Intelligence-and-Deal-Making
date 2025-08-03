"""
Business Model Agent - CrewAI wrapper for business model analysis.
Handles LLM orchestration and calls the business model chain for deterministic processing.
"""

from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path

from core.schemas import StartupProfile
from chains.memo_synthesis_chain import run_business_model_chain

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)


def build_business_model_agent(profile: StartupProfile, trace_id=None):
    """Build the business model analysis agent."""
    analyst = Agent(
        role="Business Model Analyst",
        goal="Analyze and describe the startup's business model, revenue streams, and monetization strategy.",
        backstory=(
            "Expert business analyst with 15+ years experience in startup business models, "
            "revenue optimization, and go-to-market strategies. Specializes in SaaS, marketplace, "
            "and platform business models."
        ),
        verbose=True,
        llm=llm,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_) -> str:
        """Callback function that calls the business model chain."""
        # Run business model analysis using the chain
        result = run_business_model_chain(profile)
        return result

    task = Task(
        description="Analyze the startup's business model, revenue streams, pricing strategy, and monetization approach.",
        agent=analyst,
        expected_output="A comprehensive business model analysis including revenue streams, pricing, and monetization strategy.",
        callback=_callback,
    )
    return analyst, task 