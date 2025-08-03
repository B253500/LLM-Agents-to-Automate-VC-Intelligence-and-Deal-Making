from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path

from core.schemas import StartupProfile
from chains.financial_analysis_chain import run_financial_analysis_chain

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)


def build_financial_analysis_agent(profile: StartupProfile, full_text: str = "", tables_text: str = "", figures_ocr: str = "", trace_id=None):
    fa = Agent(
        role="Financial analyst",
        goal="Extract comprehensive financial metrics including revenue, profitability, growth, business model, and operational data using both regex patterns and AI-powered detection.",
        backstory="Ex-investment-banker who crunches numbers for VC deals. Expert in financial modeling, cash flow analysis, startup valuation, and comprehensive financial data extraction.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        # Use comprehensive extracted data context with financial focus
        from core.hybrid_context import get_hybrid_context
        
        # Get comprehensive context including all extracted data with financial focus
        comprehensive_context = get_hybrid_context(profile, "financial analysis OR revenue OR funding OR valuation OR burn rate OR runway OR cash flow OR financial metrics OR profitability OR growth OR business model", use_reports=False)
        
        # Also include any additional financial-specific data
        financial_context = comprehensive_context
        if tables_text:
            financial_context += "\n\nTABLES DATA:\n" + tables_text
        if figures_ocr:
            financial_context += "\n\nFIGURES/OCR DATA:\n" + figures_ocr
        if full_text:
            # Add full text as backup
            financial_context += "\n\nFULL TEXT:\n" + full_text[:3000]
        
        # Call the chain with the comprehensive context - let the chain handle all extraction
        print("[Financial Analysis] Running comprehensive financial analysis chain...")
        updated = run_financial_analysis_chain(profile, financial_context=financial_context)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Extract comprehensive financial metrics including revenue, profitability, growth rates, business model details, operational metrics, and efficiency ratios using both regex patterns and AI-powered detection.",
        agent=fa,
        expected_output="A detailed financial analysis report including comprehensive financial metrics, business model analysis, and operational data.",
        callback=_callback,
    )
    return fa, task
