#!/usr/bin/env python3
"""
Test for string-based financial parsing
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schemas import StartupProfile

def test_string_financial_formatting():
    """Test that financial formatting handles both numeric and string values"""
    print("=" * 60)
    print("TESTING STRING-BASED FINANCIAL FORMATTING")
    print("=" * 60)
    
    # Import the formatting function
    from main import format_clean_financials_section
    
    # Test cases with different value types
    test_cases = [
        {
            "name": "Numeric values",
            "implied_valuation": 1500000000,
            "latest_round_amount": 70000000,
            "total_funding_raised": 206500000
        },
        {
            "name": "String values",
            "implied_valuation": "$1.5 billion",
            "latest_round_amount": "$70 million",
            "total_funding_raised": "$206.5 million"
        },
        {
            "name": "Mixed values",
            "implied_valuation": "$1.5 billion",
            "latest_round_amount": 70000000,
            "total_funding_raised": "$206.5 million"
        },
        {
            "name": "Currency strings",
            "implied_valuation": "1.5 billion USD",
            "latest_round_amount": "70 million EUR",
            "total_funding_raised": "206.5 million USD"
        },
        {
            "name": "Range values",
            "implied_valuation": "$70-80 million",
            "latest_round_amount": "50-60 million",
            "total_funding_raised": "200-250 million"
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
        profile.web_sources = ["https://example.com/source1", "https://example.com/source2"]
        
        # Format the financial section
        from datetime import datetime
        formatted_section = format_clean_financials_section(profile, datetime.now())
        
        print("Formatted output:")
        print(formatted_section)
        print("-" * 40)

if __name__ == "__main__":
    test_string_financial_formatting() 