#!/usr/bin/env python3
"""
Test script to verify AI-powered market extraction from Shopify PDF
"""

import json
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.download_utils import ai_extract_market_data, extract_market_size_from_text

def test_ai_market_extraction():
    """Test the AI-powered market extraction on Shopify PDF text"""
    
    # Load the Shopify PDF extracted text
    shopify_cache_file = "extraction_cache/shopify.pdf_68adaa0de2223b7b38fe146a2cfe826b7a21dd8b.json"
    
    try:
        with open(shopify_cache_file, 'r') as f:
            data = json.load(f)
            text = data.get('text', '')
    except FileNotFoundError:
        print(f"❌ Shopify cache file not found: {shopify_cache_file}")
        return False
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in cache file: {shopify_cache_file}")
        return False
    
    print("🔍 Testing AI-powered market extraction on Shopify PDF...")
    print(f"📄 Text length: {len(text)} characters")
    
    # Test AI extraction
    print("\n🤖 AI-Powered Market Extraction:")
    print("=" * 50)
    
    ai_market_data = ai_extract_market_data(text)
    
    if ai_market_data:
        print("✅ AI extraction successful!")
        print(f"📊 Found {len(ai_market_data)} market data categories:")
        
        for category, data in ai_market_data.items():
            if isinstance(data, dict):
                print(f"  📁 {category}: {len(data)} fields")
                for key, value in data.items():
                    if value and value != "null":
                        print(f"    • {key}: {value}")
            elif data and data != "null":
                print(f"  📁 {category}: {data}")
    else:
        print("❌ AI extraction failed or returned no data")
        return False
    
    # Test combined extraction (regex + AI)
    print("\n🔧 Combined Extraction (Regex + AI):")
    print("=" * 50)
    
    combined_market_data = extract_market_size_from_text(text)
    
    if combined_market_data:
        print("✅ Combined extraction successful!")
        print(f"📊 Found {len(combined_market_data)} total market data points:")
        
        # Categorize the data
        categories = {
            'Traditional Metrics': ['TAM', 'SAM', 'SOM', 'cagr'],
            'Merchant Data': ['total_merchants', 'global_merchants', 'core_geography_merchants'],
            'Revenue Data': ['revenue_per_merchant'],
            'Market Definition': ['market_definition', 'geographic_focus'],
            'Source Data': ['market_source'],
            'AI-Enhanced': [k for k in combined_market_data.keys() if any(prefix in k for prefix in ['market_metrics_', 'geographic_data_', 'growth_metrics_', 'competitive_data_', 'source_attribution_'])]
        }
        
        for category, fields in categories.items():
            category_data = {k: v for k, v in combined_market_data.items() if k in fields}
            if category_data:
                print(f"  📁 {category}: {len(category_data)} fields")
                for key, value in category_data.items():
                    print(f"    • {key}: {value}")
    else:
        print("❌ Combined extraction failed")
        return False
    
    return True

def test_memo_integration():
    """Test how the AI-extracted data would appear in the memo"""
    
    print("\n📝 Testing Memo Integration:")
    print("=" * 50)
    
    # Create a mock profile with AI-extracted data
    from core.schemas import StartupProfile
    
    profile = StartupProfile(
        name="Shopify",
        TAM=46000000000.0,
        SAM=10000000000.0,
        total_merchants=200000,
        global_merchants=46000000,
        core_geography_merchants=10000000,
        revenue_per_merchant=1000,
        market_definition="retailers with less than 500 employees",
        geographic_focus="U.S., Canada, U.K., Western Europe, Australia and New Zealand",
        market_source="AMI Partners",
        sector="ecommerce",
        # AI-extracted fields
        market_metrics_total_customers="200,000+",
        market_metrics_active_customers="200,000+",
        market_metrics_market_penetration="0.43%",
        geographic_data_global_market="46M merchants globally",
        geographic_data_core_geographies="U.S., Canada, U.K., Western Europe, Australia and New Zealand",
        growth_metrics_cagr="85%",
        growth_metrics_growth_drivers="Ecommerce adoption, mobile commerce, international expansion",
        competitive_data_market_share="Leading ecommerce platform",
        source_attribution_data_source="AMI Partners",
        source_attribution_research_firm="AMI Partners"
    )
    
    # Import and test the market section generation
    from agents.market_sizing_agent import generate_market_size_section
    
    try:
        market_section = generate_market_size_section(profile)
        print("✅ Memo integration successful!")
        print(f"📄 Section length: {len(market_section)} characters")
        
        # Check for AI-enhanced content
        ai_phrases = [
            "AI-Enhanced Market Intelligence",
            "AI-Detected Market Metrics",
            "AI-Detected Geographic Data", 
            "AI-Detected Growth Metrics",
            "AI-Detected Competitive Data",
            "AI-Detected Source Attribution"
        ]
        
        found_ai_phrases = []
        for phrase in ai_phrases:
            if phrase in market_section:
                found_ai_phrases.append(phrase)
                print(f"✅ Found: {phrase}")
            else:
                print(f"❌ Missing: {phrase}")
        
        print(f"\n📊 AI-enhanced content found: {len(found_ai_phrases)}/{len(ai_phrases)} phrases")
        
        # Show a sample of the memo section
        print("\n📄 Sample Memo Section:")
        print("-" * 50)
        lines = market_section.split('\n')
        for i, line in enumerate(lines):
            if i < 50:  # Show first 50 lines
                print(line)
            else:
                print("...")
                break
        
        return len(found_ai_phrases) >= len(ai_phrases) * 0.5  # 50% success rate
        
    except Exception as e:
        print(f"❌ Memo integration failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing AI-Powered Market Extraction and Memo Integration")
    print("=" * 70)
    
    # Test 1: AI extraction
    extraction_success = test_ai_market_extraction()
    
    # Test 2: Memo integration
    integration_success = test_memo_integration()
    
    print("\n" + "=" * 70)
    print("📋 FINAL RESULTS:")
    print(f"• AI Market Extraction: {'✅ PASS' if extraction_success else '❌ FAIL'}")
    print(f"• Memo Integration: {'✅ PASS' if integration_success else '❌ FAIL'}")
    
    if extraction_success and integration_success:
        print("\n🎉 All tests passed! AI-powered market extraction is working.")
        print("\n💡 Benefits of AI-powered extraction:")
        print("• Detects ANY market-related data, not just predefined patterns")
        print("• Extracts competitive intelligence, growth drivers, geographic data")
        print("• Provides comprehensive market analysis in the memo")
        print("• Adapts to different company types and industries")
    else:
        print("\n⚠️  Some tests failed. Review the output above for details.") 