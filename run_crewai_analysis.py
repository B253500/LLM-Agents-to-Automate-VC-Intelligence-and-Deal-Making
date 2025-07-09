import sys
import json
from crewai import Crew, Task, Process
from dotenv import load_dotenv
from agents.crewai_agents import get_market_analyst, get_competitor_analyst, get_strategy_advisor, get_website_finder_agent, get_financial_research_agent
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

# Portkey is a proxy/gateway service for OpenAI and other LLM APIs that allows you to route, monitor, and manage LLM requests. It can provide features like API key management, usage tracking, fallback routing, and observability for LLM calls. In this codebase, Portkey is used to optionally route OpenAI API calls through a Portkey gateway if configured, otherwise it falls back to direct OpenAI usage.

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

# --- Website finder integration ---
def run_website_finder(company_name, founder_name=None, sector=None, trace_id=None):
    website_finder_agent = get_website_finder_agent(trace_id)
    from crewai import Task, Crew, Process
    website_task = Task(
        description=f"Find the official website for the company named '{company_name}' founded by '{founder_name}' in sector '{sector}'.",
        expected_output="The official website URL for the company, with warning if ambiguous.",
        agent=website_finder_agent,
        async_execution=False
    )
    crew = Crew(
        agents=[website_finder_agent],
        tasks=[website_task],
        verbose=False,
        process=Process.sequential,
        manager_agent=None,
        planning=False,
    )
    result = crew.kickoff()
    return result.tasks_output[0].raw.strip()

# --- Financial research integration ---
def run_financial_research(company_name, founder_name=None, sector=None, trace_id=None):
    financial_agent = get_financial_research_agent(trace_id)
    from crewai import Task, Crew, Process
    financial_task = Task(
        description=f"Find the latest available financial data for the company {company_name} founded by {founder_name} in sector {sector} from the internet.",
        expected_output="A summary of the latest funding, valuation, and revenue for the company, with sources and warning if ambiguous.",
        agent=financial_agent,
        async_execution=False
    )
    crew = Crew(
        agents=[financial_agent],
        tasks=[financial_task],
        verbose=False,
        process=Process.sequential,
        manager_agent=None,
        planning=False,
    )
    result = crew.kickoff()
    return result.tasks_output[0].raw.strip()

# --- LLM-powered financial commentary ---
def generate_financial_commentary(profile, financial_research_output=None):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "[No LLM commentary generated: missing API key]"
    client = openai.OpenAI(api_key=api_key)
    context = f"""
Company: {profile.name}\nSector: {profile.sector}\nCash Burn (12m): {profile.cash_burn_12m}\nRunway (months): {profile.runway_months}\nImplied Valuation: {profile.implied_valuation}\nRevenue: {getattr(profile, 'revenue', None)}\nProjected Revenue: {getattr(profile, 'projected_revenue', None)}\nFunding Sought: {getattr(profile, 'funding_sought', None)}\n"""
    if financial_research_output:
        context += f"\nAdditional Internet Research:\n{financial_research_output}\n"
    prompt = f"""
You are a top-tier VC analyst. Given the following financial data, provide a short, critical analysis of the company's financial health, model, and risks. If no financial data is available, explain the risks and recommend next steps for diligence.

{context}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error generating financial commentary: {e}]"

# --- Deck extraction/classic pipeline ---
def run_deck_analysis(pdf_path, trace_id=None):
    print(f"Extracting text from: {pdf_path}")
    try:
        text = extract_text(pdf_path)
    except Exception as e:
        print(f"Error extracting {pdf_path}: {e}")
        return None, None, None
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
    # --- Website finder integration ---
    if profile.name:
        website = run_website_finder(profile.name, profile.founder_name, profile.sector, trace_id)
        profile.website = website
        print(f"[Website Finder] Found website: {website}")
    else:
        print("[Website Finder] No company name found, skipping website search.")
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
    return deck_memo, market_opportunity, profile

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

def generate_detailed_summary(profile):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[Warning] OPENAI_API_KEY not set in environment.")
        return "[No LLM summary generated: missing API key]"
    client = openai.OpenAI(api_key=api_key)
    prompt = f"""
You are a top-tier VC analyst. Given the following extracted company profile, generate a detailed executive summary covering:
- Company overview
- Product/service
- Business model
- Market opportunity
- Team/founders
- Traction/customers
- Funding stage
- Key risks and recommendations

Profile:
{profile.model_dump_json(indent=2)}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=900,
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[Error generating detailed summary: {e}]"

def format_integrated_memo(profile, crewai_outputs, llm_summary, meta):
    # --- Source attribution and explicit 'not found' logic ---
    # Market analysis source
    market_analysis = crewai_outputs['market_analysis']
    if market_analysis.startswith('Market (from deck):'):
        market_source = 'Source: Company pitch deck'
    elif 'GrandViewResearch' in market_analysis or 'MarketsandMarkets' in market_analysis or 'Verified Market Research' in market_analysis:
        market_source = 'Source: ' + ', '.join([src for src in ['GrandViewResearch', 'MarketsandMarkets', 'Verified Market Research'] if src in market_analysis])
    elif '[Market Research] No specific market data found.' in market_analysis:
        market_source = 'Source: No specific market data could be found from deck or CrewAI research.'
    else:
        market_source = 'Source: CrewAI agent estimate'

    # Competitor analysis source/logic
    competitor_analysis = crewai_outputs['competitor_analysis']
    if '[Competitor Analysis] Not available.' in competitor_analysis or not competitor_analysis.strip():
        competitor_analysis = 'No specific competitors could be identified from the deck or CrewAI research.'
        competitor_source = 'Source: Deck and CrewAI research'
    else:
        competitor_source = 'Source: CrewAI research'

    # --- Financial analysis section ---
    financial_fields = [
        ('Cash Burn (12m)', profile.cash_burn_12m),
        ('Runway (months)', profile.runway_months),
        ('Implied Valuation', profile.implied_valuation),
        ('Revenue', getattr(profile, 'revenue', None)),
        ('Projected Revenue', getattr(profile, 'projected_revenue', None)),
        ('Funding Sought', getattr(profile, 'funding_sought', None)),
    ]
    has_financials = any(v is not None for _, v in financial_fields)
    financial_research_output = meta.get('financial_research_output')
    financial_warning = meta.get('financial_warning')
    financial_commentary = meta.get('financial_commentary')
    if has_financials:
        financial_section = 'FINANCIAL ANALYSIS\n-------------\n' + '\n'.join([
            f"{label}: ${value}M" if value is not None else f"{label}: N/A" for label, value in financial_fields
        ]) + '\n'
        if financial_research_output:
            financial_section += f"\nAdditional Internet Research:\n{financial_research_output}\n"
        if financial_warning:
            financial_section += f"\n{financial_warning}\n"
    else:
        if financial_research_output:
            financial_section = f'FINANCIAL ANALYSIS\n-------------\nNo financial data was available from the deck or extraction.\n\nAdditional Internet Research:\n{financial_research_output}\n'
            if financial_warning:
                financial_section += f"\n{financial_warning}\n"
        else:
            financial_section = 'FINANCIAL ANALYSIS\n-------------\nNo financial data was available from the deck or extraction, and no additional financial data was found online.\n'
    if financial_commentary:
        financial_section += f"\nFinancial Commentary:\n{financial_commentary}\n"

    # --- Competitor section: always list or state none found, use bullet points ---
    competitor_analysis = crewai_outputs['competitor_analysis']
    competitor_source = 'Source: Deck and CrewAI research'
    competitors_list = []
    if competitor_analysis and competitor_analysis.strip() and 'No specific competitors' not in competitor_analysis:
        # Try to extract bullet points from competitor_analysis
        lines = [line.strip() for line in competitor_analysis.split('\n') if line.strip()]
        for line in lines:
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                competitors_list.append(line)
            elif any(url in line for url in ['http', 'www.', '.ai', '.com']):
                competitors_list.append(f"• {line}")
        if not competitors_list:
            competitors_list = [f"• {line}" for line in lines]
    competitor_section = ''
    if competitors_list:
        competitor_section = 'COMPETITOR ANALYSIS\n-------------------\n' + '\n'.join(competitors_list) + f'\n{competitor_source}\n'
    else:
        competitor_section = 'COMPETITOR ANALYSIS\n-------------------\nNo direct competitors could be identified from the deck or external research. This may indicate a unique market position or a lack of available data.\n' + f'{competitor_source}\n'

    # --- Website warning in executive summary ---
    website_warning = meta.get('website_warning')
    website_line = f"Website: {profile.website}"
    if website_warning:
        website_line += f"\nWebsite Warning: {website_warning}"

    detailed_summary = generate_detailed_summary(profile)
    summary = f"""
INTEGRATED INVESTMENT MEMO
============================================================
Analysis Date: {meta['date']}
Deck File: {meta['deck_file']}
Trace ID: {meta['trace_id']}

EXECUTIVE SUMMARY (Deck-Based)
------------------------------
Company: {profile.name}
Sector: {profile.sector}
Founders: {profile.founder_name}
{website_line}
Funding Stage: {profile.funding_stage}
Market: TAM ${profile.TAM}M, SAM ${profile.SAM}M, SOM ${profile.SOM}M
Market Source: {market_source}
Product/Service: {profile.moat_strength or profile.tech_maturity or 'N/A'}
Key Investment Drivers: {profile.moat_strength or 'N/A'}
Scores: Market {min(10, max(1, int((profile.TAM or 0) / 100)))}/10, Team {min(10, max(1, int((profile.founder_fit_score or 0.5) * 10)))}/10, Tech {profile.tech_maturity or 'N/A'}
Investment Thesis: {profile.name or 'The company'} represents a compelling investment opportunity in the {profile.sector or 'emerging'} sector.
Risks: {', '.join(profile.risk_flags) if profile.risk_flags else 'N/A'}
Recommendation: {'PROCEED' if (profile.founder_fit_score or 0) > 0.6 and (profile.TAM or 0) > 100 else 'FURTHER DUE DILIGENCE' if (profile.founder_fit_score or 0) > 0.4 else 'PASS'}
"""

    crewai_section = f"""
CREWAI AGENTIC ANALYSIS
-----------------------
MARKET ANALYSIS
{market_analysis}
{market_source}

{competitor_section}
PRODUCT/SERVICE DEEP DIVE
-------------------------
Maturity Level: {profile.tech_maturity or 'N/A'}
Technical Moat: {profile.moat_strength or 'N/A'}
Scalability: {profile.tech_maturity or 'N/A'} architecture supports growth
Security: {profile.tech_maturity or 'N/A'} includes robust security measures

TEAM DEEP DIVE
--------------
Founders: {profile.founder_name or 'N/A'}
Founder Fit Score: {profile.founder_fit_score or 'N/A'} / 1.0
Prior Exits: {profile.prior_exits or '0'}
Sector Experience: {profile.sector or 'N/A'}

{financial_section}
RISK ANALYSIS
-------------
Overall Risk Level: {'LOW' if profile.risk_score and profile.risk_score < 0.3 else 'MEDIUM' if profile.risk_score and profile.risk_score < 0.7 else 'HIGH'}
Risk Score: {profile.risk_score or 'N/A'} / 1.0
Identified Risks: {', '.join(profile.risk_flags) if profile.risk_flags else 'N/A'}
"""

    summary_section = f"""
LLM DISCUSSION & ANALYST SUMMARY
--------------------------------
{llm_summary}
"""

    return summary + crewai_section + summary_section

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_crewai_analysis.py <path_to_pdf> [<trace_id>]")
        sys.exit(1)
    pdf_path = sys.argv[1]
    trace_id = sys.argv[2] if len(sys.argv) > 2 else f"trace-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 1. Extract and analyze deck (deck-first extraction)
    deck_memo, market_opportunity, profile = run_deck_analysis(pdf_path, trace_id)
    if not deck_memo or not profile:
        print("Deck analysis failed. Exiting.")
        sys.exit(1)

    # 2. Enrichment (website, founder, market) with deduplication and retry logic
    # --- Website finder ---
    website = None
    website_warning = None
    if profile.name:
        website_result = run_website_finder(profile.name, profile.founder_name, profile.sector, trace_id)
        if "Warning:" in website_result:
            website, website_warning = website_result.split("Warning:", 1)
            website = website.strip()
            website_warning = website_warning.strip()
        else:
            website = website_result
        profile.website = website
        print(f"[Website Finder] Found website: {website}")
        if website_warning:
            print(f"[Website Finder] {website_warning}")
    else:
        print("[Website Finder] No company name found, skipping website search.")

    # --- Founder enrichment (placeholder for future LinkedIn/other enrichment) ---
    # Only one query, fallback if needed (not implemented, but structure is here)
    # founder_info = find_founder_info(profile.founder_name)
    # if not founder_info:
    #     founder_info = find_founder_info_fallback(profile.founder_name)

    # --- Market research (deduplication: use deck if specific, else CrewAI, retry once if generic) ---
    def is_generic_market(market_str):
        if not market_str:
            return True
        generic_terms = ["overall AI market", "general AI market", "unknown", "N/A", "not specified", "not available"]
        return any(term.lower() in market_str.lower() for term in generic_terms)

    # Prefer deck market data if available and not generic
    deck_market_data = f"TAM ${profile.TAM}M, SAM ${profile.SAM}M, SOM ${profile.SOM}M" if profile.TAM or profile.SAM or profile.SOM else None
    use_deck_market = deck_market_data and not is_generic_market(deck_market_data)
    market_analysis_output = None
    if use_deck_market:
        market_analysis_output = f"Market (from deck): {deck_market_data}"
    else:
        # Run CrewAI market research, retry once if generic
        result = run_crewai_analysis(market_opportunity, trace_id)
        market_analysis_output = result.tasks_output[0].raw
        if is_generic_market(market_analysis_output):
            print("[Market Research] First CrewAI result was generic, retrying...")
            result_retry = run_crewai_analysis(market_opportunity, trace_id)
            market_analysis_output = result_retry.tasks_output[0].raw
        # Use only the first specific finding
        if is_generic_market(market_analysis_output):
            market_analysis_output = "[Market Research] No specific market data found."
    # Competitor analysis (CrewAI, one query)
    competitor_analysis_output = None
    if 'result' in locals() and hasattr(result, 'tasks_output') and len(result.tasks_output) > 1:
        competitor_analysis_output = result.tasks_output[1].raw
    else:
        competitor_analysis_output = "[Competitor Analysis] Not available."

    # 2b. Financial research via CrewAI if financials are missing or incomplete
    financial_fields = [profile.cash_burn_12m, profile.runway_months, profile.implied_valuation, getattr(profile, 'revenue', None), getattr(profile, 'projected_revenue', None), getattr(profile, 'funding_sought', None)]
    has_financials = any(v is not None for v in financial_fields)
    financial_research_output = None
    financial_warning = None
    if not has_financials and profile.name:
        print("[Financial Research] No financials found in deck, running CrewAI financial research agent...")
        financial_result = run_financial_research(profile.name, profile.founder_name, profile.sector, trace_id)
        if "Warning:" in financial_result:
            financial_research_output, financial_warning = financial_result.split("Warning:", 1)
            financial_research_output = financial_research_output.strip()
            financial_warning = financial_warning.strip()
        else:
            financial_research_output = financial_result
        print(f"[Financial Research] Output: {financial_research_output}")
        if financial_warning:
            print(f"[Financial Research] {financial_warning}")
    else:
        financial_research_output = None

    # 3. LLM-powered financial commentary
    financial_commentary = generate_financial_commentary(profile, financial_research_output)

    # 3. Reasoning & Analysis (best LLM, using all context)
    # (Classic chains already run in run_deck_analysis, so profile is up-to-date)
    # You can add further CrewAI/LLM reasoning here if needed

    # 4. Memo Synthesis (avoid duplication, use only best findings)
    discussion = generate_llm_discussion(deck_memo, market_analysis_output, competitor_analysis_output)
    current_date = datetime.now().strftime("%B %d, %Y")
    meta = {
        'date': current_date,
        'deck_file': pdf_path,
        'trace_id': trace_id,
        'financial_research_output': financial_research_output,
        'financial_warning': financial_warning,
        'website_warning': website_warning,
        'financial_commentary': financial_commentary
    }
    crewai_outputs = {
        'market_analysis': market_analysis_output,
        'competitor_analysis': competitor_analysis_output
    }
    memo_text = format_integrated_memo(profile, crewai_outputs, discussion, meta)
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
    # Print detailed executive summary (fix bug)
    detailed_summary = generate_detailed_summary(profile)
    print("\nDETAILED EXECUTIVE SUMMARY:\n" + detailed_summary) 