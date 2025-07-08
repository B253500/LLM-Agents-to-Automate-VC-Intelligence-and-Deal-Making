import sys
import json
from crewai import Crew, Task, Process
from dotenv import load_dotenv
from agents.crewai_agents import get_market_analyst, get_competitor_analyst, get_strategy_advisor
from datetime import datetime
import os
from fpdf import FPDF
import openai
from core.download_utils import extract_text
from core.schemas import StartupProfile
from core.vector_store import clear_collection
from chains.pitch_deck_chain import run_pitch_deck_chain
from chains.technical_dd_chain import run_technical_dd_chain
from chains.founder_profiling_chain import run_founder_profiling_chain
from chains.market_sizing_chain import run_market_sizing_chain
from chains.financial_analysis_chain import run_financial_analysis_chain
from chains.competitive_intel_chain import run_competitive_intel_chain
from chains.risk_assessment_chain import run_risk_assessment_chain

# Load environment variables
load_dotenv()

# --- LLM-based summary/discussion ---
def generate_llm_discussion(deck_memo, market_analysis, competitor_analysis):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[Warning] OPENAI_API_KEY not set in environment.")
        return "[No LLM summary generated: missing API key]"
    client = openai.OpenAI(api_key=api_key)
    prompt = f"""
You are a senior venture capital analyst. Given the following investment memo (from a deck), market analysis, and competitor analysis, write a detailed, insightful discussion section for an investment memo. Summarize the findings, highlight key opportunities and risks, and provide your own perspective on the market, company, and competitive landscape. Be critical, thorough, and actionable.

Deck Memo:
{deck_memo}

Market Analysis:
{market_analysis}

Competitor Analysis:
{competitor_analysis}

Structure:
1. Summary of Key Findings
2. Opportunities
3. Risks
4. Analyst Commentary
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[Error generating LLM discussion: {e}]"

# --- PDF generation logic (reuse from generate_pdf_memo.py) ---
def save_memo_as_pdf(text: str, output_path: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in text.split("\n"):
        clean_line = line.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, clean_line)
    pdf.output(output_path)

# --- Deck extraction/classic pipeline ---
def run_deck_analysis(pdf_path):
    print(f"Extracting text from: {pdf_path}")
    try:
        text = extract_text(pdf_path)
    except Exception as e:
        print(f"Error extracting {pdf_path}: {e}")
        return None, None
    clear_collection()
    profile = StartupProfile()
    # Run all chains
    def run_pitch_deck_chain_with_text(full_text, profile):
        from chains.pitch_deck_chain import run_pitch_deck_chain_with_text as run_pitch_chain
        return run_pitch_chain(full_text, profile)
    def run_technical_dd_chain_with_text(full_text, profile):
        return run_technical_dd_chain(profile)
    def run_founder_profiling_chain_with_text(full_text, profile):
        return run_founder_profiling_chain(profile)
    def run_market_sizing_chain_with_text(full_text, profile):
        return run_market_sizing_chain(profile)
    def run_financial_analysis_chain_with_text(full_text, profile):
        return run_financial_analysis_chain(profile)
    def run_competitive_intel_chain_with_text(full_text, profile):
        return run_competitive_intel_chain(profile)
    def run_risk_assessment_chain_with_text(full_text, profile):
        return run_risk_assessment_chain(profile)
    profile = run_pitch_deck_chain_with_text(text, profile)
    profile = run_technical_dd_chain_with_text(text, profile)
    profile = run_founder_profiling_chain_with_text(text, profile)
    profile = run_market_sizing_chain_with_text(text, profile)
    profile = run_financial_analysis_chain_with_text(text, profile)
    profile = run_competitive_intel_chain_with_text(text, profile)
    profile = run_risk_assessment_chain_with_text(text, profile)
    # Format classic memo
    from generate_pdf_memo import format_memo
    deck_memo = format_memo(profile)
    # Use sector or company name for CrewAI
    market_opportunity = profile.sector or profile.name or "Unknown Market"
    return deck_memo, market_opportunity

# --- CrewAI orchestration ---
def run_crewai_analysis(market_opportunity, trace_id):
    print(f"Analyzing market opportunity: {market_opportunity}")
    market_analyst = get_market_analyst(trace_id)
    competitor_analyst = get_competitor_analyst(trace_id)
    strategy_advisor = get_strategy_advisor(trace_id)
    market_task = Task(
        description=f"""Analyze the market size and expected growth rate for market of {market_opportunity}.
        1. Estimate the total market size and growth rate (CAGR). Avoid taking the overall size of the AI market and randomly assuming a percentage of that market goes towards the subsegment market; instead, search for data on the specific subsegment data directly.
        2. Estimate the total number of potential customers in the target market.
        Provide a concise report with clear data points and sources.""",
        expected_output="""A detailed market analysis report including:
        1. Total market size with CAGR
        2. Total number of potential customers
        All with supporting data and sources links.""",
        agent=market_analyst,
        async_execution=False
    )
    competitor_task = Task(
        description=f"""Find the main AI startup player's for {market_opportunity}.
        1. Identify 3-4 specific AI startup competitors by name. Avoid generic players like OpenAI, Microsoft, Google, Anthropic, Hugging Face in results. Instead, focus on finding real company names of highly relevant players with bespoke competing products and focus.
        2. For each competitor, provide:
           - Company full name and website (if available)
           - Traction.""",
        expected_output="""A comprehensive competitor analysis including:
        1. Overview of 3-4 main AI startup competitors.
        2. For each competitor:
           - Company name and details
           - Detailed description of product offering.
           - Current known traction revenue, total customer's
           - Customer traction metrics if available.""",
        agent=competitor_analyst,
        async_execution=True
    )
    crew = Crew(
        agents=[market_analyst, competitor_analyst],
        tasks=[market_task, competitor_task],
        verbose=True,
        process=Process.hierarchical,
        manager_agent=strategy_advisor,
        planning=True,
    )
    print("Crew created, starting analysis...")
    result = crew.kickoff()
    print("Analysis completed")
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_crewai_analysis.py <path_to_pdf> [<trace_id>]")
        sys.exit(1)
    pdf_path = sys.argv[1]
    trace_id = sys.argv[2] if len(sys.argv) > 2 else f"trace-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    # 1. Extract and analyze deck
    deck_memo, market_opportunity = run_deck_analysis(pdf_path)
    if not deck_memo:
        print("Deck analysis failed. Exiting.")
        sys.exit(1)
    # 2. Run CrewAI analysis using extracted sector/name
    result = run_crewai_analysis(market_opportunity, trace_id)
    market_analysis_output = result.tasks_output[0].raw
    competitor_analysis_output = result.tasks_output[1].raw
    # 3. Generate LLM-based discussion/summary
    discussion = generate_llm_discussion(deck_memo, market_analysis_output, competitor_analysis_output)
    # 4. Format combined memo content
    current_date = datetime.now().strftime("%B %d, %Y")
    memo_text = f"""
INTEGRATED INVESTMENT MEMO\n{'='*60}\nAnalysis Date: {current_date}\nDeck File: {pdf_path}\nTrace ID: {trace_id}\n\n{'='*40}\nDECK-BASED MEMO\n{'='*40}\n{deck_memo}\n\n{'='*40}\nCREWAI MARKET ANALYSIS\n{'='*40}\n{market_analysis_output}\n\n{'='*40}\nCREWAI COMPETITOR ANALYSIS\n{'='*40}\n{competitor_analysis_output}\n\n{'='*40}\nDISCUSSION & ANALYST SUMMARY\n{'='*40}\n{discussion}\n\n---\nGenerated by Integrated VC Analysis System\n"""
    # 5. Save as PDF
    output_dir = "out"
    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"memo_Integrated_{os.path.basename(pdf_path).replace('.pdf','')}_{date_str}.pdf"
    output_path = os.path.join(output_dir, filename)
    save_memo_as_pdf(memo_text, output_path)
    print(f"\nPDF memo saved to {output_path}")
    # Also print the memo text for reference
    print(memo_text) 