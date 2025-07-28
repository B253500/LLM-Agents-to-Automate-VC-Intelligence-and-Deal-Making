#!/usr/bin/env python3
"""
Simple test for financial analysis chain
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.financial_analysis_chain import run_financial_analysis_chain
from core.schemas import StartupProfile

def test_financial_chain():
    """Test the financial analysis chain"""
    
    print("=" * 80)
    print("FINANCIAL ANALYSIS CHAIN TEST")
    print("=" * 80)
    
    # Create a test profile
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    print("Running financial analysis chain...")
    
    try:
        # Run the financial analysis chain
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
        
        # Check web sources
        web_sources = getattr(updated_profile, 'web_sources', [])
        if web_sources:
            print(f"\n✅ Web sources found: {len(web_sources)}")
            for source in web_sources[:3]:
                print(f"  • {source}")
        
        print("\n✅ Financial analysis chain completed successfully")
        
    except Exception as e:
        print(f"❌ Financial analysis chain failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_financial_chain() 