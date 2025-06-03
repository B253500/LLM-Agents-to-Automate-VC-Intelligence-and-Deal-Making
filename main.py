import sys
import pdfplumber
import os

from chains.pitch_deck_chain import run_pitch_deck_chain
from chains.technical_dd_chain import run_technical_dd_chain
from chains.founder_profiling_chain import run_founder_profiling_chain
from chains.market_sizing_chain import run_market_sizing_chain
from chains.financial_analysis_chain import run_financial_analysis_chain
from chains.competitive_intel_chain import run_competitive_intel_chain
from chains.risk_assessment_chain import run_risk_assessment_chain
from core.schemas import StartupProfile
from fpdf import FPDF
from fastapi import FastAPI
from app.routes import upload, memo, health


app = FastAPI(title="VC Memo API")

app.include_router(upload.router, prefix="/api")
app.include_router(memo.router, prefix="/api")
app.include_router(health.router, prefix="/api")


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
    return (
        f"""
Investment Memo
===============

**Name:** {profile.name or 'N/A'}
**Founder:** {profile.founder_name or 'N/A'}
**Sector:** {profile.sector or 'N/A'}
**Website:** {profile.website or 'N/A'}
**Funding Stage:** {profile.funding_stage or 'N/A'}

---

Technical Due-Diligence
-----------------------
Maturity: {profile.tech_maturity or 'unknown'}
Moat: {profile.moat_strength or 'unknown'}

Founder Fit
-----------
Score: {profile.founder_fit_score or 'N/A'}
Prior exits: {profile.prior_exits or 0}

Market Size (USD m)
-------------------
TAM: {profile.TAM or 0.0}
SAM: {profile.SAM or 0.0}
SOM: {profile.SOM or 0.0}

Financials
----------
Burn 12m: {profile.cash_burn_12m or 0.0}
Runway: {profile.runway_months or 0.0} months
Implied valuation: {profile.implied_valuation or 0.0}

Competition
-----------
"""
        + "\n".join(
            f"- {c.name}: {c.differentiator or 'No differentiator provided'}"
            for c in profile.top_competitors
        )
        + f"""

Risk Assessment
---------------
Score: {profile.risk_score or 'N/A'}
Flags: {', '.join(profile.risk_flags) if profile.risk_flags else 'None'}
"""
    )


def save_memo_as_pdf(text: str, output_path: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    for line in text.split("\n"):
        pdf.multi_cell(0, 10, line)

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
