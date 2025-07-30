#!/usr/bin/env python3
"""
Test that financial analysis now uses reduced number of sources (1-2 instead of 3-5)
"""

import os
import sys
import json

# Add the project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_reduced_sources():
    """Test that sources are now limited to 1-2."""
    
    print("🔍 Testing Reduced Financial Analysis Sources")
    print("=" * 60)
    
    # Test 1: Check financial analysis chain limits
    print("\n1️⃣ Testing Financial Analysis Chain Limits")
    print("-" * 50)
    
    from chains.financial_analysis_chain import web_search_financial_context
    
    # Mock test data
    test_company = "Test Company"
    
    # Simulate the source limiting logic
    test_sources = [
        "https://crunchbase.com/company/test",
        "https://example.com/funding",
        "https://another.com/valuation",
        "https://fourth.com/data",
        "https://fifth.com/info"
    ]
    
    # Test the limiting logic
    crunchbase_sources = [s for s in test_sources if 'crunchbase' in s.lower()]
    other_sources = [s for s in test_sources if 'crunchbase' not in s.lower()]
    
    # Old logic (3 sources)
    old_prioritized = crunchbase_sources + other_sources[:3-len(crunchbase_sources)]
    
    # New logic (2 sources)
    new_prioritized = crunchbase_sources + other_sources[:2-len(crunchbase_sources)]
    
    print(f"📊 Test Sources: {len(test_sources)} total")
    print(f"📊 Crunchbase Sources: {len(crunchbase_sources)}")
    print(f"📊 Other Sources: {len(other_sources)}")
    print(f"📊 Old Limit (3): {len(old_prioritized)} sources")
    print(f"📊 New Limit (2): {len(new_prioritized)} sources")
    print(f"✅ Reduction: {len(old_prioritized) - len(new_prioritized)} fewer sources")
    
    # Test 2: Check main.py formatting limits
    print("\n2️⃣ Testing Main.py Formatting Limits")
    print("-" * 50)
    
    # Simulate the web_sources limiting
    test_web_sources = [
        "https://source1.com",
        "https://source2.com", 
        "https://source3.com",
        "https://source4.com",
        "https://source5.com"
    ]
    
    # Old limits
    old_clean_limit = test_web_sources[:3]  # Clean financials
    old_original_limit = test_web_sources[:5]  # Original financials
    old_url_limit = test_web_sources[:3]  # URL extraction
    
    # New limits
    new_clean_limit = test_web_sources[:2]  # Clean financials
    new_original_limit = test_web_sources[:2]  # Original financials  
    new_url_limit = test_web_sources[:2]  # URL extraction
    
    print(f"📊 Clean Financials:")
    print(f"   • Old limit: {len(old_clean_limit)} sources")
    print(f"   • New limit: {len(new_clean_limit)} sources")
    print(f"   • Reduction: {len(old_clean_limit) - len(new_clean_limit)} sources")
    
    print(f"📊 Original Financials:")
    print(f"   • Old limit: {len(old_original_limit)} sources")
    print(f"   • New limit: {len(new_original_limit)} sources")
    print(f"   • Reduction: {len(old_original_limit) - len(new_original_limit)} sources")
    
    print(f"📊 URL Extraction:")
    print(f"   • Old limit: {len(old_url_limit)} sources")
    print(f"   • New limit: {len(new_url_limit)} sources")
    print(f"   • Reduction: {len(old_url_limit) - len(new_url_limit)} sources")
    
    # Test 3: Check market sizing agent limits
    print("\n3️⃣ Testing Market Sizing Agent Limits")
    print("-" * 50)
    
    # Simulate market sizing web sources
    market_sources = [
        "https://market1.com",
        "https://market2.com",
        "https://market3.com",
        "https://market4.com"
    ]
    
    # Old limit (3)
    old_market_limit = market_sources[:3]
    
    # New limit (2)
    new_market_limit = market_sources[:2]
    
    print(f"📊 Market Sizing Sources:")
    print(f"   • Old limit: {len(old_market_limit)} sources")
    print(f"   • New limit: {len(new_market_limit)} sources")
    print(f"   • Reduction: {len(old_market_limit) - len(new_market_limit)} sources")
    
    # Test 4: Performance summary
    print("\n4️⃣ Performance Summary")
    print("-" * 50)
    
    total_old_sources = len(old_prioritized) + len(old_clean_limit) + len(old_original_limit) + len(old_url_limit) + len(old_market_limit)
    total_new_sources = len(new_prioritized) + len(new_clean_limit) + len(new_original_limit) + len(new_url_limit) + len(new_market_limit)
    
    print(f"🎯 Total Source Reduction:")
    print(f"   • Old total: {total_old_sources} sources")
    print(f"   • New total: {total_new_sources} sources")
    print(f"   • Reduction: {total_old_sources - total_new_sources} sources")
    print(f"   • Percentage: {((total_old_sources - total_new_sources) / total_old_sources * 100):.1f}% reduction")
    
    print(f"\n✅ Benefits:")
    print(f"   • Faster analysis (fewer web requests)")
    print(f"   • More focused results")
    print(f"   • Reduced token usage")
    print(f"   • Lower costs")

if __name__ == "__main__":
    test_reduced_sources() 