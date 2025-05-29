"""
End-to-end orchestration – sequential (CrewAI 0.121.x compatible)
Usage:
    python main.py data/sample_deck.pdf
"""

import re
import sys
from pathlib import Path
from textwrap import indent  # noqa: F401

from crewai import Crew
from core.schemas import StartupProfile

# agent imports
from agents.deck_agent import run_crew as run_pitch_deck_crew
from agents.technical_dd_agent import build_technical_dd_agent
from agents.founder_profiling_agent import build_founder_profiling_agent
from agents.market_sizing_agent import build_market_sizing_agent
from agents.financial_analysis_agent import build_financial_analysis_agent
from agents.competitive_intel_agent import build_competitive_intel_agent
from agents.risk_assessment_agent import build_risk_assessment_agent
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas


# ───────────────────────── helpers ──────────────────────────
def _extract_json(text: str) -> str:
    """Return the first {...} block, stripping ```json fences if present."""
    if text.startswith("```"):
        text = re.sub(r"^```[^\n]*\n", "", text, count=1)
        text = text.rsplit("```", 1)[0]
    first, last = text.find("{"), text.rfind("}")
    if first == -1 or last == -1 or last < first:
        raise ValueError("No JSON object found in LLM response")
    return text[first : last + 1]


# ───────────────────── orchestration ───────────────────────
def run_all_sequential(pdf_path: str) -> StartupProfile:
    if not Path(pdf_path).is_file():
        raise FileNotFoundError(pdf_path)

    # 0. baseline extraction
    raw_json = run_pitch_deck_crew(pdf_path)
    profile = StartupProfile.model_validate_json(_extract_json(raw_json))

    # 1-6. specialist agents
    builders = [
        build_technical_dd_agent,
        build_founder_profiling_agent,
        build_market_sizing_agent,
        build_financial_analysis_agent,
        build_competitive_intel_agent,
        build_risk_assessment_agent,
    ]
    agents, tasks = zip(*(b(profile) for b in builders))

    Crew(agents=list(agents), tasks=list(tasks), manager_llm=None).kickoff()
    return profile


def _memo_to_pdf(text: str, out_path: str):
    """Very simple PDF writer: 1 column, wraps long lines."""
    c = canvas.Canvas(out_path, pagesize=LETTER)
    width, height = LETTER
    y = height - 72  # 1-inch margin
    for line in text.splitlines():
        if not line:  # blank line
            y -= 14
            continue
        # rough word-wrap at 90 chars
        while len(line) > 90:
            c.drawString(72, y, line[:90])
            line = line[90:]
            y -= 14
        c.drawString(72, y, line)
        y -= 14
        if y < 72:  # new page
            c.showPage()
            y = height - 72
    c.save()


# ─────────────── markdown output helper (unchanged) ─────────
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
    if p.top_competitors:
        for c in p.top_competitors:
            md += f"▪ **{c.name}** – {c.differentiator}\n"
    else:
        md += "No direct competitors listed.\n"
    md += "\n"

    md += "## Risk Assessment\n"
    md += f"*Score:* {p.risk_score}  \n"
    md += "Flags: " + ", ".join(p.risk_flags) + "\n"
    return md


# ─────────────────────────── CLI ────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print("Usage: python main.py <pitch.pdf> [out.{md|pdf}]")
        sys.exit(1)

    profile = run_all_sequential(sys.argv[1])
    memo_md = profile_to_markdown(profile)

    if len(sys.argv) == 3:
        out = sys.argv[2]
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        if out.lower().endswith(".pdf"):
            _memo_to_pdf(memo_md, out)
        else:  # default to markdown
            Path(out).write_text(memo_md, encoding="utf-8")
        print(f"Memo written to {out}")
    else:
        print(memo_md)
