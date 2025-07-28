from core.schemas import StartupProfile
from core.vector_store import add_doc
from chains.market_sizing_chain import run_market_sizing_chain
from agents.market_sizing_agent import generate_market_size_section

from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage
import pytest
import re


@pytest.fixture(autouse=True)
def _stub_llm(monkeypatch):
    def fake_invoke(self, prompt):
        return AIMessage(content='{"TAM":5000,"SAM":800,"SOM":50}')

    monkeypatch.setattr(ChatOpenAI, "invoke", fake_invoke, raising=True)


def test_market_sizing():
    prof = StartupProfile(startup_id="market1", name="Beta")
    add_doc("market1", "We address a rapidly growing $5 billion global market.")

    prof = run_market_sizing_chain(prof)

    assert prof.TAM == 5000
    assert prof.SAM == 800
    assert prof.SOM == 50


def test_url_preservation_in_market_section():
    """Test that URLs are properly preserved in market section generation"""
    # Create a test profile with URLs that could be problematic
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Add test URLs that should be preserved
    test_urls = [
        "https://www.researchandmarkets.com/reports/5785723/battery-technology-market-report",
        "https://www.precedenceresearch.com/battery-technology-market",
        "https://www.grandviewresearch.com/industry-analysis/battery-technology-market",
        "https://www.marketsandmarkets.com/Market-Reports/battery-technology-market-123456.html",
        "https://www.statista.com/outlook/energy/battery-technology-market",
        "https://www.ibisworld.com/united-states/market-research-reports/battery-technology-industry/"
    ]
    
    # Mock the market_size_sources to include our test URLs
    profile.market_size_sources = test_urls
    
    # Generate market section
    market_section = generate_market_size_section(profile)
    
    # Extract URLs from the generated section
    url_pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'
    found_urls = re.findall(url_pattern, market_section)
    
    # Check that we found URLs
    assert len(found_urls) > 0, "No URLs found in market section"
    
    # Check if any URLs were truncated (end with just a period)
    truncated_urls = []
    for text, url in found_urls:
        if url.endswith('.') and not any(url.endswith(ext) for ext in ['.com', '.org', '.net', '.co', '.io']):
            truncated_urls.append((text, url))
    
    # Assert that no URLs were truncated
    assert len(truncated_urls) == 0, f"Found {len(truncated_urls)} truncated URLs: {truncated_urls}"
    
    # Check that URLs contain expected domains
    found_domains = [url.split('/')[2] for text, url in found_urls]
    expected_domains = ['www.researchandmarkets.com', 'www.precedenceresearch.com', 
                       'www.grandviewresearch.com', 'www.marketsandmarkets.com',
                       'www.statista.com', 'www.ibisworld.com']
    
    # At least some of the expected domains should be found
    found_expected = any(domain in found_domains for domain in expected_domains)
    assert found_expected, f"Expected domains not found. Found: {found_domains}"
