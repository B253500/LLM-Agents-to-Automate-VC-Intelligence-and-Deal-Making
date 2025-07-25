from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path

from core.schemas import StartupProfile
from chains.financial_analysis_chain import run_financial_analysis_chain

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4", temperature=0.2)


def build_financial_analysis_agent(profile: StartupProfile, full_text: str = "", tables_text: str = "", figures_ocr: str = "", trace_id=None):
    fa = Agent(
        role="Financial analyst",
        goal="Estimate burn, runway, implied valuation, and analyze financial health of the startup.",
        backstory="Ex-investment-banker who crunches numbers for VC deals. Expert in financial modeling, cash flow analysis, and startup valuation.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        # Aggregate all relevant financial information inside the agent
        def extract_financial_paragraphs(text):
            keywords = ["revenue", "funding", "ebitda", "burn", "runway", "profit", "loss", "investment", "round", "valuation", "gross", "opex", "net", "cash", "amortization", "depreciation"]
            paras = text.split('\n')
            return '\n'.join([p for p in paras if any(k in p.lower() for k in keywords)])
        financial_context = ""
        if tables_text:
            financial_context += "\n\n" + tables_text
        if figures_ocr:
            financial_context += "\n\n" + figures_ocr
        if full_text:
            financial_context += "\n\n" + extract_financial_paragraphs(full_text)
        # Call the chain with the aggregated context
        updated = run_financial_analysis_chain(profile, financial_context=financial_context)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Compute cash burn, runway, implied valuation, and provide a financial health summary.",
        agent=fa,
        expected_output="A detailed financial analysis report including cash burn, runway, valuation, and key financial metrics.",
        callback=_callback,
    )
    return fa, task
