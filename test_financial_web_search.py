#!/usr/bin/env python3
"""
Test script to check web search functionality for financial data
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.financial_analysis_chain import web_search_financial_context

def test_web_search_financial():
    """Test the web search functionality for financial data"""
    
    print("=" * 80)
    print("WEB SEARCH FINANCIAL TEST")
    print("=" * 80)
    
    # Test with StoreDot
    company_name = "StoreDot"
    print(f"Searching for financial data for: {company_name}")
    
    try:
        web_data = web_search_financial_context(company_name)
        
        if web_data:
            print("✅ Web search successful")
            print(f"Data length: {len(web_data)} characters")
            print("\nWeb search data preview:")
            print("-" * 50)
            print(web_data[:500] + "..." if len(web_data) > 500 else web_data)
        else:
            print("❌ No web data found")
            
    except Exception as e:
        print(f"❌ Web search failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_web_search_financial() 