"""
End-to-end orchestration
Usage:
    python main.py data/sample_deck.pdf
"""

import sys
from textwrap import indent  # noqa: F401

from core.schemas import StartupProfile
from agents.deck_agent import run_crew as run_pitch_deck_crew
from agents.technical_dd_agent import build_technical_dd_agent
from agents.founder_profiling_agent import build_founder_profiling_agent
from agents.market_sizing_agent import build_market_sizing_agent
from agents.financial_analysis_agent import build_financial_analysis_agent
from agents.competitive_intel_agent import build_competitive_intel_agent
from agents.risk_assessment_agent import build_risk_assessment_agent

from crewai import Crew


def run_all(pdf_path: str) -> StartupProfile:
    # 0 ───────── initial extraction (returns JSON string)
    profile = StartupProfile.model_validate_json(run_pitch_deck_crew(pdf_path))

    # 1-6 ─────── build all specialist agents for the *same* profile object
    builders = [
        build_technical_dd_agent,
        build_founder_profiling_agent,
        build_market_sizing_agent,
        build_financial_analysis_agent,
        build_competitive_intel_agent,
        build_risk_assessment_agent,
    ]

    agents, tasks = zip(*(b(profile) for b in builders))

    # Wire them after the pitch-deck agent
    crew = Crew(
        agents=list(agents),
        tasks=list(tasks),
        manager_llm=None,  # no need for a separate manager agent
    )
    crew.kickoff()  # updates profile in place
    return profile


def profile_to_markdown(p: StartupProfile) -> str:
    md = f"# Investment Memo – {p.name}\n\n"
    md += f"**Sector:** {p.sector or 'N/A'}  \n"
    md += f"**Website:** {p.website or 'N/A'}  \n"
    md += f"**Funding Stage:** {p.funding_stage or 'N/A'}  \n"
    md += "\n---\n\n"

    md += "## Technical Due-Diligence\n"
    md += f"*Maturity:* **{p.tech_maturity}**  \n"
    md += f"*Moat:* {p.moat_strength}\n\n"

    md += "## Founder Fit\n"
    md += f"*Score:* {p.founder_fit_score}  \n"
    md += f"*Prior exits:* {p.prior_exits}\n\n"

    md += "## Market Size (USD m)\n"
    md += f"TAM {p.TAM} • SAM {p.SAM} • SOM {p.SOM}\n\n"

    md += "## Financials\n"
    md += f"Burn 12m: {p.cash_burn_12m}  \n"
    md += f"Runway: {p.runway_months} months  \n"
    md += f"Implied valuation: {p.implied_valuation}\n\n"

    md += "## Competition\n"
    for c in p.top_competitors:
        md += f"▪ **{c.name}** – {c.differentiator}\n"
    if not p.top_competitors:
        md += "No direct competitors listed.\n"
    md += "\n"

    md += "## Risk Assessment\n"
    md += f"*Score:* {p.risk_score}  \n"
    md += "Flags: " + ", ".join(p.risk_flags) + "\n"

    return md


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main.py <pitch_deck.pdf>")
        sys.exit(1)

    profile = run_all(sys.argv[1])
    print(profile_to_markdown(profile))
