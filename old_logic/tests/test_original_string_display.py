#!/usr/bin/env python3
"""
Test for original string display in financial section
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schemas import StartupProfile

def test_original_string_display():
    """Test that financial values display as original readable strings"""
    print("=" * 60)
    print("TESTING ORIGINAL STRING DISPLAY")
    print("=" * 60)
    
    # Import the formatting function
    from main import format_clean_financials_section
    
    # Test case with original string values (like what LLM returns)
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.implied_valuation = "$1.27 billion"  # Original string from LLM
    profile.latest_round_amount = "$70 million"   # Original string from LLM
    profile.total_funding_raised = "$206.5 million"  # Original string from LLM
    profile.web_sources = [
        "https://www.crunchbase.com/organization/storedot",
        "https://en.wikipedia.org/wiki/StoreDot"
    ]
    
    # Format the financial section
    from datetime import datetime
    formatted_section = format_clean_financials_section(profile, datetime.now())
    
    print("Expected display (original strings):")
    print("• **Current Valuation**: $1.27 billion")
    print("• **Latest Funding Round**: $70 million")
    print("• **Total Funding Raised**: $206.5 million")
    print()
    
    print("Actual display:")
    print(formatted_section)
    print("-" * 40)
    
    # Check if the output contains the original strings
    if "$1.27 billion" in formatted_section:
        print("✅ SUCCESS: Original string '$1.27 billion' is displayed")
    else:
        print("❌ FAILED: Original string not found")
    
    if "$70 million" in formatted_section:
        print("✅ SUCCESS: Original string '$70 million' is displayed")
    else:
        print("❌ FAILED: Original string not found")
    
    if "$206.5 million" in formatted_section:
        print("✅ SUCCESS: Original string '$206.5 million' is displayed")
    else:
        print("❌ FAILED: Original string not found")

if __name__ == "__main__":
    test_original_string_display() 