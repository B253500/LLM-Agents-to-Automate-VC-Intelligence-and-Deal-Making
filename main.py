import sys
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from memo_api.routes import upload, memo, health, pdf_memo
from chains.pitch_deck_chain import run_pitch_deck_chain
from chains.technical_dd_chain import run_technical_dd_chain
from chains.founder_profiling_chain import run_founder_profiling_chain
from chains.market_sizing_chain import run_market_sizing_chain
from chains.financial_analysis_chain import run_financial_analysis_chain
from chains.competitive_intel_chain import run_competitive_intel_chain
from chains.risk_assessment_chain import run_risk_assessment_chain
from core.schemas import StartupProfile
from fpdf import FPDF

# Load environment variables
load_dotenv()

app = FastAPI(title="VC Memo API")

# Include API routes
app.include_router(upload.router, prefix="/api")
app.include_router(memo.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(pdf_memo.router, prefix="/api")


def run_all_sequential(pdf_path: str) -> StartupProfile:
    profile = run_pitch_deck_chain(pdf_path)
    profile = run_technical_dd_chain(profile)
    profile = run_founder_profiling_chain(profile)
    profile = run_market_sizing_chain(profile)
    profile = run_financial_analysis_chain(profile)
    profile = run_competitive_intel_chain(profile)
    profile = run_risk_assessment_chain(profile)
    return profile


def format_memo(profile: StartupProfile) -> str:
    """Format the investment memo with improved data handling."""
    # Format market info
    market_info = profile.market_info or {}
    tam = market_info.get("TAM", "Unknown")
    sam = market_info.get("SAM", "Unknown")
    som = market_info.get("SOM", "Unknown")
    growth_rate = market_info.get("growth_rate", "Unknown")
    key_drivers = market_info.get("key_drivers", [])
    barriers = market_info.get("barriers", [])

    # Format competitor info
    competitor_info = profile.competitor_info or {}
    competitors = competitor_info.get("competitors", [])

    # Format company info
    company_info = {
        "name": profile.name or "Unknown",
        "founder": profile.founder_name or "Unknown",
        "sector": profile.sector or "Unknown",
        "website": profile.website or "Unknown",
        "funding_stage": profile.funding_stage or "Unknown",
        "funding_amount": profile.funding_amount or "Unknown",
        "tech_maturity": profile.tech_maturity or "Unknown",
        "moat_strength": profile.moat_strength or "Unknown",
    }

    # Build the memo
    memo = f"""
Investment Memo
===============

**Name:** {company_info['name']}
**Founder:** {company_info['founder']}
**Sector:** {company_info['sector']}
**Website:** {company_info['website']}
**Funding Stage:** {company_info['funding_stage']}
**Funding Amount:** {company_info['funding_amount']}

---

Technical Due-Diligence
-----------------------
Maturity: {company_info['tech_maturity']}
Moat: {company_info['moat_strength']}

Founder Fit
-----------
Score: {profile.founder_fit_score or 0.0}
Prior exits: {profile.prior_exits or 0}

Market Analysis
--------------
TAM: {tam}
SAM: {sam}
SOM: {som}
Growth Rate: {growth_rate}

Key Market Drivers:
{chr(10).join(f"- {driver}" for driver in key_drivers) if key_drivers else "- None identified"}

Market Barriers:
{chr(10).join(f"- {barrier}" for barrier in barriers) if barriers else "- None identified"}

Financials
----------
Burn 12m: ${profile.cash_burn_12m or 0.0:,.2f}M
Runway: {profile.runway_months or 0.0} months
Implied valuation: ${profile.implied_valuation or 0.0:,.2f}M

Competition
-----------
"""

    # Add competitor information
    if competitors:
        for comp in competitors:
            memo += f"""
{comp.get('name', 'Unknown Competitor')}:
- Position: {comp.get('position', 'Unknown')}
- Advantages: {', '.join(comp.get('advantages', ['None identified']))}
- Moats: {', '.join(comp.get('moats', ['None identified']))}
- Market Share: {comp.get('market_share', 'Unknown')}
- Growth Rate: {comp.get('growth_rate', 'Unknown')}
- Technology: {comp.get('technology', 'Unknown')}
- Pricing: {comp.get('pricing', 'Unknown')}
- GTM: {comp.get('gtm', 'Unknown')}
"""
    else:
        memo += "No competitor information available\n"

    # Add risk assessment
    memo += f"""
Risk Assessment
---------------
Score: {profile.risk_score or 0.0}
Flags: {', '.join(profile.risk_flags) if profile.risk_flags else 'None identified'}
"""

    return memo


def save_memo_as_pdf(text: str, output_path: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Use Helvetica instead of Arial
    pdf.set_font("Helvetica", size=12)

    # Set margins
    pdf.set_margins(20, 20, 20)

    # Process text line by line
    for line in text.split("\n"):
        # Handle markdown-style headers
        if line.startswith("="):
            pdf.set_font("Helvetica", "B", 16)
            pdf.ln(10)
            pdf.cell(0, 10, line.strip("=").strip(), ln=True)
            pdf.set_font("Helvetica", size=12)
        elif line.startswith("-"):
            pdf.set_font("Helvetica", "B", 14)
            pdf.ln(5)
            pdf.cell(0, 10, line.strip("-").strip(), ln=True)
            pdf.set_font("Helvetica", size=12)
        elif line.startswith("**"):
            # Handle bold text
            parts = line.split("**")
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Regular text
                    pdf.set_font("Helvetica", size=12)
                else:  # Bold text
                    pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 10, part, ln=True)
        else:
            # Regular text
            pdf.set_font("Helvetica", size=12)
            # Split long lines to fit page width
            words = line.split()
            current_line = ""
            for word in words:
                if pdf.get_string_width(current_line + " " + word) < pdf.w - 40:
                    current_line += " " + word if current_line else word
                else:
                    pdf.cell(0, 10, current_line, ln=True)
                    current_line = word
            if current_line:
                pdf.cell(0, 10, current_line, ln=True)

    pdf.output(output_path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    profile = run_all_sequential(pdf_path)
    memo_text = format_memo(profile)
    print(memo_text)

    output_dir = "out"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "memo.pdf")
    save_memo_as_pdf(memo_text, output_path)
    print(f"\nPDF memo saved to {output_path}")
