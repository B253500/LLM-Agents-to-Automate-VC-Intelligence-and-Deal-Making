# Loading environment variables first
from dotenv import load_dotenv
load_dotenv()

# Suppress SWIG deprecation warnings
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module=".*swig.*")

# Standard library imports
import sys
import os
import json
import time
import re
import subprocess
from datetime import datetime
from pathlib import Path

# Third-party imports
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.shared import OxmlElement, qn
from fpdf import FPDF
import requests

# Local application imports
from core.download_utils import extract_text, get_cache_path, load_from_cache, save_to_cache, extract_market_size_from_text, update_market_value, log_market_size_changes
from core.utils import merge_outputs, synthesize_product_description
from core.orchestration import run_all_sequential_with_text
from core.schemas import StartupProfile
from core.vector_store import clear_collection

from core.visual_utils import extract_images_from_pdf, generate_sample_market_chart, extract_market_and_financials_from_visuals
from core.coresignal_utils import get_full_company_data

# Chain imports
from chains.pitch_deck_chain import run_pitch_deck_chain
from chains.technical_dd_chain import run_technical_dd_chain
from chains.market_sizing_chain import run_market_sizing_chain
from chains.financial_analysis_chain import run_financial_analysis_chain
from chains.competitive_intel_chain import run_competitive_intel_chain
from chains.risk_assessment_chain import run_risk_assessment_chain
from chains.product_description_chain import run_product_description_chain
from chains.memo_synthesis_chain import (
    run_detailed_summary_chain,
    run_problem_statement_chain,
    run_solution_overview_chain,
    run_business_model_chain,
    run_risks_section_chain,
    run_team_section_chain,
    run_esg_section_chain,
    run_analyst_commentary_chain,
    run_exit_strategies_chain,
    run_followup_section_chain
)

# Agent imports
from agents.technical_dd_agent import build_technical_dd_agent, format_technical_dd_section
from agents.market_sizing_agent import build_market_sizing_agent, generate_market_size_section, format_market_size
from agents.competitive_intel_agent import build_competitive_intel_agent, generate_competitive_landscape
from agents.founder_profiling_agent import build_founder_profiling_agent, enrich_executive_details_with_perplexity, generate_team_section
from agents.financial_analysis_agent import build_financial_analysis_agent
from agents.risk_assessment_agent import build_risk_assessment_agent, generate_discussion_section, generate_counterfactual_section
from agents.deck_agent import build_deck_agent

CACHE_DIR = "extraction_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def add_hyperlink(paragraph, text, url):
    """Add a hyperlink to a paragraph with blue color and underline."""
    # Create a proper hyperlink using the document's hyperlink collection
    try:
        # Get the document
        doc = paragraph._element.getparent().getparent()
        if hasattr(doc, 'part'):
            doc = doc.part
        
        # Add the hyperlink relationship
        if hasattr(doc, 'rels'):
            r_id = doc.rels.add_hyperlink(url, url)
            
            # Create the hyperlink element
            hyperlink = OxmlElement('w:hyperlink')
            hyperlink.set(qn('r:id'), r_id)
            
            # Create the run element
            new_run = OxmlElement('w:r')
            rPr = OxmlElement('w:rPr')
            
            # Add blue color
            color = OxmlElement('w:color')
            color.set(qn('w:val'), '0563C1')  # Blue color
            rPr.append(color)
            
            # Add underline
            underline = OxmlElement('w:u')
            underline.set(qn('w:val'), 'single')
            rPr.append(underline)
            
            # Add the text
            text_element = OxmlElement('w:t')
            text_element.text = text
            new_run.append(rPr)
            new_run.append(text_element)
            hyperlink.append(new_run)
            
            # Add to paragraph
            paragraph._element.append(hyperlink)
        else:
            # Fallback: add as blue underlined text
            run = paragraph.add_run(text)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(12)
            run.font.color.rgb = RGBColor(5, 99, 193)  # Blue color
            run.font.underline = True
    except Exception as e:
        # Fallback: add as blue underlined text
        run = paragraph.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(5, 99, 193)  # Blue color
        run.font.underline = True


def process_text_with_hyperlinks(paragraph, text):
    """Process text and convert markdown links to DOCX hyperlinks."""
    import re
    
    # Pattern to match markdown links: [text](url)
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    
    # Find all links in the text
    links = list(re.finditer(link_pattern, text))
    
    if not links:
        # No links found, just add the text normally
        run = paragraph.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        return
    
    # Process text with links
    last_end = 0
    for match in links:
        link_text = match.group(1)
        link_url = match.group(2)
        
        # Add text before the link
        if match.start() > last_end:
            before_text = text[last_end:match.start()]
            if before_text.strip():
                run = paragraph.add_run(before_text)
                run.font.name = 'Times New Roman'
                run.font.size = Pt(12)
        
        # Add the hyperlink
        add_hyperlink(paragraph, link_text, link_url)
        
        last_end = match.end()
    
    # Add any remaining text after the last link
    if last_end < len(text):
        remaining_text = text[last_end:]
        if remaining_text.strip():
            run = paragraph.add_run(remaining_text)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(12)


def run_pitch_deck_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    from chains.pitch_deck_chain import run_pitch_deck_chain_with_text as run_pitch_chain
    return run_pitch_chain(full_text, profile)


def run_technical_dd_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_technical_dd_chain(profile)


def run_founder_profiling_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    from agents.founder_profiling_agent import run_founder_profiling_chain_with_text as run_founder_chain
    return run_founder_chain(full_text, profile)


def run_market_sizing_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_market_sizing_chain(profile)


def run_financial_analysis_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_financial_analysis_chain(profile)


def run_competitive_intel_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_competitive_intel_chain(profile)


def run_risk_assessment_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_risk_assessment_chain(profile)


# --- Inline Source Attribution for Market Size & Analysis ---


def format_company_overview_section(profile):
    lines = []
    lines.append(f"Company: {getattr(profile, 'name', 'TBD')}")
    if getattr(profile, 'sector', None):
        lines.append(f"Sector: {profile.sector}")
    if getattr(profile, 'website', None):
        lines.append(f"Website: {profile.website}")
    if getattr(profile, 'status', None):
        lines.append(f"Status: {profile.status}")
    if getattr(profile, 'size_range', None):
        lines.append(f"Size: {profile.size_range}")
    elif getattr(profile, 'size', None):
        lines.append(f"Size: {profile.size}")
    if getattr(profile, 'founded_year', None):
        lines.append(f"Founded: {profile.founded_year}")
    elif getattr(profile, 'founded', None):
        lines.append(f"Founded: {profile.founded}")
    # HQ - check CoreSignal fields first, then fallback
    hq = getattr(profile, 'hq_city', None) or getattr(profile, 'headquarters_new_address', None) or getattr(profile, 'headquarters_city', None)
    if hq:
        lines.append(f"Headquarters: {hq}")
    hq_country = getattr(profile, 'hq_country_iso2', None) or getattr(profile, 'headquarters_country_restored', None)
    if hq_country:
        lines.append(f"Country: {hq_country}")
    if getattr(profile, 'linkedin', None):
        lines.append(f"LinkedIn: {profile.linkedin}")
    elif getattr(profile, 'canonical_url', None):
        lines.append(f"LinkedIn: {profile.canonical_url}")
    if getattr(profile, 'linkedin_followers', None):
        lines.append(f"LinkedIn Followers: {profile.linkedin_followers}")
    elif getattr(profile, 'followers', None):
        lines.append(f"Followers: {profile.followers}")
    if getattr(profile, 'employees_count', None):
        lines.append(f"Employees: {profile.employees_count}")
    if getattr(profile, 'website_traffic', None):
        lines.append(f"Website Traffic: {profile.website_traffic}")
    if getattr(profile, 'emails', None):
        lines.append(f"Company Emails: {profile.emails}")
    if getattr(profile, 'phones', None):
        lines.append(f"Company Phones: {profile.phones}")
    if getattr(profile, 'twitter', None):
        lines.append(f"Twitter: {profile.twitter}")
    if getattr(profile, 'facebook', None):
        lines.append(f"Facebook: {profile.facebook}")
    # Office locations - check CoreSignal field first, then fallback
    locs = getattr(profile, 'office_locations', None) or getattr(profile, 'company_locations_collection', None)
    if locs and isinstance(locs, list):
        # Use deduplication function to get unique locations
        from core.orchestration import deduplicate_office_locations
        unique_locs = deduplicate_office_locations(locs)
        
        loc_strs = []
        for loc in unique_locs:
            addr = loc.get('location_address') if isinstance(loc, dict) else str(loc)
            if addr and addr.strip():
                loc_strs.append(addr.strip())
        
        if loc_strs:
            # Show only the first (primary) location to avoid clutter
            primary_location = loc_strs[0]
            if len(loc_strs) > 1:
                lines.append(f"Office Location: {primary_location} (and {len(loc_strs)-1} other locations)")
            else:
                lines.append(f"Office Location: {primary_location}")
    # Funding Stage - Enhanced to show latest significant funding
    funding_stage = format_funding_stage(profile)
    
    # Try to get more detailed funding info from funding rounds
    latest_funding_info = ""
    if hasattr(profile, 'funding_rounds') and profile.funding_rounds:
        try:
            import json
            funding_rounds = json.loads(profile.funding_rounds) if isinstance(profile.funding_rounds, str) else profile.funding_rounds
            
            if funding_rounds and isinstance(funding_rounds, list):
                # Find the most recent significant funding round
                for round_data in funding_rounds:
                    if isinstance(round_data, dict):
                        round_type = round_data.get('last_round_type') or round_data.get('round_type')
                        round_amount = round_data.get('last_round_money_raised') or round_data.get('amount_usd')
                        round_date = round_data.get('last_round_date') or round_data.get('date')
                        
                        if round_type and round_amount and round_date:
                            # Format the date
                            try:
                                if isinstance(round_date, str) and len(round_date) == 8 and round_date.isdigit():
                                    # Format like "20180522" to "May 2018"
                                    from datetime import datetime
                                    date_obj = datetime.strptime(round_date, '%Y%m%d')
                                    formatted_date = date_obj.strftime('%B %Y')
                                elif isinstance(round_date, str) and '-' in round_date:
                                    # Format like "2018-05-22" to "May 2018"
                                    from datetime import datetime
                                    date_obj = datetime.strptime(round_date.split(' ')[0], '%Y-%m-%d')
                                    formatted_date = date_obj.strftime('%B %Y')
                                else:
                                    formatted_date = str(round_date)
                            except:
                                formatted_date = str(round_date)
                            
                            # Format the amount
                            try:
                                amount_float = float(round_amount)
                                if amount_float >= 1_000_000:
                                    formatted_amount = f"${amount_float/1_000_000:.1f}M"
                                elif amount_float >= 1_000:
                                    formatted_amount = f"${amount_float/1_000:.1f}K"
                                else:
                                    formatted_amount = f"${amount_float:.0f}"
                            except:
                                formatted_amount = str(round_amount)
                            
                            latest_funding_info = f" ({round_type} - {formatted_amount} - {formatted_date})"
                            break
        except Exception as e:
            print(f"[Company Overview] Error processing funding rounds: {e}")
    
    lines.append(f"Funding Stage: {funding_stage}{latest_funding_info}")
    # Team
    execs = getattr(profile, 'executives', []) or []
    if execs:
        team_str = "Team: " + ", ".join(
            f"{e.get('name', 'Unknown')} ({e.get('role', '')})" if isinstance(e, dict) else str(e)
            for e in execs[:3]
        )
        lines.append(team_str)
    return '\n'.join(lines)


def format_product_description_section(profile):
    # Gather all relevant fields
    desc = getattr(profile, 'product_description', None)
    specs = getattr(profile, 'product_specs', None)
    roadmap = getattr(profile, 'product_roadmap', None)
    unique = getattr(profile, 'unique_features', None)
    status = getattr(profile, 'status', None)
    cell_format = getattr(profile, 'cell_format', None)
    cycle_life = getattr(profile, 'cycle_life', None)
    energy_density = getattr(profile, 'energy_density', None)
    uniqueness = getattr(profile, 'uniqueness', None)
    diff = getattr(profile, 'difference_from_competitors', None)
    scalability = getattr(profile, 'scalability', None)
    sustainability = getattr(profile, 'sustainability', None)
    regulatory = getattr(profile, 'regulatory', None)
    testing = getattr(profile, 'testing', None)
    security = getattr(profile, 'security', None)

    # Synthesize a narrative lead sentence
    lead = None
    if desc and len(desc.split()) > 6:
        lead = desc
    else:
        # Try to synthesize a narrative
        parts = []
        if cell_format or status:
            parts.append(f"The core product is a {cell_format or ''} {status or ''} battery".strip() + ".")
        if unique:
            parts.append(f"It features {unique}.")
        if specs:
            parts.append(f"Key specs: {specs}.")
        if cycle_life or energy_density:
            ce = []
            if cycle_life:
                ce.append(f"cycle life of {cycle_life}")
            if energy_density:
                ce.append(f"energy density of {energy_density}")
            if ce:
                parts.append("It offers " + " and ".join(ce) + ".")
        if roadmap:
            parts.append(f"Product roadmap: {roadmap}.")
        if uniqueness:
            parts.append(f"What makes it unique: {uniqueness}.")
        if diff:
            parts.append(f"Compared to competitors: {diff}.")
        if scalability:
            parts.append(f"Scalability: {scalability}.")
        if sustainability:
            parts.append(f"Sustainability: {sustainability}.")
        if regulatory:
            parts.append(f"Regulatory: {regulatory}.")
        if testing:
            parts.append(f"Testing: {testing}.")
        if security:
            parts.append(f"Security: {security}.")
        # Compose a paragraph
        lead = ' '.join(parts)
    if not lead or len(lead.strip()) < 20:
        # Fallback: concatenate all fields if no narrative possible
        all_fields = [desc, specs, roadmap, unique, status, cell_format, cycle_life, energy_density, uniqueness, diff, scalability, sustainability, regulatory, testing, security]
        all_fields = [str(f) for f in all_fields if f]
        if all_fields:
            lead = ' '.join(all_fields)
        else:
            return 'Product description not available.'
    return lead.strip()

def format_funding_stage(profile):
    funding_stage = getattr(profile, 'funding_stage', None) or 'Undisclosed'
    # Try to pull from PitchBook if available
    pitchbook_round = getattr(profile, 'pitchbook_last_round', None)
    pitchbook_year = getattr(profile, 'pitchbook_last_year', None)
    if funding_stage.lower() in ['unknown', 'n/a', '']:
        if pitchbook_round and pitchbook_year:
            funding_stage = f"{pitchbook_round} ({pitchbook_year})"
        else:
            last_round = getattr(profile, 'last_funding_round', None)
            last_round_year = getattr(profile, 'last_funding_year', None)
            if last_round and last_round_year:
                funding_stage = f"Undisclosed (last round: {last_round} - {last_round_year})"
            else:
                funding_stage = "Undisclosed (no public data found)"
    return funding_stage

def format_financials_section(profile, current_date):
    # Collect all financial metrics
    metrics = [
        ("Revenue", getattr(profile, 'revenue', None)),
        ("Projected Revenue", getattr(profile, 'projected_revenue', None)),
        ("Cash Burn (12m)", getattr(profile, 'cash_burn_12m', None)),
        ("Runway (months)", getattr(profile, 'runway_months', None)),
        ("Implied Valuation", getattr(profile, 'implied_valuation', None)),
        ("Gross Margin", getattr(profile, 'gross_margin', None)),
        ("EBITDA", getattr(profile, 'ebitda', None)),
        ("Net Income", getattr(profile, 'net_income', None)),
        ("ARR", getattr(profile, 'arr', None)),
        ("MRR", getattr(profile, 'mrr', None)),
        ("CAC", getattr(profile, 'cac', None)),
        ("LTV", getattr(profile, 'ltv', None)),
        ("Payback Period", getattr(profile, 'payback_period', None)),
        ("Revenue Growth Rate", getattr(profile, 'revenue_growth_rate', None)),
        ("Debt", getattr(profile, 'debt', None)),
        ("Cash on Hand", getattr(profile, 'cash_on_hand', None)),
        ("Estimated Revenue", getattr(profile, 'estimated_revenue_range', None)),
        ("Revenue Currency", getattr(profile, 'revenue_currency', None)),
        ("Revenue Source", getattr(profile, 'revenue_source', None)),
        ("Last Funding Round", getattr(profile, 'last_funding_round_name', None)),
        ("Last Round Amount", getattr(profile, 'last_funding_round_amount_raised', None)),
        ("Last Round Date", getattr(profile, 'last_funding_round_announced_date', None)),
    ]
    
    # Check for Crunchbase-sourced valuation data
    crunchbase_valuation = None
    web_sources = []
    
    if hasattr(profile, 'funding_rounds') and profile.funding_rounds:
        try:
            import json
            funding_rounds = json.loads(profile.funding_rounds) if isinstance(profile.funding_rounds, str) else profile.funding_rounds
            
            # Look for the most recent significant funding round
            for round_data in funding_rounds:
                if isinstance(round_data, dict) and round_data.get('last_round_money_raised'):
                    crunchbase_valuation = {
                        'amount': round_data.get('last_round_money_raised'),
                        'type': round_data.get('last_round_type'),
                        'date': round_data.get('last_round_date'),
                        'url': round_data.get('cb_url')
                    }
                    break
        except Exception as e:
            print(f"[Financial Formatting] Error processing funding rounds: {e}")
    
    # Check for web search sources from financial analysis chain
    if hasattr(profile, 'web_sources') and profile.web_sources:
        web_sources = profile.web_sources[:5]  # Use up to 5 sources from financial analysis
    elif hasattr(profile, 'financial_summary') and profile.financial_summary:
        import re
        # Extract URLs from financial summary as fallback
        urls = re.findall(r'https?://[^\s]+', profile.financial_summary)
        web_sources = urls[:3]  # Limit to first 3 sources
    else:
        web_sources = []
    # Cap Table/Investors
    major_investors = getattr(profile, 'major_investors', None)
    ownership_breakdown = getattr(profile, 'ownership_breakdown', None)
    # Only count as 'present' if not None and not empty string
    present_metrics = [v for _, v in metrics if v not in [None, '']]
    if len(present_metrics) < 3 and not (major_investors or ownership_breakdown):
        return f"Company has not released financials as of {current_date}. No detailed financials were disclosed in the deck or public sources. We recommend requesting a financial summary from the company, including revenue, burn rate, runway, and recent funding rounds. Independent verification of financials is advised before proceeding."
    # Table header
    lines = ["| Metric | Value |", "|--------|-------|"]
    
    # Add Crunchbase-sourced funding data prominently if available
    if crunchbase_valuation:
        lines.append(f"| **Latest Funding Round** | **{crunchbase_valuation['type']}** |")
        lines.append(f"| **Funding Amount** | **{crunchbase_valuation['amount']}** |")
        lines.append(f"| **Funding Date** | **{crunchbase_valuation['date']}** |")
        if crunchbase_valuation['url']:
            lines.append(f"| **Source** | **[Crunchbase]({crunchbase_valuation['url']})** |")
        lines.append("| **---** | **---** |")  # Separator
    
    # Add web-sourced financial data if available
    if hasattr(profile, 'financial_summary') and profile.financial_summary and 'Web Search Results' in profile.financial_summary:
        lines.append("| **Web-Sourced Financial Data** | **External Research** |")
        # Extract key financial information from web search results
        web_summary = profile.financial_summary
        if 'valuation' in web_summary.lower():
            lines.append("| **Valuation Data** | **Available from web sources** |")
        if 'funding' in web_summary.lower():
            lines.append("| **Funding History** | **Available from web sources** |")
        if 'revenue' in web_summary.lower():
            lines.append("| **Revenue Data** | **Available from web sources** |")
        lines.append("| **---** | **---** |")  # Separator
    
    for label, value in metrics:
        if value is not None and value != '':
            lines.append(f"| {label} | {value} |")
    
    # Cap Table/Investors
    if major_investors:
        lines.append(f"| Major Investors | {', '.join(major_investors)} |")
    if ownership_breakdown:
        for owner in ownership_breakdown:
            name = owner.get('name', 'Unknown')
            percent = owner.get('percent', '')
            lines.append(f"| Ownership: {name} | {percent} |")
    
    # Add web sources if available
    if web_sources:
        lines.append("| **---** | **---** |")  # Separator
        lines.append("| **Data Sources** | **Web Research** |")
        for i, source in enumerate(web_sources, 1):
            # Extract domain name for better display
            try:
                from urllib.parse import urlparse
                domain = urlparse(source).netloc
                if domain.startswith('www.'):
                    domain = domain[4:]
                source_name = domain.replace('.com', '').replace('.co', '').title()
            except:
                source_name = f"Source {i}"
            
            lines.append(f"| {source_name} | [{source}]({source}) |")
    
    return '\n'.join(lines)

def format_risk_score(profile):
    risk_score = getattr(profile, 'risk_score', None)
    if risk_score is not None and risk_score != 'N/A':
        return f"Risk Score: {risk_score}"
    else:
        return ""

# --- De-duplication Post-processing ---
def deduplicate_memo(text):
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
    
    # Apply additional cleaning to remove redundant elements
    result_text = '\n'.join(result)
    result_text = clean_blank_bullets(result_text)
    
    return result_text

def format_risk_section(profile):
    risk_flags = getattr(profile, 'risk_flags', [])
    regulatory = getattr(profile, 'regulatory', None)
    testing = getattr(profile, 'testing', None)
    security = getattr(profile, 'security', None)
    discussion = []
    # Enumerate and describe all risks
    if risk_flags:
        for rf in risk_flags:
            discussion.append(f"• {rf}")
    else:
        discussion.append("• Risks are present but not fully disclosed. Investors should request more information and conduct further diligence.")
    # Always include regulatory, testing, security
    discussion.append(f"• Regulatory: {regulatory or 'Compliance with evolving standards and certifications is required.'}")
    discussion.append(f"• Testing: {testing or 'Independent validation and certification are recommended.'}")
    discussion.append(f"• Security: {security or 'Product safety, data, and IP protection should be addressed.'}")
    return '\n'.join(discussion)

def format_financial_history_section(profile):
    lines = []
    rounds = getattr(profile, 'company_funding_rounds_collection', None) or getattr(profile, 'funding_rounds', None)
    
    if rounds and isinstance(rounds, list):
        lines.append("**Funding Rounds:**")
        lines.append("")
        
        # Clean and deduplicate rounds
        cleaned_rounds = []
        seen_rounds = set()
        
        for r in rounds:
            if isinstance(r, dict):
                round_type = r.get('last_round_type') or r.get('round_type', 'Unknown')
                date = r.get('last_round_date') or r.get('date', '')
                amount = r.get('last_round_money_raised') or r.get('amount_usd', '')
                investors = r.get('last_round_investors_count') or r.get('investors', '')
                
                # Clean up the data
                round_type = str(round_type).strip()
                date = str(date).strip()
                amount = str(amount).strip()
                investors = str(investors).strip()
                
                # Filter out unwanted round types
                unwanted_types = ['Series unknown', 'Non equity assistance', 'Unknown']
                if round_type in unwanted_types:
                    continue
                
                # Filter out corporate rounds without amounts and secondary market rounds
                if round_type == 'Corporate round' and (not amount or amount == 'None' or amount == ''):
                    continue
                if 'secondary' in round_type.lower():
                    continue
                
                # Format date properly - extract only the date part
                if date and date != 'None':
                    try:
                        # Handle different date formats
                        if ' ' in date:
                            # Remove time component and extract date
                            date_part = date.split(' ')[0]
                            if len(date_part) == 8 and date_part.isdigit():
                                # Format like "20180522" to "22 May 2018"
                                date_obj = datetime.strptime(date_part, '%Y%m%d')
                                formatted_date = date_obj.strftime('%d %B %Y')
                            elif len(date_part) == 10 and '-' in date_part:
                                # Format like "2018-05-22" to "22 May 2018"
                                date_obj = datetime.strptime(date_part, '%Y-%m-%d')
                                formatted_date = date_obj.strftime('%d %B %Y')
                            else:
                                formatted_date = date_part
                        else:
                            # Handle single date strings
                            if len(date) == 8 and date.isdigit():
                                # Format like "20180522" to "22 May 2018"
                                date_obj = datetime.strptime(date, '%Y%m%d')
                                formatted_date = date_obj.strftime('%d %B %Y')
                            elif len(date) == 10 and '-' in date:
                                # Format like "2018-05-22" to "22 May 2018"
                                date_obj = datetime.strptime(date, '%Y-%m-%d')
                                formatted_date = date_obj.strftime('%d %B %Y')
                            else:
                                formatted_date = date
                    except:
                        formatted_date = date
                else:
                    formatted_date = 'Date not specified'
                
                # Format amount properly
                if amount and amount != 'None':
                    try:
                        # Convert to float and format as currency
                        amount_float = float(amount)
                        if amount_float >= 1_000_000:
                            formatted_amount = f"${amount_float/1_000_000:.1f}M"
                        elif amount_float >= 1_000:
                            formatted_amount = f"${amount_float/1_000:.1f}K"
                        else:
                            formatted_amount = f"${amount_float:.0f}"
                    except:
                        formatted_amount = amount
                else:
                    # For secondary rounds, specify "Unknown amount" instead of "Amount not disclosed"
                    if 'secondary' in round_type.lower():
                        formatted_amount = 'Unknown amount'
                    else:
                        formatted_amount = 'Amount not disclosed'
                
                # Create unique identifier for deduplication (by type and date, not amount)
                round_key = f"{round_type}_{formatted_date}"
                
                # Check if we already have this round type and date
                existing_round = None
                for existing in cleaned_rounds:
                    if existing['type'] == round_type and existing['date'] == formatted_date:
                        existing_round = existing
                        break
                
                if existing_round:
                    # If we have a duplicate, keep the one with the larger amount
                    try:
                        current_amount = float(existing_round['amount'].replace('$', '').replace('M', '').replace('K', '').replace(',', ''))
                        new_amount = float(formatted_amount.replace('$', '').replace('M', '').replace('K', '').replace(',', ''))
                        if new_amount > current_amount:
                            # Replace with the larger amount
                            existing_round['amount'] = formatted_amount
                            existing_round['investors'] = investors
                    except:
                        # If we can't compare amounts, keep the existing one
                        pass
                else:
                    # New round type and date combination
                    cleaned_rounds.append({
                        'type': round_type,
                        'date': formatted_date,
                        'amount': formatted_amount,
                        'investors': investors
                    })
        
        # Sort rounds by date (most recent first)
        # Convert dates back to datetime for proper sorting
        def parse_date_for_sorting(date_str):
            try:
                if date_str == 'Date not specified':
                    return datetime.min
                # Try different date formats for sorting
                for fmt in ['%d %B %Y', '%B %Y', '%Y-%m-%d', '%Y%m%d']:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except:
                        continue
                return datetime.min
            except:
                return datetime.min
        
        cleaned_rounds.sort(key=lambda x: parse_date_for_sorting(x['date']), reverse=True)
        
        # Display cleaned rounds
        for r in cleaned_rounds[:10]:  # Limit to top 10 rounds
            parts = []
            parts.append(f"**{r['type']}**")
            parts.append(r['date'])
            if r['amount'] != 'Amount not disclosed':
                parts.append(r['amount'])
            if r['investors'] and r['investors'] != 'None':
                parts.append(f"({r['investors']} investors)")
            
            lines.append(f"• {', '.join(parts)}")
    
    # Add major investors section
    investors = getattr(profile, 'company_featured_investors_collection', None)
    if investors and isinstance(investors, list):
        lines.append("")
        lines.append("**Major Investors:**")
        lines.append("")
        
        seen_investors = set()
        for inv in investors:
            name = inv.get('name') if isinstance(inv, dict) else str(inv)
            url = inv.get('cb_url') if isinstance(inv, dict) else None
            
            if name and name not in seen_investors:
                seen_investors.add(name)
                # Keep the name as is (including any tokens)
                if name and name != 'None':
                    if url:
                        lines.append(f"• **{name}** ([Profile]({url}))")
                    else:
                        lines.append(f"• **{name}**")
    
    # Add acquisitions if available
    acquisitions = getattr(profile, 'acquisitions', None)
    if acquisitions and isinstance(acquisitions, list):
        lines.append("")
        lines.append("**Acquisitions:**")
        lines.append("")
        
        for acq in acquisitions:
            if isinstance(acq, dict):
                name = acq.get('name', 'Unknown')
                date = acq.get('date', '')
                amount = acq.get('amount', '')
                
                if name and name != 'Unknown':
                    parts = [f"**{name}**"]
                    if date:
                        parts.append(date)
                    if amount:
                        parts.append(amount)
                    lines.append(f"• {', '.join(parts)}")
            else:
                acq_str = str(acq).strip()
                if acq_str and acq_str != 'None':
                    lines.append(f"• **{acq_str}**")
    
    return '\n'.join(lines)



def format_followup_section(profile):
    fq = getattr(profile, 'follow_up_questions', None) or ''
    # Remove all '**' and leading '-' from every line
    lines = []
    for line in fq.split('\n'):
        clean_line = line.replace('**', '').strip()
        # Remove leading '-' and any whitespace after it
        if clean_line.startswith('-'):
            clean_line = clean_line[1:].lstrip()
        if clean_line.startswith('• -'):
            clean_line = clean_line[3:].lstrip()
        elif clean_line.startswith('•') and clean_line[1:2] in [' ', '-']:
            clean_line = '•' + clean_line[2:].lstrip('-').lstrip()
        # Header if ends with ':' after cleaning, or if it is a title-like line (contains & or is Title Case)
        is_header = False
        if clean_line.endswith(':'):
            is_header = True
        elif clean_line and (clean_line.istitle() or ('&' in clean_line and clean_line == clean_line.title())):
            is_header = True
        # Special case: if line started with '• -', treat as header if it looks like a section
        if line.strip().startswith('• -') and (':' not in clean_line and (clean_line.istitle() or '&' in clean_line)):
            is_header = True
        if is_header:
            lines.append(f"<HEADER>{clean_line.rstrip(':')}")
        elif clean_line:
            lines.append(f"• {clean_line}")
    return '\n'.join(lines) if lines else 'No follow-up questions generated.'

def clean_discussion_section(discussion):
    lines = discussion.split('\n')
    cleaned = []
    for line in lines:
        # Remove lines that are just a bullet or whitespace
        if line.strip() in ['•', '-', '*', '']:
            continue
        # Remove leading bullet from the first non-empty line
        if cleaned == [] and line.strip().startswith('•'):
            line = line.lstrip('•').strip()
        cleaned.append(line)
    
    # Remove redundant conclusion at the bottom
    result = '\n'.join(cleaned)
    
    # Remove the redundant "Conclusion:" line at the bottom
    result = re.sub(r'\n\s*Conclusion:\s*\n\s*Based on the analysis above, this investment opportunity presents both significant potential and notable risks that require careful consideration\.\s*$', '', result, flags=re.MULTILINE)
    
    # Remove trailing bullet points and redundant elements
    result = re.sub(r'\n\s*•\s*$', '', result, flags=re.MULTILINE)  # Remove trailing bullet point
    result = re.sub(r'\n\s*-\s*$', '', result, flags=re.MULTILINE)   # Remove trailing dash
    result = re.sub(r'\n\s*\*\s*$', '', result, flags=re.MULTILINE)  # Remove trailing asterisk
    
    # Remove multiple consecutive blank lines at the end
    result = re.sub(r'\n\s*\n\s*$', '\n', result, flags=re.MULTILINE)
    
    # Remove any trailing whitespace
    result = result.rstrip()
    
    return result

def clean_blank_bullets(text):
    lines = text.split('\n')
    cleaned = []
    for i, line in enumerate(lines):
        # Remove lines that are just a bullet or a bullet with whitespace
        if line.strip() in ['•', '-', '*']:
            # Also skip if the next line is blank or whitespace
            if i + 1 < len(lines) and not lines[i + 1].strip():
                continue
            # Or if it's the last line
            if i + 1 == len(lines):
                continue
            # Or if it's followed by another bullet point
            if i + 1 < len(lines) and lines[i + 1].strip() in ['•', '-', '*']:
                continue
        cleaned.append(line)
    
    # Remove trailing bullet points and redundant elements
    result = '\n'.join(cleaned)
    result = re.sub(r'\n\s*•\s*$', '', result, flags=re.MULTILINE)  # Remove trailing bullet point
    result = re.sub(r'\n\s*-\s*$', '', result, flags=re.MULTILINE)   # Remove trailing dash
    result = re.sub(r'\n\s*\*\s*$', '', result, flags=re.MULTILINE)  # Remove trailing asterisk
    
    # Remove multiple consecutive blank lines at the end
    result = re.sub(r'\n\s*\n\s*$', '\n', result, flags=re.MULTILINE)
    
    # Remove any trailing whitespace
    result = result.rstrip()
    
    return result



def format_memo(profile: StartupProfile) -> str:
    current_date = datetime.now().strftime("%B %d, %Y")
    def clean(text):
        """Clean up text by removing hashtags, special markers, and normalizing formatting."""
        if not isinstance(text, str):
            return text
        # Remove hashtags only
        text = re.sub(r'#+\s*[A-Za-z\s]+', '', text)
        # Remove extra whitespace and normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()
    # --- Team line for Company Overview ---
    execs = getattr(profile, 'executives', []) or []
    if execs:
        team_line = "Team: " + ", ".join(
            f"{e.get('name', 'Unknown')} ({e.get('role', '')})" for e in execs[:3]
        )
    else:
        team_line = f"Team: {getattr(profile, 'founder_name', 'TBD')}"

    # --- Funding line for Company Overview ---
    funding_line = f"Funding Stage: {getattr(profile, 'funding_stage', 'Undisclosed')}"
    if getattr(profile, 'funding_amount', None):
        funding_line += f", {profile.funding_amount}"
    if getattr(profile, 'funding_source', None):
        funding_line += f" [Source: {profile.funding_source}]"

    memo_body = f"""
1. DETAILED SUMMARY
{clean(run_detailed_summary_chain(profile))}

2. COMPANY OVERVIEW
{clean(format_company_overview_section(profile))}

3. PROBLEM STATEMENT
{clean(run_problem_statement_chain(profile))}
    
4. SOLUTION OVERVIEW
{clean(run_solution_overview_chain(profile))}
    
5. PRODUCT/SERVICE DESCRIPTION
{run_product_description_chain(profile)}
    
6. MARKET SIZE & ANALYSIS
{generate_market_size_section(profile)}
{clean(getattr(profile, 'sector', ''))}

7. COMPETITORS
{clean(generate_competitive_landscape(profile))}
{clean(getattr(profile, 'competitive_summary', ''))}

8. BUSINESS MODEL
{run_business_model_chain(profile)}

9. TECHNICAL DUE DILIGENCE
{clean(format_technical_dd_section(profile))}

10. FINANCIAL ANALYSIS
{format_financials_section(profile, current_date)}

{format_financial_history_section(profile)}

11. TEAM & MANAGEMENT
{clean(generate_team_section(profile))}

12. ESG CONSIDERATIONS
{run_esg_section_chain(profile)}

13. RISKS
{run_risks_section_chain(profile)}

14. INVESTMENT & EXIT STRATEGIES
{run_exit_strategies_chain(profile)}

15. COUNTERFACTUAL ANALYSIS: WHAT IF WE DON'T INVEST?
{generate_counterfactual_section(profile)}

16. FOLLOW-UP QUESTIONS & NEXT STEPS
{run_followup_section_chain(profile)}
"""
    discussion = generate_discussion_section(memo_body)
    return deduplicate_memo(f"{memo_body}\n17. AI DISCUSSION AND COMMENTARY\n{clean_discussion_section(discussion)}\n\n---\nGenerated by VC Analysis System on {current_date}\nData Sources: Company documents, market research, competitive intelligence, technical analysis\nAnalysis Framework: Multi-agent AI system with specialized domain expertise\n")


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
    template_path = os.path.abspath('template.docx')
    doc = Document(template_path)
    now = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    company_name = getattr(profile, 'name', 'Company')

    # --- Mermaid diagram rendering automation ---
    mermaid_blocks = list(re.finditer(r'```mermaid\s*([\s\S]+?)```', memo_text))
    mermaid_images = {}
    for idx, match in enumerate(mermaid_blocks):
        code = match.group(1).strip()
        rendered = False
        
        # Try multiple Mermaid rendering services
        services = [
            ('https://kroki.io/mermaid/png', 'Kroki.io'),
            ('https://mermaid.ink/img/', 'Mermaid.ink'),
        ]
        
        for service_url, service_name in services:
            if rendered:
                break
            try:
                if service_name == 'Kroki.io':
                    resp = requests.post(service_url, data=code.encode('utf-8'), timeout=30)
                elif service_name == 'Mermaid.ink':
                    # Mermaid.ink uses GET with base64 encoded diagram
                    import base64
                    encoded = base64.b64encode(code.encode('utf-8')).decode('utf-8')
                    resp = requests.get(f"{service_url}{encoded}", timeout=30)
                
                if resp.status_code == 200:
                    img_path = os.path.join('extraction_cache', f'mermaid_{idx}.png')
                    with open(img_path, 'wb') as f:
                        f.write(resp.content)
                    mermaid_images[f'<MERMAID_IMAGE_{idx}>'] = img_path
                    print(f"[Mermaid] Rendered diagram {idx} using {service_name} to {img_path}")
                    rendered = True
                else:
                    print(f"[Mermaid] {service_name} failed to render diagram {idx}: {resp.status_code}")
            except requests.exceptions.Timeout:
                print(f"[Mermaid] {service_name} timeout for diagram {idx}")
            except Exception as e:
                print(f"[Mermaid] {service_name} exception rendering diagram {idx}: {e}")
        
        if not rendered:
            print(f"[Mermaid] All services failed for diagram {idx}, will show as text")
            # Store the Mermaid code as text for fallback
            mermaid_images[f'<MERMAID_IMAGE_{idx}>'] = f"MERMAID_TEXT_{idx}"

    # --- Replace {{COVER_TEXT}} in-place, always center-aligned ---
    cover_found = False
    for i, p in enumerate(doc.paragraphs):
        if '{{COVER_TEXT}}' in p.text:
            cover_found = True
            p.clear()
            phrase_run = p.add_run(f"This Investment Memo for {company_name} was Automatically Generated by the VC Intelligence System")
            phrase_run.font.size = Pt(22)
            phrase_run.bold = True
            phrase_run.font.name = 'Times New Roman'
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            date_para = doc.add_paragraph()
            date_run = date_para.add_run(f"Prepared on {now}")
            date_run.font.size = Pt(14)
            date_run.font.name = 'Times New Roman'
            date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
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
        'Financial Analysis', 'Team & Management', 'ESG Considerations', 'Risks',
        'Investment & Exit Strategies', 'Follow-up Questions & Next Steps', 'Figures & Visuals',
        'Appendix: Additional Tables', 'AI DISCUSSION AND COMMENTARY', 'Key Strengths',
        'Key Weaknesses', 'Opportunities', 'Risks', 'Conclusion',
        'Summary', 'Analysis Framework', 'Strengths', 'Weaknesses',
        'Appendix', 'Figures & Visuals',
        'ESG Alignment', 'Technical Validation Gaps', 'Competitive Landscape Challenges',
        'Execution & Commercialization Risk', 'Technology Risk', 'Competitive Displacement',
        'IP & Freedom to Operate', 'Financial & Funding Risk', 'Market Adoption & Regulatory Risk',
    ]
    known_headers_lower = [h.lower() for h in known_headers]
    for i, p in enumerate(doc.paragraphs):
        if '{{MEMO_CONTENT}}' in p.text:
            memo_found = True
            alignment = p.alignment
            p.clear()
            # --- Split memo into text and diagram blocks ---
            blocks = re.split(r'(```mermaid[\s\S]+?```)', memo_text)
            mermaid_idx = 0
            for block in blocks:
                block = block.strip('\n')
                if block.startswith('```mermaid') and block.endswith('```'):
                    # Mermaid diagram block
                    img_path = mermaid_images.get(f'<MERMAID_IMAGE_{mermaid_idx}>')
                    if img_path and os.path.exists(img_path):
                        para = doc.add_paragraph()
                        para.paragraph_format.first_line_indent = Pt(0)
                        run = para.add_run()
                        try:
                            run.add_picture(img_path, width=Pt(320))
                            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            print(f"[Mermaid] Inserted diagram {mermaid_idx} into DOCX.")
                        except Exception as e:
                            run.add_text(f"[Could not insert Mermaid diagram: {img_path}]")
                            print(f"[Mermaid] Error inserting diagram {mermaid_idx}: {e}")
                    elif img_path and img_path.startswith('MERMAID_TEXT_'):
                        # Fallback: show Mermaid code as text
                        para = doc.add_paragraph()
                        para.paragraph_format.first_line_indent = Pt(0)
                        run = para.add_run("Business Model Schema (Mermaid Diagram):")
                        run.bold = True
                        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        
                        # Add the Mermaid code in a monospace font
                        code_para = doc.add_paragraph()
                        code_para.paragraph_format.first_line_indent = Pt(0)
                        code_run = code_para.add_run(block)
                        code_run.font.name = 'Courier New'
                        code_run.font.size = Pt(10)
                        code_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        print(f"[Mermaid] Inserted text fallback for diagram {mermaid_idx}")
                    else:
                        # No image or text fallback available
                        para = doc.add_paragraph()
                        para.paragraph_format.first_line_indent = Pt(0)
                        run = para.add_run("[Mermaid diagram could not be rendered]")
                        run.italic = True
                        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        print(f"[Mermaid] No fallback available for diagram {mermaid_idx}")
                    mermaid_idx += 1
                    continue
                # Otherwise, process as text (split by lines)
                for line in block.split('\n'):
                    line_stripped = line.strip().replace('**', '').replace('<HEADER>', '').strip()
                    if line_stripped == '•' or not line_stripped:
                        continue
                    header_cleaned = re.sub(r"\s*\([^)]*\)", "", line_stripped)
                    header_cleaned = re.sub(r"^[-=*•#]+\s*", "", header_cleaned)
                    header_cleaned = header_cleaned.replace("**", "").replace("#", "").strip()
                    is_numbered_header = section_header_pattern.match(header_cleaned)
                    is_all_caps = all_caps_pattern.match(header_cleaned) and len(header_cleaned) > 6
                    is_known_header = header_cleaned.lower() in known_headers_lower
                    if is_numbered_header or is_all_caps or is_known_header:
                        if is_numbered_header:
                            header_style = "Heading 1"
                        elif is_all_caps:
                            header_style = "Heading 2"
                        else:
                            header_style = "Heading 3"
                        para = doc.add_paragraph()
                        para.paragraph_format.space_before = Pt(12)
                        run = para.add_run(header_cleaned)
                        run.font.name = 'Times New Roman'
                        run.font.size = Pt(12)
                        run.bold = True
                        para.alignment = alignment if alignment is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
                        para.paragraph_format.line_spacing = 1.5
                        para.paragraph_format.space_after = Pt(6)
                        para.paragraph_format.first_line_indent = Pt(0)
                        last_para = para
                        continue
                    if (line_stripped.startswith('•') or line_stripped.startswith('-') or line_stripped.startswith('*')):
                        bullet_line = re.sub(r"^[•\-*#]+\s*", "• ", line_stripped)
                        bullet_line = bullet_line.replace('*', '').replace('-', '').strip()
                        if not bullet_line.startswith('•'):
                            bullet_line = '• ' + bullet_line.lstrip()
                        para = doc.add_paragraph()
                        # Use the new function to process text with hyperlinks
                        process_text_with_hyperlinks(para, bullet_line)
                        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                        para.paragraph_format.line_spacing = 1.5
                        para.paragraph_format.first_line_indent = Pt(0)
                        last_para = para
                        continue
                    # Normal paragraph
                    para = doc.add_paragraph()
                    # Use the new function to process text with hyperlinks
                    process_text_with_hyperlinks(para, line_stripped)
                    para.alignment = alignment if alignment is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
                    para.paragraph_format.line_spacing = 1.5
                    para.paragraph_format.first_line_indent = Pt(0)
                    last_para = para
            break
    if not memo_found:
        print("[Warning] {{MEMO_CONTENT}} placeholder not found in template.")
    doc.save(output_path)
    print(f"✅ DOCX memo generated from template and saved to {output_path}")
    for img_path in mermaid_images.values():
        try:
            if os.path.exists(img_path):
                os.remove(img_path)
                print(f"[Mermaid] Deleted temporary image {img_path}")
        except Exception as e:
            print(f"[Mermaid] Error deleting temporary image {img_path}: {e}")


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


# --- Excel evaluation output ---
def generate_excel_output(metrics, company_name, timestamp, output_dir):
    """Generate comprehensive Excel analysis"""
    try:
        import pandas as pd
        
        excel_file = os.path.join(output_dir, f"memo_evaluation_{company_name}_{timestamp}.xlsx")
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            
            # Summary sheet
            summary_data = {
                "Metric": [
                    "Company Name",
                    "Generation Time (minutes)",
                    "Total Tokens",
                    "Total Cost (USD)",
                    "Quality Score (/10)",
                    "Time Savings vs Traditional VC (%)",
                    "Cost Savings vs Traditional VC (%)",
                    "Efficiency Improvement (x)",
                    "Sections Present",
                    "Readability Score"
                ],
                "Value": [
                    company_name,
                    f"{metrics.generation_time_seconds / 60:.2f}",
                    f"{sum(metrics.token_usage.values()):,}",
                    f"${metrics.total_cost_usd:.4f}",
                    f"{metrics.analyst_readability_score:.1f}",
                    f"{metrics.traditional_vc_comparison['time_savings_percentage']:.1f}%",
                    f"{metrics.traditional_vc_comparison['cost_savings_percentage']:.1f}%",
                    f"{metrics.traditional_vc_comparison['efficiency_improvement']['time_efficiency']:.1f}x",
                    f"{metrics.section_count}/17",
                    f"{metrics.flesch_kincaid_score:.1f}"
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            
            # Traditional VC comparison sheet
            vc_comp = metrics.traditional_vc_comparison
            comparison_data = {
                "Metric": [
                    "Traditional VC Time (minutes)",
                    "AI System Time (minutes)",
                    "Time Savings (minutes)",
                    "Time Savings (%)",
                    "Traditional VC Cost (USD)",
                    "AI System Cost (USD)",
                    "Cost Savings (USD)",
                    "Cost Savings (%)",
                    "Time Efficiency (x)",
                    "Cost Efficiency (x)"
                ],
                "Value": [
                    vc_comp["traditional_time_minutes"],
                    vc_comp["ai_time_minutes"],
                    vc_comp["traditional_time_minutes"] - vc_comp["ai_time_minutes"],
                    f"{vc_comp['time_savings_percentage']:.1f}%",
                    f"${vc_comp['traditional_cost_usd']:.2f}",
                    f"${vc_comp['ai_cost_usd']:.4f}",
                    f"${vc_comp['cost_savings_usd']:.2f}",
                    f"{vc_comp['cost_savings_percentage']:.1f}%",
                    f"{vc_comp['efficiency_improvement']['time_efficiency']:.1f}x",
                    f"{vc_comp['efficiency_improvement']['cost_efficiency']:.1f}x"
                ]
            }
            
            comparison_df = pd.DataFrame(comparison_data)
            comparison_df.to_excel(writer, sheet_name="VC Comparison", index=False)
            
            # Performance metrics sheet
            performance_data = {
                "Metric": [
                    "Total Generation Time (seconds)",
                    "Total Generation Time (minutes)",
                    "Total Tokens Used",
                    "Total Cost (USD)",
                    "CPU Usage (%)",
                    "GPU Usage (%)",
                    "Memory Usage (MB)",
                    "Section Completeness",
                    "Duplicate Content Ratio",
                    "Unknown Coverage Ratio"
                ],
                "Value": [
                    metrics.generation_time_seconds,
                    metrics.generation_time_seconds / 60,
                    sum(metrics.token_usage.values()),
                    metrics.total_cost_usd,
                    metrics.cpu_usage_percent,
                    metrics.gpu_usage_percent,
                    metrics.memory_usage_mb,
                    "Complete" if metrics.all_sections_present else "Incomplete",
                    f"{metrics.duplicate_ratio:.2%}",
                    f"{metrics.unknown_coverage_ratio:.2%}"
                ]
            }
            
            performance_df = pd.DataFrame(performance_data)
            performance_df.to_excel(writer, sheet_name="Performance Metrics", index=False)
        
        return excel_file
        
    except Exception as e:
        print(f"❌ Error generating Excel output: {e}")
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
        
        # Initialize evaluation tracker with real-time tracking
        from evaluation_metrics import MemoEvaluator
        evaluator = MemoEvaluator()
        evaluator.start_evaluation()
        
        # Track the main analysis pipeline with real timing
        evaluator.log_section_start("COMPLETE ANALYSIS PIPELINE")
        start_time = time.time()
        profile = run_all_sequential_with_text(text, profile, file_path)
        pipeline_time = time.time() - start_time
        
        # Estimate tokens based on text length and processing time
        estimated_tokens = min(len(text) // 2, 8000)  # Conservative estimate
        evaluator.log_section_end("COMPLETE ANALYSIS PIPELINE", tokens_used=estimated_tokens, model="gpt-4o-mini")
        
        # Populate structured data
        profile.tables = tables
        profile.figures = figures

        # Extract images from PDF and generate chart 
        # Use extraction_cache/ for intermediate image extraction only
        intermediate_dir = CACHE_DIR
        output_dir = "out"
        os.makedirs(output_dir, exist_ok=True)
        
        evaluator.log_section_start("VISUAL EXTRACTION")
        extracted_image_paths = extract_images_from_pdf(file_path, intermediate_dir)
        company_name = profile.name or "unknown_company"
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        market_chart_path = None
        if hasattr(profile, "market_size_by_year") and profile.market_size_by_year:
            chart_path = os.path.join(output_dir, f"{company_name.replace(' ', '_')}_market_chart_{date_str}.png")
            generate_sample_market_chart(profile.market_size_by_year, chart_path)
            market_chart_path = chart_path
        evaluator.log_section_end("VISUAL EXTRACTION", tokens_used=0, model="local")
        
        # Attach visuals to profile for use in memo formatting
        profile.extracted_image_paths = extracted_image_paths
        profile.market_chart_path = market_chart_path
        
        # Track memo generation with real timing
        evaluator.log_section_start("MEMO GENERATION")
        memo_start_time = time.time()
        memo_text = format_memo(profile)
        memo_time = time.time() - memo_start_time
        
        # Estimate tokens for memo generation based on content length
        memo_tokens = len(memo_text) // 3  # Rough estimate: 1 token per 3 characters
        evaluator.log_section_end("MEMO GENERATION", tokens_used=memo_tokens, model="gpt-4o")
        
        print(memo_text)
        
        print("\n" + "="*80)
        print("EVALUATION METRICS")
        print("="*80)
        
        # Track document creation
        evaluator.log_section_start("DOCUMENT CREATION")
        docx_filename = f"memo_{company_name.replace(' ', '_')}_{date_str}.docx"
        docx_path = os.path.join(output_dir, docx_filename)
        save_memo_with_template(memo_text, profile, docx_path)
        convert_docx_to_pdf(docx_path)
        evaluator.log_section_end("DOCUMENT CREATION", tokens_used=0, model="local")
        
        # Evaluate the complete memo (using tracked data)
        print("\n🔍 Evaluating memo quality and performance...")
        metrics = evaluator.evaluate_memo(memo_text)
        
        # Save detailed metrics for academic analysis
        evaluation_dir = "evaluation_results"
        pdf_name = Path(file_path).stem
        os.makedirs(evaluation_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = os.path.join(evaluation_dir, f"detailed_metrics_{pdf_name}_{timestamp}.json")
        
        # Save metrics to JSON
        with open(metrics_file, 'w') as f:
            json.dump(metrics.__dict__, f, indent=2, default=str)
        
        # Generate academic summary
        from integrate_evaluation import create_academic_summary
        summary_file = create_academic_summary(metrics_file, evaluation_dir)
        
        # Print key results for supervisor
        print(f"\n🎯 KEY RESULTS:")
        print(f"⏰ Time Savings: {metrics.traditional_vc_comparison['time_savings_percentage']:.1f}%")
        print(f"💰 Cost Savings: {metrics.traditional_vc_comparison['cost_savings_percentage']:.1f}%")
        print(f"📊 Quality Score: {evaluator._calculate_overall_score(metrics):.1f}/10")
        print(f"📈 Efficiency: {metrics.traditional_vc_comparison['efficiency_improvement']['time_efficiency']:.1f}x faster")
        print(f"📋 Sections: {metrics.section_count}/17 present")
        print(f"💵 Total Cost: ${metrics.total_cost_usd:.4f}")
        print(f"⏱️ Total Time: {metrics.generation_time_seconds:.1f} seconds")
        print(f"🖥️ CPU Usage: {metrics.cpu_usage_percent:.1f}%")
        print(f"🎮 GPU Usage: {metrics.gpu_usage_percent:.1f}%")
        print(f"💾 Memory Usage: {metrics.memory_usage_mb:.1f} MB")
        
        print(f"\n📊 Detailed metrics saved to: {metrics_file}")
        print(f"📚 Academic summary saved to: {summary_file}")
        
        # Generate Excel output with comprehensive analysis
        try:
            excel_file = generate_excel_output(metrics, company_name, date_str, evaluation_dir)
            if excel_file:
                print(f"📈 Excel analysis saved to: {excel_file}")
        except ImportError:
            print("⚠️ pandas not available - skipping Excel output")
        except Exception as e:
            print(f"⚠️ Error generating Excel output: {e}")


if __name__ == "__main__":
    main()
