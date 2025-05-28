from agents.deck_agent import run_crew
from pathlib import Path


def test_deck_agent():
    out = run_crew(str(Path("data/sample_deck.pdf")))
    assert '"name"' in out or "'name'" in out
