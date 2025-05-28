from pathlib import Path
from agents.deck_agent import run_crew


def test_deck_agent():
    pdf = Path("data/sample_deck.pdf")
    assert pdf.exists(), "sample_deck.pdf is missing"

    out = run_crew(str(pdf))
    assert "name" in out or "CompanyName" in out or "company_name" in out
