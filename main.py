import sys
import os
import hashlib
import json as pyjson
import subprocess
import tempfile
import re
from datetime import datetime
from core.download_utils import extract_text
from core.schemas import StartupProfile
from core.vector_store import clear_collection
from fpdf import FPDF
from langchain_openai import ChatOpenAI
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from core.perplexity_utils import search_perplexity
from core.visual_utils import extract_images_from_pdf, generate_sample_market_chart
from agents.technical_dd_agent import build_technical_dd_agent
from agents.market_sizing_agent import build_market_sizing_agent
from agents.competitive_intel_agent import build_competitive_intel_agent
from agents.founder_profiling_agent import build_founder_profiling_agent
from agents.financial_analysis_agent import build_financial_analysis_agent
from agents.risk_assessment_agent import build_risk_assessment_agent
from agents.deck_agent import build_deck_agent
from agents.business_model_agent import build_business_model_chain_agent
from agents.esg_agent import build_esg_chain_agent
from agents.exit_strategy_agent import build_exit_chain_agent
from agents.follow_up_agent import build_followup_chain_agent
from crewai import Crew, Agent, Task, Process
from dotenv import load_dotenv
load_dotenv()

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

def enrich_executives_with_perplexity(company_name, existing_execs):
    """
    Use Perplexity to find additional executives and their LinkedIn profiles if fewer than 3 are found.
    """
    if not company_name or len(existing_execs) >= 3:
        return existing_execs
    query = f"List the CEO/founder, CFO, CTO, and Chairman of {company_name} with their LinkedIn URLs if available."
    result = search_perplexity(query)
    if not result:
        return existing_execs
    # Simple parsing: look for lines with name, role, and LinkedIn
    import re
    execs = existing_execs.copy()
    for line in result.split('\n'):
        match = re.match(r"[-•]?\s*(.+?)\s*\((.+?)\):?\s*(https?://[\w./-]+)?", line)
        if match:
            name, role, linkedin = match.groups()
            name = name.strip()
            role = role.strip()
            linkedin = linkedin.strip() if linkedin else ''
            # Deduplicate by name
            if not any(e.get('name', '').lower() == name.lower() for e in execs):
                execs.append({'name': name, 'role': role, 'linkedin': linkedin})
        elif 'linkedin.com/in/' in line:
            # Fallback: try to extract name, role, linkedin from a line with a LinkedIn URL
            parts = line.split(' - ')
            if len(parts) >= 2:
                name_role = parts[0].strip()
                linkedin = [p for p in parts if 'linkedin.com/in/' in p][0].strip()
                if '(' in name_role and ')' in name_role:
                    name, role = name_role.split('(', 1)
                    name = name.strip()
                    role = role.replace(')', '').strip()
                    if not any(e.get('name', '').lower() == name.lower() for e in execs):
                        execs.append({'name': name, 'role': role, 'linkedin': linkedin})
    return execs[:3]

def enrich_executive_details_with_perplexity(company_name, executives):
    enriched = []
    for exec in executives:
        name = exec.get('name', '').strip()
        role = exec.get('role', '').strip()
        linkedin = exec.get('linkedin', '').strip()
        bio = exec.get('bio', '').strip() if 'bio' in exec else ''
        # Enrich LinkedIn if missing
        if not linkedin and name and company_name:
            query = f"What is the LinkedIn profile URL for {name} at {company_name}?"
            result = search_perplexity(query)
            if result and 'linkedin.com/in/' in result:
                import re
                # Find LinkedIn URL in result
                match = re.search(r"https?://[\w./-]*linkedin.com/in/[\w/_-]+", result)
                if match:
                    linkedin = match.group(0)
        # Enrich bio if missing or generic
        if (not bio or 'not available' in bio.lower() or 'unknown' in bio.lower()) and name and role and company_name:
            query = f"Write a 2-3 sentence professional bio for {name}, {role} at {company_name}. Include notable past roles, companies, and achievements if available."
            result = search_perplexity(query)
            if result and len(result.split()) > 8:
                bio = result.strip()
        exec['linkedin'] = linkedin
        exec['bio'] = bio
        enriched.append(exec)
    return enriched

# Add product_description to StartupProfile if not present
if not hasattr(StartupProfile, 'product_description'):
    StartupProfile.product_description = None


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

def synthesize_product_description_llm(profile):
    """
    Use LLM to synthesize a detailed, multi-paragraph, multi-bullet Product/Service Description section for the memo, matching the style of memo_generator's generate_llm_memo.
    """
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    context = f"""
Company: {getattr(profile, 'name', 'N/A')}
Sector: {getattr(profile, 'sector', 'N/A')}
Product Description: {getattr(profile, 'product_description', '')}
Product Specs: {getattr(profile, 'product_specs', '')}
Product Roadmap: {getattr(profile, 'product_roadmap', '')}
Unique Features: {getattr(profile, 'unique_features', '')}
Status: {getattr(profile, 'status', '')}
Cell Format: {getattr(profile, 'cell_format', '')}
Cycle Life: {getattr(profile, 'cycle_life', '')}
Performance: {getattr(profile, 'performance', '')}
Technology: {getattr(profile, 'technology', '')}
Differentiator: {getattr(profile, 'differentiator', '')}
"""
    prompt = f"""
You are a top-tier senior venture capitalist with experience in evaluating early-stage startups. Your role is to generate a detailed, critical Product/Service Description section for an investment memorandum, using only the provided context. Do not make up facts. Use plain text (no HTML). Structure the output as follows:

- Begin with a concise overview paragraph of the product/service and its purpose.
- Add subheadings and bullet points for:
  • Key Features and Functionality (bulleted)
  • Performance and Scalability (bulleted)
  • Extensibility and Integration (bulleted)
  • Open-Source/Community Aspects (if relevant)
  • Product Roadmap (as a subheading or bullet list if available)
- Highlight what differentiates this product/service from competitors.
- Use a critical, VC-style lens—note both strengths and any missing or unclear information.
- Do not hallucinate or invent details not present in the context.

Context:
{context}
"""
    response = llm.invoke(prompt)
    return response.content if hasattr(response, 'content') else response


# --- Enhanced Detailed Summary Paragraph ---
def synthesize_detailed_summary(profile):
    """
    Produce a 3–4 sentence overview based solely on whatever fields
    have been populated in `profile`. No hard-coded company names.
    """
    name    = getattr(profile, 'name', None) or "The company"
    founder = getattr(profile, 'founder_name', None)
    sector  = getattr(profile, 'sector', None)
    tech    = getattr(profile, 'technology', None) or getattr(profile, 'product_description', None)
    model   = getattr(profile, 'business_model', None)
    patents = getattr(profile, 'patents', None)
    partners= getattr(profile, 'partnerships', None)

    parts = []
    # Lead sentence
    lead = f"{name} is a {sector or ''} company"
    if tech:
        lead += f" leveraging {tech}"
    lead += "."
    parts.append(lead)

    # Founder mention (if available)
    if founder:
        parts.append(f"It was founded by {founder}.")

    # Business model
    if model:
        parts.append(f"Their business model centers on {model}.")

    # Patent/IP / Partnerships
    extras = []
    if patents:
        extras.append(f"{patents} patents")
    if partners:
        extras.append(f"partnerships with {partners}")
    if extras:
        parts.append("They currently hold " + " and ".join(extras) + ".")

    # Return the first 3–4 sentences
    return " ".join(parts[:4])


# --- Enhanced Problem Statement and Solution Reasoning ---
def synthesize_problem_statement(profile) -> str:
    """
    Craft a short, 2-4-sentence statement of the pain-point the company is
    addressing, using ONLY info that already exists in `profile`.

    Behaviour
    ---------
    • If profile.problem_statement already looks good (≥10 words) → return it.
    • Otherwise build one from whatever fields are available:
        sector, customer_segment, pain_point, current_solution,
        market_trend, negative_impact … (all optional).
    • If we still can't build ≥2 sensible sentences, fall back to a
      neutral, industry-agnostic paragraph.
    """

    # 1)  Re-use a supplied statement if it's long enough
    raw = getattr(profile, "problem_statement", None)
    if raw and len(raw.split()) >= 10:
        return raw.strip()

    # 2)  Assemble one from crumbs we already extracted
    sector      = getattr(profile, "sector",            None) or "the market"
    customer    = getattr(profile, "customer_segment",  None) \
               or getattr(profile, "target_market",     None) \
               or "customers"
    pain        = getattr(profile, "pain_point",        None) \
               or getattr(profile, "key_challenge",     None)
    status_quo  = getattr(profile, "current_solution",  None)
    trend       = getattr(profile, "market_trend",      None)
    impact      = getattr(profile, "negative_impact",   None)

    sents = []

    # Who + what
    if pain:
        sents.append(
            f"{customer.capitalize()} face {pain}, an issue {sector} has struggled with for years."
        )
    elif status_quo:
        sents.append(
            f"Within {sector}, {customer} still rely on {status_quo}, which is increasingly inadequate."
        )

    # Trend / context
    if trend:
        sents.append(
            f"Shifts in the market – {trend} – are magnifying the urgency of this challenge."
        )

    # Impact / consequence
    if impact:
        sents.append(
            f"As a result, organisations experience {impact}, limiting growth and profitability."
        )

    if len(sents) >= 2:
        return " ".join(sents)

    # 3)  Last-resort neutral fallback
    return (
        "Target customers struggle with fragmented, outdated processes that raise costs, "
        "consume valuable time, and restrict scalability. Despite clear demand for more efficient "
        "alternatives, incumbent solutions have failed to keep pace – leaving a significant gap in the market."
    )

def synthesize_solution_overview(profile) -> str:
    """
    Produce a succinct, 3-5-sentence description of how the company solves
    the above problem. 100 % data-driven – no baked-in industry language.

    Logic
    -----
    • Honour an existing `solution_overview` if it's reasonably long.
    • Otherwise compose a paragraph from fields like technology,
      unique_features, benefits, compatibility_notes, roadmap, etc.
    • Final fallback: a neutral paragraph that says the company introduces
      a novel, data-driven platform/service to address the pain-point.
    """

    # 1)  Use the user-supplied overview if present
    raw = getattr(profile, "solution_overview", None)
    if raw and len(raw.split()) >= 10:
        return raw.strip()

    # 2)  Build one from profile crumbs
    name          = getattr(profile, "name",                "The company")
    tech          = getattr(profile, "technology",          None) \
                 or getattr(profile, "product_description", None) \
                 or "a novel technology"
    features      = getattr(profile, "unique_features",     None)
    benefits      = getattr(profile, "benefits",            None)
    compatibility = getattr(profile, "compatibility_notes", None)
    roadmap       = getattr(profile, "product_roadmap",     None)

    sents = [
        f"{name} introduces {tech} that directly tackles the above pain-point."
    ]

    if features:
        sents.append(f"Key differentiators include {features}.")
    if compatibility:
        sents.append(f"The solution is compatible with {compatibility}, easing adoption.")
    if benefits:
        sents.append(f"Customers gain {benefits}.")
    if roadmap:
        sents.append(f"The roadmap outlines: {roadmap}.")

    # If that got us >2 sentences, great
    if len(sents) >= 2:
        return " ".join(sents[:5])

    # 3)  Neutral fallback
    return (
        f"{name} delivers an end-to-end platform that streamlines workflows, "
        "reduces operating friction, and unlocks new revenue opportunities for its target customers."
    )

# --- Inline Source Attribution for Market Size & Analysis ---
def format_money(val):
    try:
        val = float(val)
    except (TypeError, ValueError):
        return str(val)
    print(f"[DEBUG] format_money raw value: {val}")  # Debug print for diagnosis
    abs_val = abs(val)
    if abs_val >= 1_000_000_000:
        if val % 1_000_000_000 == 0:
            return f"${val/1_000_000_000:,.0f} B"
        else:
            return f"${val/1_000_000_000:,.1f} B"
    elif abs_val >= 1_000_000:
        if val % 1_000_000 == 0:
            return f"${val/1_000_000:,.0f} M"
        else:
            return f"${val/1_000_000:,.1f} M"
    elif abs_val >= 1_000:
        if val % 1_000 == 0:
            return f"${val/1_000:,.0f} K"
        else:
            return f"${val/1_000:,.1f} K"
    else:
        return f"${val:,.0f}"

def format_market_size_section(profile):
    # Get LLM-generated narrative if available
    narrative = getattr(profile, 'market_summary', '') or getattr(profile, 'market_size_narrative', '')
    TAM = format_money(getattr(profile, 'TAM', 0))
    SAM = format_money(getattr(profile, 'SAM', 0))
    SOM = format_money(getattr(profile, 'SOM', 0))
    try:
        penetration = (float(getattr(profile, 'SOM', 0)) / float(getattr(profile, 'TAM', 1))) * 100 if getattr(profile, 'TAM', 0) else 0
    except Exception:
        penetration = 0
    source = getattr(profile, 'market_source', None) or 'Pitch deck'
    # Compose a richer discussion
    discussion_parts = []
    # Growth drivers and inhibitors
    discussion_parts.append("Growth is driven by increasing EV adoption, regulatory mandates for clean energy, and advances in battery technology. Inhibitors include supply chain constraints, raw material costs, and evolving safety standards.")
    # Opportunities and threats
    discussion_parts.append("Key opportunities include first-mover advantage, strategic partnerships, and addressing unmet needs in fast-charging and energy density. Threats include new entrants, disruptive chemistries, and policy uncertainty.")
    # SOM justification
    som_just = getattr(profile, 'som_justification', None)
    if som_just:
        discussion_parts.append(f"SOM is based on: {som_just}")
    else:
        discussion_parts.append("SOM is based on company projections and may require independent validation.")
    # Segmentation, regional trends, customer types
    segmentation = getattr(profile, 'market_segmentation', None)
    if segmentation:
        discussion_parts.append(f"Market segmentation: {segmentation}")
    # Recent news/events
    recent_news = getattr(profile, 'market_news', None)
    if recent_news:
        discussion_parts.append(f"Recent market news: {recent_news}")
    # Source and verification
    if source.lower() == 'pitch deck':
        discussion_parts.append('(Market size is based on company materials; independent verification recommended.)')
    else:
        discussion_parts.append(f"Source: {source}")
    # Compose final discussion
    market_discussion = ' '.join(discussion_parts)
    lines = []
    if narrative:
        lines.append(narrative.strip())
    lines.append(f"TAM {TAM}, SAM {SAM}, SOM {SOM}; Market Penetration: {penetration:.1f} %")
    if market_discussion:
        lines.append(market_discussion)
    # Remove sector name at end (do not append)
    return '\n'.join(lines)

# --- Expanded Competitive Landscape ---
def format_competitive_landscape(profile):
    competitors = getattr(profile, 'top_competitors', [])
    if not competitors:
        return 'Competitor analysis not available.'
    lines = []
    for comp in competitors:
        # Name and website
        name = comp.get('name', 'Unknown')
        website = comp.get('website', '') or comp.get('url', '')
        name_line = f"• {name} ({website})" if website else f"• {name}"
        lines.append(name_line)
        # Total funding
        funding = comp.get('total_funding', '')
        if funding:
            lines.append(f"  • Total Funding: {funding}")
        # Product offering/description
        product = comp.get('product_offering', '') or comp.get('product', '') or comp.get('description', '')
        if product:
            lines.append(f"  • Product Offering: {product}")
        # Traction
        traction = comp.get('traction', '')
        if traction:
            lines.append(f"  • Traction: {traction}")
        # Differentiator
        differentiator = comp.get('differentiator', '')
        if differentiator:
            lines.append(f"  • Differentiator: {differentiator}")
    return '\n'.join(lines)

def format_technical_dd_section(profile):
    # Display the full LLM-generated technical due diligence narrative if available
    narrative = getattr(profile, 'technical_dd_narrative', '') or getattr(profile, 'technical_dd_analysis', '')
    tech = profile.tech_maturity or 'N/A'
    moat = profile.moat_strength or ''
    tech_stack = getattr(profile, 'tech_stack', None)
    regulatory = getattr(profile, 'regulatory', None)
    testing = getattr(profile, 'testing', None)
    security = getattr(profile, 'security', None)
    complexity = getattr(profile, 'complexity', None)
    implementation = getattr(profile, 'implementation', None)
    # assumption_risks = getattr(profile, 'assumption_risks', None)  # Removed
    bullets = []
    bullets.append(f"• Technical Feasibility and Performance: {tech}.")
    if moat:
        bullets.append(f"• Moat: {moat}.")
    if tech_stack:
        bullets.append(f"• Tech Stack: {tech_stack}.")
    bullets.append(f"• Complexity: {complexity or 'Not specified.'}")
    bullets.append(f"• Security: {security or 'Product safety, data, and IP protection should be addressed.'}")
    bullets.append(f"• Implementation: {implementation or 'Implementation details not specified.'}")
    # bullets.append(f"• Assumption Risks: {assumption_risks or 'Assumption risks not specified.'}")  # Removed
    bullets.append(f"• Regulatory: {regulatory or 'Compliance with industry standards and certifications is required.'}")
    bullets.append(f"• Testing: {testing or 'Independent validation and certification are recommended.'}")
    bullets.append("• Further technical due diligence is required, including independent validation of performance claims, cycle life, and safety.")
    lines = []
    if narrative:
        lines.append(narrative.strip())
    lines.extend(bullets)
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
    implied_valuation = getattr(profile, 'implied_valuation', None)
    cash_burn_12m = getattr(profile, 'cash_burn_12m', None)
    runway_months = getattr(profile, 'runway_months', None)
    SOM = getattr(profile, 'SOM', None)
    ASP = getattr(profile, 'average_selling_price', None)
    # Estimate potential revenue and valuation
    revenue_projection = None
    valuation_projection = None
    revenue_comment = ""
    if SOM:
        try:
            som_val = float(SOM)
            asp_val = float(ASP) if ASP else 100000  # Default ASP if not available
            revenue_projection = som_val * asp_val
            valuation_projection = revenue_projection * 8  # 8x revenue multiple as a default
            revenue_comment = f"\nPotential Annual Revenue (if full SOM captured): {format_money(revenue_projection)} (Assumes ASP ${asp_val:,.0f})\nPotential Valuation (8x revenue): {format_money(valuation_projection)}"
        except Exception:
            revenue_comment = "\nPotential revenue/valuation projections unavailable due to missing or invalid data."
    else:
        revenue_comment = "\nPotential revenue/valuation projections unavailable due to missing SOM."
    if not (implied_valuation or cash_burn_12m or runway_months):
        return f"Company has not released financials as of {current_date}.{revenue_comment}"
    else:
        return f"Implied Valuation: {format_money(implied_valuation) if implied_valuation else 'N/A'}\nCash Burn (12 months): {format_money(cash_burn_12m) if cash_burn_12m else 'N/A'}\nRunway: {runway_months if runway_months else 'N/A'} months{revenue_comment}"

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

# Move the entire format_risk_section(profile) function definition so it is above format_memo(profile: StartupProfile)
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

def synthesize_risks_section_llm(profile):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    context = f"""
Company: {getattr(profile, 'name', 'N/A')}
Sector: {getattr(profile, 'sector', '')}
Risks: {getattr(profile, 'risk_flags', '')}
Risk Score: {getattr(profile, 'risk_score', '')}
Financials: {getattr(profile, 'financials', '')}
Competitive Landscape: {getattr(profile, 'competitive_summary', '')}
Product/Tech: {getattr(profile, 'product_description', '')}
"""
    prompt = f"""
You are a top-tier VC analyst. Write a detailed, multi-bullet, multi-paragraph Risks & Mitigations section for an investment memo, using only the provided context. For each risk, include:
- A clear, specific risk title (e.g., 'Feature Commoditization', 'Open-Source Vulnerabilities', 'Customer Acquisition Costs')
- A short explanation of the risk and why it matters
- (Optional) A brief note on possible mitigation, or state if mitigation is unclear
Cover market, technical, operational, and regulatory risks. Use a critical, VC-style lens. Do not make up facts. Use plain text, no HTML.
Context:
{context}
"""
    response = llm.invoke(prompt)
    return response.content if hasattr(response, 'content') else response

def format_team_section(profile):
    lines = []
    # Only show key roles: founder/CEO, CFO, chairman, and any C-levels
    execs = getattr(profile, 'executives', None) or []
    founder = getattr(profile, 'founder_name', None)
    key_roles = ['founder', 'ceo', 'chief executive officer', 'cfo', 'chief financial officer', 'chairman', 'cto', 'chief technology officer', 'coo', 'chief operating officer']
    shown = set()
    # Always show founder if present
    if founder:
        lines.append(f"Founder: {founder}")
        shown.add(founder.lower())
    for exec in execs:
        if isinstance(exec, dict):
            name = exec.get('name', 'Unknown')
            role = exec.get('role', '').lower()
            linkedin = exec.get('linkedin', '')
            # Only show if role is in key_roles or if not already shown
            if any(r in role for r in key_roles) and name.lower() not in shown:
                line = f"{name} ({exec.get('role', '')})"
                if linkedin:
                    line += f" | LinkedIn: {linkedin}"
                lines.append(line)
                shown.add(name.lower())
    # Prior exits
    prior_exits = getattr(profile, 'prior_exits', None)
    prior_exit_details = getattr(profile, 'prior_exit_details', None) or []
    if prior_exits and int(prior_exits) > 0:
        lines.append(f"Prior Exits: {prior_exits}")
        for exit in prior_exit_details:
            if isinstance(exit, dict):
                cname = exit.get('company', 'Unknown')
                link = exit.get('link', '')
                if link:
                    lines.append(f"  - {cname}: {link}")
                else:
                    lines.append(f"  - {cname}")
            else:
                lines.append(f"  - {exit}")
    # LinkedIn summary (if available)
    if hasattr(profile, 'founder_linkedin_formatted'):
        lines.append(profile.founder_linkedin_formatted)
    return '\n'.join(lines) if lines else 'Team and management information not available.'

def synthesize_team_section_llm(profile):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    context = f"""
Company: {getattr(profile, 'name', 'N/A')}
Executives: {getattr(profile, 'executives', '')}
Sector: {getattr(profile, 'sector', '')}
"""
    prompt = f"""
You are a top-tier VC analyst. Write a detailed, multi-paragraph, multi-bullet Team & Management section for an investment memo, using only the provided context. For each of the 3 key team members (founder/CEO, CFO, CTO/Chairman), include:
- Name and role
- LinkedIn (if available)
- Short bio/track record (notable companies, roles, achievements)
Use a critical, VC-style lens. Do not make up facts. Use plain text, no HTML.
Context:
{context}
"""
    response = llm.invoke(prompt)
    return response.content if hasattr(response, 'content') else response

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

def format_memo(profile: StartupProfile) -> str:
    current_date = datetime.now().strftime("%B %d, %Y")
    def clean(text):
        return text.replace('B253500', '') if isinstance(text, str) else text
    memo_body = f"""
INVESTMENT MEMORANDUM – {clean_company_name(getattr(profile, 'name', None)) or 'COMPANY ANALYSIS'}
1. DETAILED SUMMARY
{clean(synthesize_detailed_summary(profile))}

2. COMPANY OVERVIEW
Company: {clean(getattr(profile, 'name', None)) or 'TBD'}
Sector: {clean(getattr(profile, 'sector', None) or 'TBD')}
Website: {clean(getattr(profile, 'website', None) or 'TBD')}
Funding Stage: {format_funding_stage(profile)}
Team: {clean(getattr(profile, 'founder_name', None) or 'TBD')}
{clean(getattr(profile, 'founder_linkedin_formatted', ''))}

3. PROBLEM STATEMENT
{clean(synthesize_problem_statement(profile))}

4. SOLUTION OVERVIEW
{clean(synthesize_solution_overview(profile))}

5. MARKET SIZE & ANALYSIS
{format_market_size_section(profile)}
{clean(getattr(profile, 'sector', ''))}

6. COMPETITORS
{format_competitive_landscape(profile)}
{clean(getattr(profile, 'competitive_summary', ''))}

7. BUSINESS MODEL
{clean(profile.business_model) if getattr(profile, 'business_model', None) else 'Business model analysis not available.'}

8. TECHNICAL DUE DILIGENCE
{format_technical_dd_section(profile)}

9. PRODUCT/SERVICE DESCRIPTION
{synthesize_product_description_llm(profile)}

10. FINANCIAL ANALYSIS
{format_financials_section(profile, current_date)}

11. TEAM & MANAGEMENT
{synthesize_team_section_llm(profile)}

12. ESG CONSIDERATIONS
{clean(profile.esg_summary) if getattr(profile, 'esg_summary', None) else 'ESG analysis not available.'}

13. RISKS & MITIGATIONS
{synthesize_risks_section_llm(profile)}

14. INVESTMENT & EXIT STRATEGIES
{clean(profile.exit_strategy) if getattr(profile, 'exit_strategy', None) else 'Exit strategy analysis not available.'}

15. FOLLOW-UP QUESTIONS & NEXT STEPS
{format_followup_section(profile)}

16. ADDITIONAL FIGURES & VISUALS
{clean(getattr(profile, 'figures_section', ''))}
"""
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)
    discussion_prompt = f"""
You are a senior VC analyst. Based on the following investment memo, provide a critical discussion and analyst commentary. Highlight key strengths, weaknesses, opportunities, and risks. Offer actionable recommendations for investors. Be concise but insightful.

MEMO:
{memo_body}
"""
    discussion = llm.invoke(discussion_prompt).content.strip()
    # De-duplication post-processing
    return deduplicate_memo(f"{memo_body}\n17. DISCUSSION & ANALYST COMMENTARY\n{discussion}\n\n---\nGenerated by VC Analysis System on {current_date}\nData Sources: Company documents, market research, competitive intelligence, technical analysis\nAnalysis Framework: Multi-agent AI system with specialized domain expertise\n")


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
    # In save_memo_with_template, track page breaks and insert a blank paragraph after the 2nd page break
    page_break_count = 0
    for i, p in enumerate(doc.paragraphs):
        if '{{MEMO_CONTENT}}' in p.text:
            memo_found = True
            alignment = p.alignment
            p.clear()
            memo_lines = memo_text.split('\n')
            for idx, line in enumerate(memo_lines):
                line_stripped = line.strip().replace('**', '').replace('<HEADER>', '').strip()
                if line_stripped == '•' or not line_stripped:
                    continue
                # Remove text in brackets from section headers
                header_cleaned = re.sub(r"\s*\([^)]*\)", "", line_stripped)
                # Remove dashes, asterisks, hashes, and extra symbols from headers and bullets
                header_cleaned = re.sub(r"^[-=*•#]+\s*", "", header_cleaned)
                header_cleaned = header_cleaned.replace("**", "").replace("#", "").strip()
                is_numbered_header = section_header_pattern.match(header_cleaned)
                is_all_caps = all_caps_pattern.match(header_cleaned) and len(header_cleaned) > 6
                is_known_header = header_cleaned.lower() in known_headers_lower
                # --- PATCH: Insert images/graphs after 'Figures & Visuals' header ---
                # (Removed: now handled by deck agent. If visuals are present in profile, insert as before.)
                # if header_cleaned.lower() == 'figures & visuals':
                #     para = doc.add_paragraph()
                #     para.paragraph_format.space_before = Pt(12)
                #     run = para.add_run(header_cleaned)
                #     run.font.name = 'Times New Roman'
                #     run.font.size = Pt(12)
                #     run.bold = True
                #     para.alignment = alignment if alignment is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
                #     para.paragraph_format.line_spacing = 1.5
                #     para.paragraph_format.space_after = Pt(6)
                #     para.paragraph_format.first_line_indent = Pt(0)
                #     last_para = para
                #     # Insert extracted images
                #     if hasattr(profile, 'extracted_image_paths') and profile.extracted_image_paths:
                #         for img_idx, img_path in enumerate(profile.extracted_image_paths):
                #             img_para = doc.add_paragraph()
                #             run = img_para.add_run()
                #             try:
                #                 run.add_picture(img_path, width=Pt(320))  # ~4.5in wide
                #             except Exception as e:
                #                 run.add_text(f"[Could not insert image: {img_path}]")
                #             # Caption
                #             caption = img_para.add_run(f"\nFigure {img_idx+1}: Extracted from pitch deck")
                #             caption.font.name = 'Times New Roman'
                #             caption.font.size = Pt(12)
                #             img_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                #     # Insert generated chart
                #     if hasattr(profile, 'market_chart_path') and profile.market_chart_path:
                #         chart_para = doc.add_paragraph()
                #         run = chart_para.add_run()
                #         try:
                #             run.add_picture(profile.market_chart_path, width=Pt(320))
                #         except Exception as e:
                #             run.add_text(f"[Could not insert chart: {profile.market_chart_path}]")
                #         caption = chart_para.add_run("\nFigure: Market Size Chart")
                #         caption.font.name = 'Times New Roman'
                #         caption.font.size = Pt(12)
                #         chart_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                #     continue
                # Special handling for DISCUSSION & ANALYST COMMENTARY section headers
                discussion_headers = [
                    'Analyst Commentary on Investment Memo', 'Key Strengths', 'Key Weaknesses',
                    'Opportunities', 'Risks', 'Actionable Recommendations for Investors', 'Summary'
                ]
                # --- PATCH: Always use '•' for bullets in section 18 and its subheaders ---
                if any(h in header_cleaned for h in discussion_headers) or any(line_stripped.startswith(h) for h in discussion_headers):
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
                # Clean up bullets for this section (force '•' and remove all '*', '-')
                if (line_stripped.startswith('•') or line_stripped.startswith('-') or line_stripped.startswith('*')):
                    # Remove all stars and dashes, replace with '• '
                    bullet_line = re.sub(r"^[•\-*#]+\s*", "• ", line_stripped)
                    bullet_line = bullet_line.replace('*', '').replace('-', '').strip()
                    if not bullet_line.startswith('•'):
                        bullet_line = '• ' + bullet_line.lstrip()
                    para = doc.add_paragraph()
                    run = para.add_run(bullet_line)
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
                    para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    para.paragraph_format.line_spacing = 1.5
                    para.paragraph_format.first_line_indent = Pt(0)
                    last_para = para
                    continue
                # Add a space before each section header for visual separation
                if is_numbered_header or is_all_caps or is_known_header:
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
                # Special handling for RISKS & MITIGATIONS risk headers
                if (
                    'RISKS & MITIGATIONS' in ''.join(memo_lines[max(0, idx-3):idx+1]).upper() and
                    not line_stripped.startswith('•') and
                    not line_stripped.lower().startswith('explanation:') and
                    not line_stripped.lower().startswith('mitigation:') and
                    line_stripped and
                    idx+1 < len(memo_lines) and
                    (memo_lines[idx+1].strip().lower().startswith('• explanation:') or
                     memo_lines[idx+1].strip().lower().startswith('• mitigation:'))
                ):
                    para = doc.add_paragraph()
                    run = para.add_run(line_stripped)
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
                    run.bold = True
                    para.alignment = alignment if alignment is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
                    para.paragraph_format.line_spacing = 1.5
                    para.paragraph_format.space_before = Pt(8)
                    para.paragraph_format.space_after = Pt(2)
                    para.paragraph_format.first_line_indent = Pt(0)
                    last_para = para
                    continue
                # Special handling for FOLLOW-UP QUESTIONS section headers (bulleted headers)
                if (
                    'FOLLOW-UP QUESTIONS' in ''.join(memo_lines[max(0, idx-3):idx+1]).upper() and
                    line_stripped.startswith('•') and
                    ':' not in line_stripped and
                    idx+1 < len(memo_lines) and
                    memo_lines[idx+1].strip().startswith('•')
                ):
                    header_text = line_stripped.lstrip('•').strip()
                    para = doc.add_paragraph()
                    run = para.add_run(header_text)
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
                    run.bold = True
                    para.alignment = alignment if alignment is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
                    para.paragraph_format.line_spacing = 1.5
                    para.paragraph_format.space_before = Pt(8)
                    para.paragraph_format.space_after = Pt(2)
                    para.paragraph_format.first_line_indent = Pt(0)
                    last_para = para
                    continue
                # Special handling for bullet points in the FOLLOW-UP QUESTIONS section
                if line_stripped.startswith('• '):
                    bullet_line = line_stripped
                    # Remove any leading asterisks or dashes from bullets
                    bullet_line = re.sub(r"^[-*]+\\s*", "• ", bullet_line)
                    para = doc.add_paragraph()
                    run = para.add_run(bullet_line)
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
                    para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    para.paragraph_format.line_spacing = 1.5
                    para.paragraph_format.first_line_indent = Pt(0)
                    last_para = para
                    continue
                # For numbered headers, ensure '•' is used and no '-'
                if is_numbered_header:
                    bullet_line = header_cleaned
                    if bullet_line.startswith('-'):
                        bullet_line = '•' + bullet_line[1:]
                    # Remove any leading asterisks or dashes from bullets
                    bullet_line = re.sub(r"^[-*]+\\s*", "• ", bullet_line)
                    para = doc.add_paragraph()
                    run = para.add_run(bullet_line)
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
                    para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    para.paragraph_format.line_spacing = 1.5
                    para.paragraph_format.first_line_indent = Pt(0)
                    last_para = para
                    continue
                # For all other lines, apply bullet point formatting
                bullet_line = line_stripped
                if bullet_line.startswith('-'):
                    bullet_line = '•' + bullet_line[1:]
                # Remove any leading asterisks or dashes from bullets
                bullet_line = re.sub(r"^[-*]+\\s*", "• ", bullet_line)
                para = doc.add_paragraph()
                run = para.add_run(bullet_line)
                run.font.name = 'Times New Roman'
                run.font.size = Pt(12)
                para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                para.paragraph_format.line_spacing = 1.5
                para.paragraph_format.first_line_indent = Pt(0)
                last_para = para
                # In save_memo_with_template, track page breaks and insert a blank paragraph after the 2nd page break
                if line_stripped == '<PAGE_BREAK>':
                    doc.add_page_break()
                    page_break_count += 1
                    # Insert a blank paragraph after the 2nd page break (i.e., starting from the 3rd page)
                    if page_break_count >= 2:
                        blank_para = doc.add_paragraph()
                        blank_para.add_run("")
                        blank_para.paragraph_format.space_after = Pt(0)
                        blank_para.paragraph_format.space_before = Pt(0)
                        blank_para.paragraph_format.first_line_indent = Pt(0)
                    continue
            break
    if not memo_found:
        print("[Warning] {{MEMO_CONTENT}} placeholder not found in template.")
    doc.save(output_path)
    print(f"✅ DOCX memo generated from template and saved to {output_path}")


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


# --- Utility functions to extract relevant sections from the full text ---
def get_technical_section(text):
    # Implement logic to extract technical section from the full text
    # For now, use a simple heuristic (can be improved)
    import re
    match = re.search(r'(Technical Due Diligence|Technology|Product|Solution)[\s\S]{0,1000}', text, re.IGNORECASE)
    return match.group(0) if match else text[:2000]

def get_founder_section(text):
    import re
    match = re.search(r'(Founder|Team|Management)[\s\S]{0,1000}', text, re.IGNORECASE)
    return match.group(0) if match else text[:2000]

def get_market_section(text):
    import re
    match = re.search(r'(Market|TAM|SAM|SOM|Opportunity)[\s\S]{0,1000}', text, re.IGNORECASE)
    return match.group(0) if match else text[:2000]

def get_financial_section(text):
    import re
    match = re.search(r'(Financial|Revenue|Profit|Loss|P&L|EBITDA|Cash Flow)[\s\S]{0,1000}', text, re.IGNORECASE)
    return match.group(0) if match else text[:2000]

def get_competitive_section(text):
    import re
    match = re.search(r'(Competitor|Competitive|Landscape|Comparison)[\s\S]{0,1000}', text, re.IGNORECASE)
    return match.group(0) if match else text[:2000]

def get_risk_section(text):
    import re
    match = re.search(r'(Risk|Mitigation|Threat|Challenge)[\s\S]{0,1000}', text, re.IGNORECASE)
    return match.group(0) if match else text[:2000]

def clean_company_name(name):
    if not name:
        return name
    return re.sub(r'[^A-Za-z0-9 ]+', '', name)

def run_crewai_hierarchical_orchestration(text, profile, file_path, deck_payload):
    """
    Use CrewAI hierarchical mode: each agent/task produces an independent output.
    At the end, merge all outputs into a single profile dictionary.
    """
    # Build all agents (ignore their Task wrappers for now)
    deck_agent, deck_task      = build_deck_agent(deck_payload)
    founder_agent, founder_task= build_founder_profiling_agent(deck_payload)
    market_agent, market_task  = build_market_sizing_agent(profile)
    tech_agent, tech_task      = build_technical_dd_agent(profile)
    bm_agent, bm_task          = build_business_model_chain_agent(profile, text, deck_payload)
    esg_agent, esg_task        = build_esg_chain_agent(profile, text, deck_payload)
    fin_agent, fin_task        = build_financial_analysis_agent(profile)
    comp_agent, comp_task      = build_competitive_intel_agent(profile)
    exit_agent, exit_task      = build_exit_chain_agent(profile, text, deck_payload)
    risk_agent, risk_task      = build_risk_assessment_agent(profile)
    followup_agent, followup_task = build_followup_chain_agent(profile, text, deck_payload)

    # Extract the initial context once
    deck_text = extract_text(file_path)

    # Define CrewAI tasks (independent, no depends_on, context embedded in description)
    tasks = [
        Task(description=(
            f"Extract fields from the following pitch deck text and return ONLY a valid JSON object with these keys: company_name, sector, founders, product_description, market_size, key_financials, competitors, business_model, esg_considerations, risks, exit_strategy. If a field is missing, use an empty string or null. Do NOT include any explanation, commentary, or markdown. The first character of your response must be '{{'.\n\nPitch deck text:\n{deck_text[:5000]}"
        ), agent=deck_agent, expected_output="Profile dict from deck agent", async_execution=False),
        Task(description=(
            f"Extract founder/team info from the following pitch deck text and return ONLY a valid JSON object with these keys: company_name, founders, key_team_members (as a list of dicts with name, role, background), founder_backgrounds, and any relevant team details. If a field is missing, use an empty string or null. Do NOT include any explanation, commentary, or markdown. The first character of your response must be '{{'.\n\nPitch deck text:\n{deck_text[:5000]}"
        ), agent=founder_agent, expected_output="Profile dict from founder profiling agent", async_execution=False),
        Task(description=(
            f"Extract market sizing from the following pitch deck text and return ONLY a valid JSON object with these keys: market_size, TAM, SAM, SOM, growth_rate, sources. If a field is missing, use an empty string or null. Do NOT include any explanation, commentary, or markdown. The first character of your response must be '{{'.\n\nPitch deck text:\n{deck_text[:5000]}"
        ), agent=market_agent, expected_output="Profile dict from market sizing agent", async_execution=False),
        Task(description=(
            f"Extract technical due diligence from the following pitch deck text and return ONLY a valid JSON object with these keys: technical_feasibility, performance, scalability, architecture, integration_complexity, security, regulatory_issues, implementation_complexity, risks, dependencies. If a field is missing, use an empty string or null. Do NOT include any explanation, commentary, or markdown. The first character of your response must be '{{'.\n\nPitch deck text:\n{deck_text[:5000]}"
        ), agent=tech_agent, expected_output="Profile dict from technical DD agent", async_execution=False),
        Task(description=(
            f"Extract business model from the following pitch deck text and return ONLY a valid JSON object with these keys: business_model, revenue_streams, pricing_strategy, scalability, sustainability. If a field is missing, use an empty string or null. Do NOT include any explanation, commentary, or markdown. The first character of your response must be '{{'.\n\nPitch deck text:\n{deck_text[:5000]}"
        ), agent=bm_agent, expected_output="Profile dict from business model agent", async_execution=False),
        Task(description=(
            f"Extract ESG analysis from the following pitch deck text and return ONLY a valid JSON object with these keys: esg_considerations, environmental, social, governance. If a field is missing, use an empty string or null. Do NOT include any explanation, commentary, or markdown. The first character of your response must be '{{'.\n\nPitch deck text:\n{deck_text[:5000]}"
        ), agent=esg_agent, expected_output="Profile dict from ESG agent", async_execution=False),
        Task(description=(
            f"Extract financials from the following pitch deck text and return ONLY a valid JSON object with these keys: key_financials, revenue, burn, runway, valuation, funding_sought, financial_summary. If a field is missing, use an empty string or null. Do NOT include any explanation, commentary, or markdown. The first character of your response must be '{{'.\n\nPitch deck text:\n{deck_text[:5000]}"
        ), agent=fin_agent, expected_output="Profile dict from financial analysis agent", async_execution=False),
        Task(description=(
            f"Extract competitive intel from the following pitch deck text and return ONLY a valid JSON object with these keys: competitors (as a list of dicts with name, website, funding, product_offering, traction, differentiator). If a field is missing, use an empty string or null. Do NOT include any explanation, commentary, or markdown. The first character of your response must be '{{'.\n\nPitch deck text:\n{deck_text[:5000]}"
        ), agent=comp_agent, expected_output="Profile dict from competitive intel agent", async_execution=False),
        Task(description=(
            f"Extract exit strategy from the following pitch deck text and return ONLY a valid JSON object with these keys: exit_strategy, likely_acquirers, IPO_potential, recommended_exit_timeline. If a field is missing, use an empty string or null. Do NOT include any explanation, commentary, or markdown. The first character of your response must be '{{'.\n\nPitch deck text:\n{deck_text[:5000]}"
        ), agent=exit_agent, expected_output="Profile dict from exit strategy agent", async_execution=False),
        Task(description=(
            f"Extract risk assessment from the following pitch deck text and return ONLY a valid JSON object with these keys: risk_flags (array), risk_score (float), risk_summary. If a field is missing, use an empty string or null. Do NOT include any explanation, commentary, or markdown. The first character of your response must be '{{'.\n\nPitch deck text:\n{deck_text[:5000]}"
        ), agent=risk_agent, expected_output="Profile dict from risk assessment agent", async_execution=False),
        Task(description=(
            f"Extract follow-up questions and next steps from the following pitch deck text and return ONLY a valid JSON object with these keys: follow_up_questions (array), next_steps. If a field is missing, use an empty string or null. Do NOT include any explanation, commentary, or markdown. The first character of your response must be '{{'.\n\nPitch deck text:\n{deck_text[:5000]}"
        ), agent=followup_agent, expected_output="Profile dict from follow-up agent", async_execution=False),
    ]

    # Create the Crew
    from langchain_openai import ChatOpenAI
    manager_llm = ChatOpenAI(model="gpt-4o", temperature=0)
    crew = Crew(
        agents=[deck_agent, founder_agent, market_agent, tech_agent, bm_agent, esg_agent, fin_agent, comp_agent, exit_agent, risk_agent, followup_agent],
        tasks=tasks,
        verbose=True,
        process=Process.hierarchical,
        manager_llm=manager_llm
    )

    print("Crew created, starting hierarchical analysis...")
    result = crew.kickoff()
    print("Analysis completed")

    # Merge all outputs into a single profile dict (flatten nested dicts)
    profile_dict = profile.model_dump()
    for i, task_output in enumerate(result.tasks_output):
        output = getattr(task_output, 'raw', task_output)
        if isinstance(output, dict):
            for k, v in output.items():
                profile_dict[k] = v
        elif isinstance(output, str):
            # Optionally handle string outputs if any agent returns plain text
            print(f"[WARNING] Agent output for task {i} is a string, not a dict: {output[:100]}")
    print("[DEBUG] Final merged profile before memo generation:", profile_dict)

    # After merging outputs, extract company_name robustly for filename
    company_name = None
    if 'company_name' in profile_dict and profile_dict['company_name']:
        company_name = profile_dict['company_name']
    elif 'name' in profile_dict and profile_dict['name']:
        company_name = profile_dict['name']
    else:
        for k in ['company_name', 'name']:
            for v in profile_dict.values():
                if isinstance(v, dict) and k in v and v[k]:
                    company_name = v[k]
                    break
            if company_name:
                break
    if not company_name:
        company_name = 'UnknownCompany'
    print(f"[DEBUG] Using company_name for filename: {company_name}")
    date_str = datetime.now().strftime("%Y%m%d")
    # Ensure company_name is always a string before using .replace()
    if not company_name or not isinstance(company_name, str):
        company_name = 'UnknownCompany'
    docx_filename = f"memo_{company_name.replace(' ', '_')}_{date_str}.docx"

    # Print the merged profile for debugging
    print("[DEBUG] Final merged profile:", profile_dict)

    # Try to generate and save the memo, handle errors gracefully
    try:
        # Replace this with your actual memo generation logic
        # For example, generate_word_memo(profile_dict, docx_filename)
        print(f"[INFO] Memo would be generated and saved as: {docx_filename}")
        # Uncomment and implement your actual memo generation here
        # generate_word_memo(profile_dict, docx_filename)
    except Exception as e:
        print(f"[ERROR] Failed to generate/save memo: {e}")

    return StartupProfile(**profile_dict)

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_file1> [<path_to_file2> ...]")
        sys.exit(1)

    file_paths = sys.argv[1:]
    for file_path in file_paths:
        print(f"Extracting text and structured data from: {file_path}")
        from core.download_utils import extract_text, extract_text_from_image
        from core.visual_utils import extract_images_from_pdf
        from core.schemas import StartupProfile
        import tempfile
        # --- Caching logic ---
        extracted = load_from_cache(file_path)
        if extracted is not None:
            print(f"[CACHE] Loaded extraction for {file_path}")
        else:
            extracted = extract_text(file_path, return_structured=True)
            save_to_cache(file_path, extracted)
            print(f"[CACHE] Saved extraction for {file_path}")
        text = extracted["text"]
        tables = extracted["tables"]
        figures = extracted["figures"]
        deck_payload = {
            "text": text,
            "tables": tables,
            "figures": figures,
            "file_path": file_path
        }
        profile = StartupProfile()
        profile.raw_text = text          # add these fields to the dataclass once
        profile.tables   = tables
        profile.figures  = figures
        profile.filepath = file_path
        
        # No visual_enrichment
        # --- CrewAI multi-agent orchestration and memo generation ---
        profile = run_crewai_hierarchical_orchestration(text, profile, file_path, deck_payload)          # Generate memo from enriched profile
        memo_text = format_memo(profile)
        with open("memo.txt", "w") as f:
            f.write(memo_text)
        # Save as Word and PDF
        company_name = clean_company_name(getattr(profile, 'name', 'unknown_company'))
        date_str = datetime.now().strftime("%Y%m%d")
        os.makedirs("out", exist_ok=True)
        # Debug print for company_name before filename generation
        print(f"[DEBUG] company_name before filename: {company_name} (type: {type(company_name)})")
        if not company_name or not isinstance(company_name, str):
            company_name = 'UnknownCompany'
        docx_filename = f"memo_{company_name.replace(' ', '_')}_{date_str}.docx"
        docx_path = os.path.join("out", docx_filename)
        save_memo_with_template(memo_text, profile, docx_path)
        convert_docx_to_pdf(docx_path)
        print(f"Memo generated and saved to {docx_path} and {docx_path.replace('.docx', '.pdf')}")


if __name__ == "__main__":
    main()
