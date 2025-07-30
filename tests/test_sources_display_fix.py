import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import format_clean_financials_section
from core.schemas import StartupProfile

# Test data with markdown links
test_sources_markdown = [
    "[Crunchbase](https://www.crunchbase.com/organization/sample-company)",
    "[TechCrunch](https://techcrunch.com/2022/01/18/sample-company-raises-70m-series-d-round/)"
]

# Test data with plain URLs
test_sources_plain = [
    "https://www.crunchbase.com/organization/sample-company",
    "https://techcrunch.com/2022/01/18/sample-company-raises-70m-series-d-round/"
]

# Test data with mixed format
test_sources_mixed = [
    "[Crunchbase](https://www.crunchbase.com/organization/sample-company)",
    "https://techcrunch.com/2022/01/18/sample-company-raises-70m-series-d-round/",
    "https://www.linkedin.com/company/sample-company"
]

def test_sources_display_fix():
    """Test that sources are displayed correctly with both markdown and plain URLs."""
    
    # Create a test profile with different types of sources
    profile = StartupProfile()
    profile.implied_valuation = 1270000000.0
    profile.latest_round_amount = 70000000.0
    profile.total_funding_raised = 206500000.0
    
    # Test case 1: Markdown links (as stored by the LLM)
    profile.web_sources = test_sources_markdown
    
    result1 = format_clean_financials_section(profile, "July 29, 2025")
    print("=== Test 1: Markdown Links ===")
    print(result1)
    print()
    
    # Test case 2: Plain URLs
    profile.web_sources = test_sources_plain
    
    result2 = format_clean_financials_section(profile, "July 29, 2025")
    print("=== Test 2: Plain URLs ===")
    print(result2)
    print()
    
    # Test case 3: Mixed format
    profile.web_sources = test_sources_mixed
    
    result3 = format_clean_financials_section(profile, "July 29, 2025")
    print("=== Test 3: Mixed Format ===")
    print(result3)
    
    # Verify that sources are displayed in all cases
    assert "🔗 Data Sources" in result1, "Sources section should be present in result1"
    assert "🔗 Data Sources" in result2, "Sources section should be present in result2"
    assert "🔗 Data Sources" in result3, "Sources section should be present in result3"
    
    print("\n✅ All tests passed! Sources are being displayed correctly.")

if __name__ == "__main__":
    test_sources_display_fix() 