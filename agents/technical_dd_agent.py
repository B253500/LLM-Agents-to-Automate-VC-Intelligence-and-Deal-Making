from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path
from core.schemas import StartupProfile
from chains.technical_dd_chain import run_technical_dd_chain, run_technical_dd_chain_with_text
from typing import Optional

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)


def build_technical_dd_agent(profile: StartupProfile, trace_id=None, evaluator: Optional[object] = None):
    ctto = Agent(
        role="Technical due-diligence lead",
        goal="Assess technical maturity, product moat, and technology risks of the startup.",
        backstory="25-year CTO who has evaluated 500+ VC deals. Expert in technical due diligence, product evaluation, and technology risk assessment.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        # Use comprehensive extracted data context to capture all valuable technical information
        from core.hybrid_context import get_hybrid_context
        
        # Get comprehensive technical context
        full_text = ""
        if hasattr(profile, 'extracted_data_context') and profile.extracted_data_context:
            # Use comprehensive search within extracted data
            full_text = get_hybrid_context(profile, "technical analysis OR energy density OR cycle life OR battery technology OR technical specifications OR patents OR product roadmap OR manufacturing OR testing", use_reports=False)
        else:
            # Fallback to comprehensive hybrid context
            full_text = get_hybrid_context(profile, "technical analysis OR energy density OR cycle life OR battery technology OR technical specifications OR patents OR product roadmap OR manufacturing OR testing", use_reports=False)
        
        # Use the comprehensive context for technical analysis
        updated = run_technical_dd_chain_with_text(full_text, profile, evaluator=evaluator)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Analyze tech stack, rate maturity, summarize moat, and assess technology risks.",
        agent=ctto,
        expected_output="A detailed technical due diligence report including tech maturity, moat strength, and risks.",
        callback=_callback,
    )
    return ctto, task
