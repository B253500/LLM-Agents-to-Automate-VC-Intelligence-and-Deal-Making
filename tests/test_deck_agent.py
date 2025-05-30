import json
from pathlib import Path
from agents.deck_agent import run_crew


def test_deck_agent():
    pdf = Path("data/sample_deck.pdf")
    assert pdf.exists(), "sample_deck.pdf is missing"

    out = run_crew(str(pdf))
    result = json.loads(out)
    profile = result.get("StartupProfile", result)  # Fallback if not wrapped

    # Normalise keys: lowercased and spaces removed
    keys_normalised = {k.lower().replace(" ", "") for k in profile.keys()}
    expected_keys = {"name", "companyname", "company_name", "startupname"}

    assert keys_normalised & expected_keys, f"Profile keys: {profile.keys()}"
