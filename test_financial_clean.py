#!/usr/bin/env python3
"""
Test script to verify the clean financial analysis output
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.financial_analysis_chain import run_financial_analysis_chain
from core.schemas import StartupProfile

def test_clean_financial_analysis():
    """Test the clean financial analysis output"""
    
    print("=" * 80)
    print("CLEAN FINANCIAL ANALYSIS TEST")
    print("=" * 80)
    
    # Create a test profile
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Run the financial analysis chain
    print("Running financial analysis chain...")
    updated_profile = run_financial_analysis_chain(profile)
    
    print("\nFinancial Analysis Results:")
    print("-" * 50)
    
    # Check key financial fields
    key_fields = [
        'implied_valuation', 'latest_round_amount', 'total_funding_raised',
        'revenue', 'web_sources'
    ]
    
    for field in key_fields:
        value = getattr(updated_profile, field, None)
        if value:
            print(f"✅ {field}: {value}")
        else:
            print(f"❌ {field}: NOT POPULATED")
    
    print("\n" + "=" * 50)
    print("CLEAN FINANCIAL SECTION OUTPUT")
    print("=" * 50)
    
    # Test the clean financial section formatting
    from main import format_clean_financials_section
    from datetime import datetime
    
    current_date = datetime.now().strftime('%B %d, %Y')
    financial_section = format_clean_financials_section(updated_profile, current_date)
    
    print(financial_section)
    
    print("\n" + "=" * 50)
    print("VERIFICATION")
    print("=" * 50)
    
    # Check if the output contains the key elements
    key_phrases = ["Current Valuation", "Latest Funding Round", "Total Funding Raised", "Data Sources"]
    
    found_phrases = []
    for phrase in key_phrases:
        if phrase in financial_section:
            found_phrases.append(phrase)
    
    print(f"✅ Found {len(found_phrases)} key financial phrases: {found_phrases}")
    
    if len(found_phrases) >= 2:
        print("✅ Financial section contains key financial information")
    else:
        print("❌ Financial section may be missing key information")
    
    print(f"\nFinancial section length: {len(financial_section)} characters")
    print("✅ This is what will appear in the memo when you run main.py")

if __name__ == "__main__":
    test_clean_financial_analysis() 