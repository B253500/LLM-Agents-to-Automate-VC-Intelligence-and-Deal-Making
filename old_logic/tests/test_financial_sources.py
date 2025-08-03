#!/usr/bin/env python3
"""
Test for financial sources display
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schemas import StartupProfile

def test_financial_sources_display():
    """Test that financial sources are displayed correctly"""
    print("=" * 60)
    print("TESTING FINANCIAL SOURCES DISPLAY")
    print("=" * 60)
    
    # Import the formatting function
    from main import format_clean_financials_section
    
    # Test cases with different source configurations
    test_cases = [
        {
            "name": "With Crunchbase and Wikipedia sources",
            "implied_valuation": "$1.5 billion",
            "latest_round_amount": "$70 million", 
            "total_funding_raised": "$206.5 million",
            "web_sources": [
                "https://www.crunchbase.com/organization/storedot",
                "https://en.wikipedia.org/wiki/StoreDot",
                "https://www.pitchbook.com/profiles/company/12345"
            ]
        },
        {
            "name": "With multiple sources",
            "implied_valuation": "1.5 billion USD",
            "latest_round_amount": "70 million EUR",
            "total_funding_raised": "206.5 million USD",
            "web_sources": [
                "https://www.crunchbase.com/organization/company",
                "https://www.pitchbook.com/profiles/company/67890",
                "https://www.linkedin.com/company/company-name",
                "https://www.techcrunch.com/company-article",
                "https://www.forbes.com/company-profile"
            ]
        },
        {
            "name": "No sources",
            "implied_valuation": "$1.5 billion",
            "latest_round_amount": "$70 million",
            "total_funding_raised": "$206.5 million",
            "web_sources": []
        },
        {
            "name": "Invalid sources (should be filtered out)",
            "implied_valuation": "1.5 billion USD",
            "latest_round_amount": "70 million EUR", 
            "total_funding_raised": "206.5 million USD",
            "web_sources": [
                "not-a-url",
                "ftp://invalid-protocol.com",
                "https://www.crunchbase.com/organization/valid",
                "another-invalid-url"
            ]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_case['name']} ---")
        
        # Create a profile with the test data
        profile = StartupProfile()
        profile.name = "Test Company"
        profile.implied_valuation = test_case.get("implied_valuation")
        profile.latest_round_amount = test_case.get("latest_round_amount")
        profile.total_funding_raised = test_case.get("total_funding_raised")
        profile.web_sources = test_case.get("web_sources", [])
        
        # Format the financial section
        from datetime import datetime
        formatted_section = format_clean_financials_section(profile, datetime.now())
        
        print("Formatted output:")
        print(formatted_section)
        print("-" * 40)

if __name__ == "__main__":
    test_financial_sources_display() 