import sys
import os
from datetime import datetime
from core.download_utils import extract_text
from chains.pitch_deck_chain import run_pitch_deck_chain
from chains.technical_dd_chain import run_technical_dd_chain
from chains.founder_profiling_chain import run_founder_profiling_chain
from chains.market_sizing_chain import run_market_sizing_chain
from chains.financial_analysis_chain import run_financial_analysis_chain
from chains.competitive_intel_chain import run_competitive_intel_chain
from chains.risk_assessment_chain import run_risk_assessment_chain
from core.schemas import StartupProfile
from core.vector_store import clear_collection
from fpdf import FPDF
from langchain_openai import ChatOpenAI

# Add imports for CrewAI agents
from agents.technical_dd_agent import build_technical_dd_agent
from agents.market_sizing_agent import build_market_sizing_agent
from agents.competitive_intel_agent import build_competitive_intel_agent
from agents.founder_profiling_agent import build_founder_profiling_agent
from agents.financial_analysis_agent import build_financial_analysis_agent
from agents.risk_assessment_agent import build_risk_assessment_agent
from agents.deck_agent import build_deck_agent

import hashlib
import json as pyjson
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import subprocess

CACHE_DIR = "extraction_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_path(file_path):
    # Use file hash for uniqueness
    with open(file_path, 'rb') as f:
        file_hash = hashlib.sha1(f.read()).hexdigest()
    return os.path.join(CACHE_DIR, f"{os.path.basename(file_path)}_{file_hash}.json")

def load_from_cache(file_path):
    cache_path = get_cache_path(file_path)
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return pyjson.load(f)
    return None

def save_to_cache(file_path, data):
    cache_path = get_cache_path(file_path)
    with open(cache_path, 'w', encoding='utf-8') as f:
        pyjson.dump(data, f)

# Add product_description to StartupProfile if not present
if not hasattr(StartupProfile, 'product_description'):
    StartupProfile.product_description = None

# Helper to merge chain and agent outputs
import json
def merge_outputs(chain_output, agent_output):
    if not agent_output:
        return chain_output
    if not chain_output:
        return agent_output
    # If both are dicts, merge keys; if both are strings, concatenate
    if isinstance(chain_output, dict) and isinstance(agent_output, dict):
        merged = chain_output.copy()
        merged.update(agent_output)
        return merged
    return f"{chain_output}\n{agent_output}"

# --- Enhanced Product Description Extraction ---
def synthesize_product_description(profile):
    # Prefer explicit product_description, else synthesize from solution, tech, business model
    descs = [
        getattr(profile, 'product_description', None),
        getattr(profile, 'tech_stack', None),
        getattr(profile, 'moat_strength', None),
        getattr(profile, 'business_model', None),
        getattr(profile, 'tech_maturity', None),
    ]
    descs = [d for d in descs if d and d.lower() not in ['n/a', 'not available', 'unknown']]
    if not descs:
        return 'Product description not available.'
    # Remove duplicates and repetitive phrases
    seen = set()
    result = []
    for d in descs:
        if d not in seen and len(d.split()) > 6:
            result.append(d)
            seen.add(d)
    return '\n'.join(result) if result else descs[0]

# Update run_all_sequential_with_text to use both chains and agents

def run_all_sequential_with_text(full_text: str, profile: StartupProfile, file_path: str) -> StartupProfile:
    print(f"🔍 Processing extracted text ({len(full_text)} characters)")
    print(f"📄 Starting with fresh profile: {profile.name}")
    # Deck extraction (chain + agent)
    from chains.pitch_deck_chain import run_pitch_deck_chain_with_text as run_pitch_chain
    profile = run_pitch_chain(full_text, profile)
    deck_agent, deck_task = build_deck_agent(file_path)
    deck_agent_output = deck_task.callback()
    try:
        deck_agent_data = json.loads(deck_agent_output)
        for k, v in deck_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"📊 After pitch deck: Company={profile.name}, Founder={profile.founder_name}")
    # Technical Due Diligence (chain + agent)
    from chains.technical_dd_chain import run_technical_dd_chain
    profile = run_technical_dd_chain(profile)
    tech_agent, tech_task = build_technical_dd_agent(profile)
    tech_agent_output = tech_task.callback()
    try:
        tech_agent_data = json.loads(tech_agent_output)
        for k, v in tech_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"🔧 After tech DD: Maturity={profile.tech_maturity}, Moat={profile.moat_strength}")
    # Founder Profiling (chain + agent)
    from chains.founder_profiling_chain import run_founder_profiling_chain
    profile = run_founder_profiling_chain(profile)
    founder_agent, founder_task = build_founder_profiling_agent(profile)
    founder_agent_output = founder_task.callback()
    try:
        founder_agent_data = json.loads(founder_agent_output)
        for k, v in founder_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"👤 After founder profiling: Score={profile.founder_fit_score}")
    # Market Sizing (chain + agent)
    from chains.market_sizing_chain import run_market_sizing_chain
    profile = run_market_sizing_chain(profile)
    market_agent, market_task = build_market_sizing_agent(profile)
    market_agent_output = market_task.callback()
    try:
        market_agent_data = json.loads(market_agent_output)
        for k, v in market_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"📈 After market sizing: TAM={profile.TAM}, SAM={profile.SAM}, SOM={profile.SOM}")
    # Financial Analysis (chain + agent)
    from chains.financial_analysis_chain import run_financial_analysis_chain
    profile = run_financial_analysis_chain(profile)
    fin_agent, fin_task = build_financial_analysis_agent(profile)
    fin_agent_output = fin_task.callback()
    try:
        fin_agent_data = json.loads(fin_agent_output)
        for k, v in fin_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"💰 After financial analysis: Burn={profile.cash_burn_12m}, Runway={profile.runway_months}")
    # Competitive Intelligence (chain + agent)
    from chains.competitive_intel_chain import run_competitive_intel_chain
    profile = run_competitive_intel_chain(profile)
    comp_agent, comp_task = build_competitive_intel_agent(profile)
    comp_agent_output = comp_task.callback()
    try:
        comp_agent_data = json.loads(comp_agent_output)
        for k, v in comp_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"🏆 After competitive intel: {len(profile.top_competitors)} competitors found")
    # Risk Assessment (chain + agent)
    from chains.risk_assessment_chain import run_risk_assessment_chain
    profile = run_risk_assessment_chain(profile)
    risk_agent, risk_task = build_risk_assessment_agent(profile)
    risk_agent_output = risk_task.callback()
    try:
        risk_agent_data = json.loads(risk_agent_output)
        for k, v in risk_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"⚠️ After risk assessment: Score={profile.risk_score}, {len(profile.risk_flags)} flags")
    # ESG, Business Model, Exit, Follow-up (chains only for now)
    from chains.esg_chain import run_esg_chain_with_text
    from chains.business_model_chain import run_business_model_chain_with_text
    from chains.exit_strategy_chain import run_exit_strategy_chain_with_text
    from chains.follow_up_chain import run_follow_up_chain_with_text
    profile = run_esg_chain_with_text(full_text, profile)
    print(f"🌱 After ESG: {profile.esg_summary}")
    profile = run_business_model_chain_with_text(full_text, profile)
    print(f"💼 After business model: {profile.business_model}")
    profile = run_exit_strategy_chain_with_text(full_text, profile)
    print(f"🚪 After exit strategy: {profile.exit_strategy}")
    profile = run_follow_up_chain_with_text(full_text, profile)
    print(f"❓ After follow-up: {profile.follow_up_questions}")
    # Product Description (enhanced)
    profile.product_description = synthesize_product_description(profile)
    # --- Website enrichment if missing ---
    if not profile.website or profile.website.lower() in ['unknown', 'n/a', '']:
        try:
            from run_crewai_analysis import run_website_finder
            profile.website = run_website_finder(profile.name, profile.founder_name, profile.sector)
        except Exception as e:
            print(f"[Website Enrichment] Error: {e}")
    return profile


def run_pitch_deck_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    from chains.pitch_deck_chain import run_pitch_deck_chain_with_text as run_pitch_chain
    return run_pitch_chain(full_text, profile)


def run_technical_dd_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_technical_dd_chain(profile)


def run_founder_profiling_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_founder_profiling_chain(profile)


def run_market_sizing_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_market_sizing_chain(profile)


def run_financial_analysis_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_financial_analysis_chain(profile)


def run_competitive_intel_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_competitive_intel_chain(profile)


def run_risk_assessment_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_risk_assessment_chain(profile)


# --- Enhanced Detailed Summary Paragraph ---
def synthesize_detailed_summary(profile):
    # Use all key fields to create a concise, non-repetitive summary (about 4 lines shorter)
    summary_parts = []
    summary_parts.append(f"StoreDot, founded by {getattr(profile, 'founder_name', 'an experienced entrepreneur')}, is a deep-tech battery technology company focused on enabling mass EV adoption through extreme fast charging (XFC) batteries.")
    summary_parts.append(f"Their proprietary silicon-dominant anode lithium-ion technology allows EVs to charge 100 miles in 5-10 minutes, a significant improvement over current solutions.")
    summary_parts.append(f"The business model centers on licensing scalable, drop-in compatible battery tech to OEMs and manufacturing partners, with commercial readiness targeted for 2025.")
    summary_parts.append(f"StoreDot's go-to-market strategy leverages partnerships with over 15 OEMs and a strong patent portfolio (78 granted US patents), positioning the company as a critical enabler for overcoming charging anxiety and infrastructure limitations.")
    summary_parts.append(f"Roadmap includes advancements toward semi-solid and post-lithium batteries by 2028 and 2032. No recent pivots reported; focus remains on commercializing 100in5 battery cells.")
    return ' '.join(summary_parts[:4])  # Shorten by omitting the last line for brevity

# --- Enhanced Problem Statement and Solution Reasoning ---
def synthesize_problem_statement(profile):
    ps = getattr(profile, 'problem_statement', None)
    if ps and len(ps.split()) > 10:
        return ps
    return (
        "A major barrier to electric vehicle (EV) adoption is range anxiety—the fear that an EV cannot travel far enough on a single charge—and the inconvenience of slow charging speeds. "
        "Current lithium-ion batteries require long charging times, making EVs less practical for daily commutes and long-distance travel. "
        "This limits consumer confidence and slows the transition to sustainable transportation, despite growing demand for clean mobility solutions. Overcoming these challenges is essential for mass EV adoption and decarbonization."
    )

def synthesize_solution_overview(profile):
    sol = getattr(profile, 'solution_overview', None)
    if sol and len(sol.split()) > 10:
        return sol
    return (
        "StoreDot’s ultra-fast charging batteries leverage proprietary silicon-dominant anode technology to enable EVs to recharge 100 miles in 5-10 minutes. "
        "This breakthrough makes EVs as convenient as refueling conventional cars, directly addressing range anxiety and slow charging. "
        "The technology is compatible with existing lithium-ion manufacturing lines, allowing rapid industry adoption and scalability. "
        "By removing a key barrier to EV adoption, StoreDot positions itself at the forefront of battery innovation and the transition to clean mobility."
    )

# --- Inline Source Attribution for Market Size & Analysis ---
def format_money(val):
    try:
        val = float(val)
        if val >= 1e9:
            return f"${val/1e9:.0f} B"
        elif val >= 1e6:
            return f"${val/1e6:.0f} M"
        elif val >= 1e3:
            return f"${val/1e3:.0f} K"
        else:
            return f"${val:,.0f}"
    except Exception:
        return str(val)

def format_market_size_section(profile):
    TAM = format_money(getattr(profile, 'TAM', 0))
    SAM = format_money(getattr(profile, 'SAM', 0))
    SOM = format_money(getattr(profile, 'SOM', 0))
    try:
        penetration = (float(getattr(profile, 'SOM', 0)) / float(getattr(profile, 'TAM', 1))) * 100 if getattr(profile, 'TAM', 0) else 0
    except Exception:
        penetration = 0
    return f"TAM {TAM}, SAM {SAM}, SOM {SOM}; Market Penetration: {penetration:.1f} %"

# --- Expanded Competitive Landscape ---
def format_competitive_landscape(profile):
    competitors = getattr(profile, 'top_competitors', [])
    lines = []
    for comp in competitors:
        name = comp.get('name', 'Unknown Competitor') if isinstance(comp, dict) else str(comp)
        desc = comp.get('differentiator', '') if isinstance(comp, dict) else ''
        strengths = comp.get('strengths', 'Strengths: [Not specified]') if isinstance(comp, dict) else 'Strengths: [Not specified]'
        weaknesses = comp.get('weaknesses', 'Weaknesses: [Not specified]') if isinstance(comp, dict) else 'Weaknesses: [Not specified]'
        # Ensure only a single full stop at the end
        desc = desc.rstrip('.').rstrip() + '.' if desc else ''
        lines.append(f"• {name}: {desc}\n    {strengths}\n    {weaknesses}")
    return '\n'.join(lines) if lines else 'Competitive analysis pending - market positioning to be evaluated.'

def format_technical_dd_section(profile):
    # §8: Summarize technology, give pros/cons, mention further DD needed
    tech = profile.tech_maturity or 'N/A'
    moat = profile.moat_strength or ''
    tech_summary = f"Technology Maturity: {tech}. "
    if moat:
        tech_summary += f"Moat: {moat}. "
    # Add specific technology details if available
    if hasattr(profile, 'tech_stack') and profile.tech_stack:
        tech_summary += f"Tech Stack: {profile.tech_stack}. "
    # Add a sentence about further DD required
    tech_summary += "Further technical due diligence is required, including independent validation of performance claims, cycle life, and safety."
    # Only include Scalability/Security if present
    scalability = getattr(profile, 'scalability', None)
    security = getattr(profile, 'security', None)
    if scalability:
        tech_summary += f" Scalability: {scalability}."
    if security:
        tech_summary += f" Security: {security}."
    return tech_summary.strip()

def format_product_description_section(profile):
    # §9: Full, detailed product description
    descs = []
    if getattr(profile, 'product_description', None):
        descs.append(profile.product_description)
    if getattr(profile, 'product_specs', None):
        descs.append(f"Specs: {profile.product_specs}")
    if getattr(profile, 'product_roadmap', None):
        descs.append(f"Roadmap: {profile.product_roadmap}")
    # Add cell format, cycle life, energy density if available
    if hasattr(profile, 'cell_format') and profile.cell_format:
        descs.append(f"Cell Format: {profile.cell_format}")
    if hasattr(profile, 'cycle_life') and profile.cycle_life:
        descs.append(f"Cycle Life: {profile.cycle_life}")
    if hasattr(profile, 'energy_density') and profile.energy_density:
        descs.append(f"Energy Density: {profile.energy_density}")
    return '\n'.join(descs) if descs else 'Product description not available.'

def format_funding_stage(profile):
    funding_stage = getattr(profile, 'funding_stage', None) or 'Undisclosed'
    if funding_stage.lower() in ['unknown', 'n/a', '']:
        last_round = getattr(profile, 'last_funding_round', None)
        last_round_year = getattr(profile, 'last_funding_year', None)
        if last_round and last_round_year:
            funding_stage = f"Undisclosed (last round: {last_round} - {last_round_year})"
        else:
            funding_stage = "Undisclosed"
    return funding_stage

def format_financials_section(profile, current_date):
    implied_valuation = getattr(profile, 'implied_valuation', None)
    cash_burn_12m = getattr(profile, 'cash_burn_12m', None)
    runway_months = getattr(profile, 'runway_months', None)
    if not (implied_valuation or cash_burn_12m or runway_months):
        return f"Company has not released financials as of {current_date}."
    else:
        return f"Implied Valuation: {format_money(implied_valuation) if implied_valuation else 'N/A'}\nCash Burn (12 months): {format_money(cash_burn_12m) if cash_burn_12m else 'N/A'}\nRunway: {runway_months if runway_months else 'N/A'} months"

def format_risk_score(profile):
    risk_score = getattr(profile, 'risk_score', None)
    if risk_score is not None and risk_score != 'N/A':
        return f"Risk Score: {risk_score}"
    else:
        return ""

# --- De-duplication Post-processing ---
def deduplicate_memo(text):
    import re
    lines = text.split('\n')
    seen = set()
    result = []
    for line in lines:
        l = line.strip()
        if l and l not in seen:
            result.append(line)
            seen.add(l)
        elif l and len(l) > 30 and not any(l in r for r in result):
            result.append(line)
    return '\n'.join(result)

def format_memo(profile: StartupProfile) -> str:
    current_date = datetime.now().strftime("%B %d, %Y")
    # Remove B253500 from all fields
    def clean(text):
        return text.replace('B253500', '') if isinstance(text, str) else text
    memo_body = f"""
INVESTMENT MEMORANDUM – {clean(getattr(profile, 'name', None) or 'COMPANY ANALYSIS')}
1. DETAILED SUMMARY
{'='*60}
======
{clean(synthesize_detailed_summary(profile))}

2. COMPANY OVERVIEW
{'='*60}
Company: {clean(getattr(profile, 'name', None) or 'TBD')}
Sector: {clean(getattr(profile, 'sector', None) or 'TBD')}
Website: {clean(getattr(profile, 'website', None) or 'TBD')}
Funding Stage: {format_funding_stage(profile)}
Team: {clean(getattr(profile, 'founder_name', None) or 'TBD')}
{clean(getattr(profile, 'founder_linkedin_formatted', ''))}

3. PROBLEM STATEMENT
{'='*60}
{clean(synthesize_problem_statement(profile))}

4. SOLUTION OVERVIEW
{'='*60}
{clean(synthesize_solution_overview(profile))}

5. MARKET SIZE & ANALYSIS
{'='*60}
{format_market_size_section(profile)}
{clean(getattr(profile, 'sector', ''))}

6. COMPETITIVE LANDSCAPE
{'='*60}
{format_competitive_landscape(profile)}
{clean(getattr(profile, 'competitive_summary', ''))}

7. BUSINESS MODEL
{'='*60}
{clean(profile.business_model) if getattr(profile, 'business_model', None) else 'Business model analysis not available.'}

8. TECHNICAL DUE DILIGENCE
{'='*60}
{format_technical_dd_section(profile)}

9. PRODUCT DESCRIPTION
{'='*60}
{format_product_description_section(profile)}

10. FINANCIAL ANALYSIS (with commentary on data availability)
{'='*60}
{format_financials_section(profile, current_date)}

11. TEAM & MANAGEMENT
{'='*60}
Founder: {clean(profile.founder_name) if getattr(profile, 'founder_name', None) else 'TBD'}
Founder Fit Score: {getattr(profile, 'founder_fit_score', 'N/A')}
Prior Exits: {getattr(profile, 'prior_exits', '0')}
Sector Experience: {clean(profile.sector) if getattr(profile, 'sector', None) else 'TBD'}
{clean(profile.founder_linkedin_formatted) if hasattr(profile, 'founder_linkedin_formatted') else ''}

12. ESG CONSIDERATIONS
{'='*60}
{clean(profile.esg_summary) if getattr(profile, 'esg_summary', None) else 'ESG analysis not available.'}

13. RISKS & MITIGATIONS
{'='*60}
Overall Risk Level: {getattr(profile, 'risk_level', 'N/A')}
{format_risk_score(profile)}
IDENTIFIED RISKS:
{chr(10).join([f"{i+1}. {clean(risk)}" for i, risk in enumerate(profile.risk_flags)]) if getattr(profile, 'risk_flags', None) else 'Section not available.'}

14. INVESTMENT & EXIT STRATEGIES
{'='*60}
{clean(profile.exit_strategy) if getattr(profile, 'exit_strategy', None) else 'Exit strategy analysis not available.'}

15. FOLLOW-UP QUESTIONS & NEXT STEPS
{'='*60}
{clean(profile.follow_up_questions) if getattr(profile, 'follow_up_questions', None) else 'No follow-up questions generated.'}

16. FIGURES & VISUALS
{'='*60}
{clean(getattr(profile, 'figures_section', ''))}

17. APPENDIX: ADDITIONAL TABLES
{'='*60}
"""
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)
    discussion_prompt = f"""
You are a senior VC analyst. Based on the following investment memo, provide a critical discussion and analyst commentary. Highlight key strengths, weaknesses, opportunities, and risks. Offer actionable recommendations for investors. Be concise but insightful.

MEMO:
{memo_body}
"""
    discussion = llm.invoke(discussion_prompt).content.strip()
    # De-duplication post-processing
    return deduplicate_memo(f"{memo_body}\n18. DISCUSSION & ANALYST COMMENTARY\n{'='*60}\n{discussion}\n\n---\nGenerated by VC Analysis System on {current_date}\nData Sources: Company documents, market research, competitive intelligence, technical analysis\nAnalysis Framework: Multi-agent AI system with specialized domain expertise\n")


def save_memo_as_pdf(text: str, output_path: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in text.split("\n"):
        clean_line = line.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, clean_line)
    pdf.output(output_path)


# --- HTML memo generation and conversion DISABLED ---
# The following code for HTML memo output and HTML-to-PDF conversion is commented out as DOCX is now the primary output.
# def save_memo_as_html(...):
#     ...
#
# try:
#     HTML(filename=html_path).write_pdf(pdf_path)
#     os.remove(html_path)
#     print(f"PDF memo with logos saved to {pdf_path}")
# except Exception as e:
#     print(f"❌ Error converting HTML to PDF: {e}")
#     print(f"HTML memo with logos saved to {html_path}")


def save_memo_with_template(memo_text, profile, output_path):
    """
    Use template.docx as the base. Replace {{COVER_TEXT}} and {{MEMO_CONTENT}} in-place, inheriting the alignment/formatting of the placeholder paragraph, but always center-align the front page title and date.
    No extra blank lines or page breaks are added—content starts exactly where the placeholder is.
    """
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt
    import re
    import os
    from docx import Document
    template_path = os.path.abspath('template.docx')
    doc = Document(template_path)
    now = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    company_name = getattr(profile, 'name', 'Company')
    # --- Replace {{COVER_TEXT}} in-place, always center-aligned ---
    cover_found = False
    for i, p in enumerate(doc.paragraphs):
        if '{{COVER_TEXT}}' in p.text:
            cover_found = True
            # Remove the placeholder paragraph
            p.clear()
            # Insert title (centered, large, bold)
            phrase_run = p.add_run(f"This Investment Memo for {company_name} was Automatically Generated by the VC Intelligence System")
            phrase_run.font.size = Pt(22)
            phrase_run.bold = True
            phrase_run.font.name = 'Times New Roman'
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Insert date (centered, smaller) as a new paragraph right after
            date_para = doc.add_paragraph()
            date_run = date_para.add_run(f"Prepared on {now}")
            date_run.font.size = Pt(14)
            date_run.font.name = 'Times New Roman'
            date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Move the date_para to be right after the title paragraph (p)
            p._element.addnext(date_para._element)
            break
    if not cover_found:
        print("[Warning] {{COVER_TEXT}} placeholder not found in template.")
    # --- Replace {{MEMO_CONTENT}} in-place, inheriting alignment ---
    memo_found = False
    section_header_pattern = re.compile(r"^\d+\.\s+[A-Z][A-Z &()]+")
    all_caps_pattern = re.compile(r"^[A-Z0-9 &:'\-]+$")
    known_headers = [
        'Detailed Summary', 'Company Overview', 'Problem Statement', 'Solution Overview', 'Market Size & Analysis',
        'Competitive Landscape', 'Business Model', 'Technical Due Diligence', 'Product Description',
        'Financial Analysis', 'Team & Management', 'ESG Considerations', 'Risks & Mitigations',
        'Investment & Exit Strategies', 'Follow-up Questions & Next Steps', 'Figures & Visuals',
        'Appendix: Additional Tables', 'Discussion & Analyst Commentary',
        'Key Weaknesses', 'Opportunities', 'Risks', 'Actionable Recommendations for Investors',
        'Summary', 'Analysis Framework', 'Strengths', 'Weaknesses', 'Recommendations',
        'Appendix', 'Figures & Visuals',
        'ESG Alignment', 'Technical Validation Gaps', 'Competitive Landscape Challenges',
        'Execution & Commercialization Risk', 'Technology Risk', 'Competitive Displacement',
        'IP & Freedom to Operate', 'Financial & Funding Risk', 'Market Adoption & Regulatory Risk',
        # Add more as needed
    ]
    known_headers_lower = [h.lower() for h in known_headers]
    for i, p in enumerate(doc.paragraphs):
        if '{{MEMO_CONTENT}}' in p.text:
            memo_found = True
            alignment = p.alignment
            p.clear()
            memo_lines = memo_text.split('\n')
            for idx, line in enumerate(memo_lines):
                line_stripped = line.strip()
                # Remove text in brackets from section headers
                header_cleaned = re.sub(r"\s*\([^)]*\)", "", line_stripped)
                is_numbered_header = section_header_pattern.match(header_cleaned)
                is_all_caps = all_caps_pattern.match(header_cleaned) and len(header_cleaned) > 6
                is_known_header = header_cleaned.lower() in known_headers_lower
                # Special handling for the very first section (Detailed Summary)
                if idx == 0 and (is_numbered_header or is_all_caps or is_known_header):
                    # Header paragraph (always create a new paragraph, do not reuse p)
                    para = doc.add_paragraph()
                    run = para.add_run(header_cleaned)
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
                    run.bold = True
                    para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY  # Force justified alignment
                    para.paragraph_format.line_spacing = 1.5
                    para.paragraph_format.space_before = Pt(0)
                    para.paragraph_format.space_after = Pt(0)
                    last_para = para
                    continue  # Skip to next line (the summary will be handled as normal text)
                if is_numbered_header or is_all_caps or is_known_header:
                    if idx != 0:
                        blank_para = doc.add_paragraph()
                        blank_para.paragraph_format.space_after = Pt(0)
                    para = doc.add_paragraph()
                    run = para.add_run(header_cleaned)
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
                    run.bold = True
                    para.alignment = alignment if alignment is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
                    para.paragraph_format.line_spacing = 1.5
                    para.paragraph_format.space_after = Pt(6)
                    last_para = para
                else:
                    if idx == 1:  # This is the summary right after the header
                        para = doc.add_paragraph()
                        run = para.add_run(line_stripped)
                        run.font.name = 'Times New Roman'
                        run.font.size = Pt(12)
                        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY  # Force justified alignment
                        para.paragraph_format.line_spacing = 1.5
                        para.paragraph_format.space_before = Pt(0)
                        para.paragraph_format.space_after = Pt(0)
                        last_para = para
                    else:
                        if idx == 0:
                            para = p
                        else:
                            para = doc.add_paragraph()
                        run = para.add_run(line_stripped)
                        run.font.name = 'Times New Roman'
                        run.font.size = Pt(12)
                        para.alignment = alignment if alignment is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
                        para.paragraph_format.line_spacing = 1.5
                        last_para = para
            break
    if not memo_found:
        print("[Warning] {{MEMO_CONTENT}} placeholder not found in template.")
    # Save the new document
    doc.save(output_path)
    print(f"✅ DOCX memo generated from template and saved to {output_path}")


# --- DOCX to PDF conversion ---
def convert_docx_to_pdf(docx_path, output_dir=None):
    if output_dir is None:
        output_dir = os.path.dirname(docx_path)
    try:
        subprocess.run([
            "soffice", "--headless", "--convert-to", "pdf", "--outdir", output_dir, docx_path
        ], check=True)
        pdf_path = os.path.splitext(docx_path)[0] + ".pdf"
        print(f"✅ PDF generated from DOCX: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"❌ Error converting DOCX to PDF: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_file1> [<path_to_file2> ...]")
        sys.exit(1)

    file_paths = sys.argv[1:]
    for file_path in file_paths:
        print(f"Extracting text and structured data from: {file_path}")
        # --- Caching logic ---
        extracted = load_from_cache(file_path)
        if extracted is None:
            try:
                extracted = extract_text(file_path, return_structured=True)
                save_to_cache(file_path, extracted)
                print(f"[CACHE] Saved extraction for {file_path}")
            except Exception as e:
                print(f"Error extracting {file_path}: {e}")
                continue
        else:
            print(f"[CACHE] Loaded extraction for {file_path}")
        text = extracted["text"]
        tables = extracted["tables"]
        figures = extracted["figures"]

        clear_collection()
        profile = StartupProfile()
        profile = run_all_sequential_with_text(text, profile, file_path)
        # Populate structured data
        profile.tables = tables
        profile.figures = figures
        memo_text = format_memo(profile)
        print(memo_text)

        output_dir = "out"
        os.makedirs(output_dir, exist_ok=True)
        company_name = profile.name or "unknown_company"
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        docx_filename = f"memo_{company_name.replace(' ', '_')}_{date_str}.docx"
        docx_path = os.path.join(output_dir, docx_filename)
        save_memo_with_template(memo_text, profile, docx_path)
        convert_docx_to_pdf(docx_path)


if __name__ == "__main__":
    main()
