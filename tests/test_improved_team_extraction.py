#!/usr/bin/env python3
"""
Test the improved team extraction with 3-step approach
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.team_chain import enrich_executives_with_perplexity

def test_improved_team_extraction():
    """Test the improved team extraction with cleaner results"""
    print("=== Testing Improved Team Extraction ===")
    
    test_companies = [
        "Dropbox",
        "Lunchbox"
    ]
    
    for company in test_companies:
        print(f"\n--- Testing: {company} ---")
        
        try:
            # Test with empty existing executives
            existing_execs = []
            result = enrich_executives_with_perplexity(company, existing_execs)
            
            print(f"Found {len(result)} executives:")
            for i, exec in enumerate(result):
                print(f"  {i+1}. {exec.get('name', 'Unknown')} - {exec.get('role', 'Unknown')}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_improved_team_extraction() 