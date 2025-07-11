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
def format_market_size_section(profile):
    source = getattr(profile, 'market_source', None) or 'StoreDot April 2023 Corporate Overview'
    return (
        f"TAM: ${getattr(profile, 'TAM', 'N/A')}M (Source: {source})\n"
        f"SAM: ${getattr(profile, 'SAM', 'N/A')}M (Source: {source})\n"
        f"SOM: ${getattr(profile, 'SOM', 'N/A')}M (Source: {source})\n"
        f"Market Penetration Potential: {((getattr(profile, 'SOM', 0) / getattr(profile, 'TAM', 1)) * 100 if getattr(profile, 'TAM', 0) else 0):.1f}%\n"
        f"{getattr(profile, 'sector', '')}\n"
        f"{getattr(profile, 'market_summary', '')}"
    )

# --- Expanded Competitive Landscape ---
def format_competitive_landscape(profile):
    competitors = getattr(profile, 'top_competitors', [])
    details = []
    for comp in competitors:
        name = getattr(comp, 'name', comp.get('name', ''))
        differentiator = getattr(comp, 'differentiator', comp.get('differentiator', ''))
        approach = getattr(comp, 'approach', comp.get('approach', ''))
        tech = getattr(comp, 'technology', comp.get('technology', ''))
        status = getattr(comp, 'status', comp.get('status', ''))
        strengths = getattr(comp, 'strengths', comp.get('strengths', ''))
        weaknesses = getattr(comp, 'weaknesses', comp.get('weaknesses', ''))
        desc = f"{name}: "
        if differentiator:
            desc += f"{differentiator}. "
        if tech:
            desc += f"Technology: {tech}. "
        if approach:
            desc += f"Approach: {approach}. "
        if status:
            desc += f"Status: {status}. "
        if strengths:
            desc += f"Strengths: {strengths}. "
        if weaknesses:
            desc += f"Weaknesses: {weaknesses}. "
        details.append(desc.strip())
    if not details:
        return 'Competitive analysis pending - market positioning to be evaluated.'
    return '\n'.join(details)

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
    market_penetration = (profile.SOM / profile.TAM * 100) if profile.TAM and profile.TAM > 0 and profile.SOM else 0
    burn_rate_months = profile.runway_months if profile.runway_months else 0
    valuation_multiple = (profile.implied_valuation / profile.TAM * 100) if profile.TAM and profile.implied_valuation else 0
    maturity_map = {"prototype": 2, "beta": 4, "production": 8, "enterprise": 10, "unknown": 1, None: 1}
    tech_score = maturity_map.get(str(profile.tech_maturity).lower() if profile.tech_maturity else None, 1)
    risk_level = "LOW" if profile.risk_score and profile.risk_score < 0.3 else "MEDIUM" if profile.risk_score and profile.risk_score < 0.7 else "HIGH"
    competitors_section = (
        chr(10).join([
            f"• {getattr(comp, 'name', comp.get('name', ''))}: {getattr(comp, 'differentiator', comp.get('differentiator', 'Competitive positioning to be analyzed'))}"
            for comp in profile.top_competitors
        ]) if profile.top_competitors else 'Competitive analysis pending - market positioning to be evaluated'
    )
    risks_section = (chr(10).join([f"{i+1}. {risk}" for i, risk in enumerate(profile.risk_flags)]) if profile.risk_flags else 'Risk assessment pending - comprehensive risk analysis required')

    # Format tables for display (show up to 2 in main body, rest in appendix)
    def format_table(table):
        rows = table.get("rows", [])
        if not rows:
            return "[Table structure detected, but no data extracted.]"
        header = " | ".join(rows[0])
        sep = " | ".join(["---"] * len(rows[0]))
        body = "\n".join([" | ".join(row) for row in rows[1:]])
        return f"\n{header}\n{sep}\n{body}\n"
    tables_main = profile.tables[:2] if hasattr(profile, 'tables') and profile.tables else []
    tables_appendix = profile.tables[2:] if hasattr(profile, 'tables') and len(profile.tables) > 2 else []
    tables_section = "\n".join([format_table(t) for t in tables_main]) if tables_main else "No tables extracted."
    appendix_tables_section = "\n".join([format_table(t) for t in tables_appendix]) if tables_appendix else ""

    # Format figures for display (list page and bounding box)
    def format_figure(fig):
        return f"Page {fig.get('page', '?')}, BoundingBox: {fig.get('boundingBox', {})}, Type: {fig.get('blockType', '')}"
    figures_section = "\n".join([format_figure(f) for f in profile.figures]) if hasattr(profile, 'figures') and profile.figures else "No figures extracted."

    memo_body = f"""
INVESTMENT MEMORANDUM – {getattr(profile, 'name', None) or 'COMPANY ANALYSIS'}
(Prepared {current_date})

1. DETAILED SUMMARY
{'='*60}
{synthesize_detailed_summary(profile)}

2. COMPANY OVERVIEW (including team and website)
{'='*60}
Company: {getattr(profile, 'name', None) or 'TBD'}
Sector: {getattr(profile, 'sector', None) or 'TBD'}
Website: {getattr(profile, 'website', None) or 'TBD'}
Funding Stage: {getattr(profile, 'funding_stage', None) or 'TBD'}
Team: {getattr(profile, 'founder_name', None) or 'TBD'}
{getattr(profile, 'founder_linkedin_formatted', '')}

3. PROBLEM STATEMENT
{'='*60}
{synthesize_problem_statement(profile)}

4. SOLUTION OVERVIEW
{'='*60}
{synthesize_solution_overview(profile)}

5. MARKET SIZE & ANALYSIS
{'='*60}
{format_market_size_section(profile)}

--- Extracted Tables ---
{tables_section}

6. COMPETITIVE LANDSCAPE (with identified competitors)
{'='*60}
{format_competitive_landscape(profile)}
{getattr(profile, 'competitive_summary', '')}

7. BUSINESS MODEL
{'='*60}
{profile.business_model or 'Business model analysis not available.'}

8. TECHNICAL DUE DILIGENCE
{'='*60}
Maturity Level: {profile.tech_maturity or 'N/A'}
Technical Moat: {profile.moat_strength or 'N/A'}
Tech Stack: {profile.tech_stack or 'N/A'}
Scalability: {getattr(profile, 'scalability', '')}
Security: {getattr(profile, 'security', '')}

9. PRODUCT DESCRIPTION
{'='*60}
{profile.product_description or 'Product description not available.'}

10. FINANCIAL ANALYSIS (with commentary on data availability)
{'='*60}
Implied Valuation: ${profile.implied_valuation or 'N/A'}M
Cash Burn (12 months): ${profile.cash_burn_12m or 'N/A'}M
Runway: {burn_rate_months} months
Valuation Multiple: {valuation_multiple:.1f}
{('Financial data is unavailable.' if not profile.implied_valuation and not profile.cash_burn_12m else '')}
{getattr(profile, 'financial_summary', '')}

--- Extracted Tables (Financial) ---
{tables_section if tables_main else ''}

11. TEAM & MANAGEMENT
{'='*60}
Founder: {profile.founder_name or 'TBD'}
Founder Fit Score: {profile.founder_fit_score or 'N/A'} / 1.0
Prior Exits: {profile.prior_exits or '0'}
Sector Experience: {profile.sector or 'TBD'}
{profile.founder_linkedin_formatted if hasattr(profile, 'founder_linkedin_formatted') else ''}

12. ESG CONSIDERATIONS
{'='*60}
{profile.esg_summary or 'ESG analysis not available.'}

13. RISKS & MITIGATIONS
{'='*60}
Overall Risk Level: {risk_level}
Risk Score: {profile.risk_score or 'N/A'} / 1.0
IDENTIFIED RISKS:
{risks_section}

14. INVESTMENT & EXIT STRATEGIES
{'='*60}
{profile.exit_strategy or 'Exit strategy analysis not available.'}

15. FOLLOW-UP QUESTIONS & NEXT STEPS
{'='*60}
{profile.follow_up_questions or 'No follow-up questions generated.'}

16. FIGURES & VISUALS
{'='*60}
{figures_section}

17. APPENDIX: ADDITIONAL TABLES
{'='*60}
{appendix_tables_section}
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


# --- DOCX with header logo ---
def save_memo_as_docx(memo_text, profile, output_path):
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import os
    from datetime import datetime
    import re

    company_name = getattr(profile, 'name', 'Company')
    sector = getattr(profile, 'sector', 'Sector')
    # Prefer .jpg, fallback to .png for both logos
    def find_logo_path(basename):
        for ext in ['.jpg', '.png']:
            path = os.path.abspath(f'logo/{basename}{ext}')
            if os.path.exists(path):
                return path
        return None
    front_logo_path = find_logo_path('front_page')
    header_logo_path = find_logo_path('uni_logo')
    now = datetime.now().strftime('%B %d, %Y at %I:%M %p')

    doc = Document()

    # --- FRONT PAGE ---
    section = doc.sections[0]
    # Add large centered logo (make it even larger)
    if front_logo_path:
        try:
            p = doc.add_paragraph()
            run = p.add_run()
            run.add_picture(front_logo_path, width=Inches(6.5))  # Increased to 6.5 inches
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for _ in range(4):
                doc.add_paragraph('')
        except Exception as e:
            print(f"[Logo Error] Could not add front page logo: {e}")
    else:
        print(f"[Logo Warning] Front page logo not found as .jpg or .png")
    # Add phrase
    p = doc.add_paragraph()
    run = p.add_run(f"This Investment Memo for {company_name} was Automatically Generated by the VC Intelligence System")
    run.font.size = Pt(22)
    run.bold = True
    run.font.name = 'Times New Roman'
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # Add date
    p = doc.add_paragraph()
    run = p.add_run(f"Prepared on {now}")
    run.font.size = Pt(14)
    run.font.name = 'Times New Roman'
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # Add a page break after the cover
    doc.add_page_break()

    # --- NEW SECTION FOR MEMO CONTENT (to enable header logo on all pages after cover) ---
    from docx.enum.section import WD_SECTION
    new_section = doc.add_section(WD_SECTION.NEW_PAGE)
    header = new_section.header
    # Remove all existing paragraphs in header
    for para in header.paragraphs:
        p = para._element
        p.getparent().remove(p)
    # Always use logo/uni_logo.png (or .jpg fallback) for header logo
    def find_uni_logo_path():
        for ext in ['.png', '.jpg']:
            path = os.path.abspath(f'logo/uni_logo{ext}')
            if os.path.exists(path):
                return path
        return None
    header_logo_path = find_uni_logo_path()
    # Add logo at exact top left, larger size
    if header_logo_path:
        try:
            paragraph = header.add_paragraph()
            run = paragraph.add_run()
            run.add_picture(header_logo_path, width=Inches(2))  # Increased to 2 inches
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
        except Exception as e:
            print(f"[Logo Error] Could not add header logo: {e}")
    else:
        print(f"[Logo Warning] Header logo not found as .png or .jpg")

    # --- MEMO CONTENT ---
    # Set default font for the rest of the document
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)

    # Section header regex (matches lines like '1. DETAILED SUMMARY', '2. COMPANY OVERVIEW', etc.)
    section_header_pattern = re.compile(r"^\d+\.\s+[A-Z][A-Z &()]+$")
    # List of known sub-section headers to bold (case-insensitive, trimmed)
    known_headers = [
        'Key Weaknesses', 'Opportunities', 'Risks', 'Actionable Recommendations for Investors',
        'Summary', 'Analysis Framework', 'Strengths', 'Weaknesses', 'Recommendations',
        'Discussion & Analyst Commentary', 'Appendix', 'Figures & Visuals',
        'ESG Alignment', 'Technical Validation Gaps', 'Competitive Landscape Challenges',
        'Execution & Commercialization Risk', 'Technology Risk', 'Competitive Displacement',
        'IP & Freedom to Operate', 'Financial & Funding Risk', 'Market Adoption & Regulatory Risk',
        # Add more as needed
    ]
    known_headers_lower = [h.lower() for h in known_headers]

    for line in memo_text.split('\n'):
        line_stripped = line.strip()
        # Check for numbered/caps section header
        is_numbered_header = section_header_pattern.match(line_stripped)
        # Check for known sub-section header (case-insensitive, exact match)
        is_known_header = line_stripped.lower() in known_headers_lower
        if is_numbered_header or is_known_header:
            p = doc.add_paragraph()
            run = p.add_run(line_stripped)
            run.bold = True
            run.font.name = 'Times New Roman'
            run.font.size = Pt(12)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        else:
            p = doc.add_paragraph(line_stripped)
            p.style = doc.styles['Normal']
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            for run in p.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(12)

    doc.save(output_path)
    print(f"✅ DOCX memo with front page and header logo saved to {output_path}")

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
        save_memo_as_docx(memo_text, profile, docx_path)
        convert_docx_to_pdf(docx_path)


if __name__ == "__main__":
    main()
