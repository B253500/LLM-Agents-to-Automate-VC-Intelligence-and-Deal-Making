"""
Product Description Agent - CrewAI wrapper for product/service analysis.
Handles LLM orchestration and calls the product description chain for deterministic processing.
"""

from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path

from core.schemas import StartupProfile
from chains.product_description_chain import run_product_description_chain

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)


def build_product_description_agent(profile: StartupProfile, trace_id=None):
    """Build the product description analysis agent."""
    analyst = Agent(
        role="Product Analyst",
        goal="Analyze and describe the startup's product or service offering in detail.",
        backstory=(
            "Senior product analyst with 12+ years experience in product strategy, "
            "user experience, and feature analysis. Expert in SaaS products, mobile apps, "
            "and enterprise software solutions."
        ),
        verbose=True,
        llm=llm,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_) -> str:
        """Callback function that calls the product description chain."""
        # Run product description analysis using the chain
        result = run_product_description_chain(profile)
        return result

    task = Task(
        description="Analyze the startup's product or service offering, features, and value proposition.",
        agent=analyst,
        expected_output="A comprehensive product/service description including features, benefits, and value proposition.",
        callback=_callback,
    )
    return analyst, task 