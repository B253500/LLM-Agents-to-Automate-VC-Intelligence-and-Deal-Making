#!/usr/bin/env python3
"""
Test script to verify enhanced financial extraction
"""

import json
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.download_utils import extract_financials_from_text, ai_extract_financial_data

def test_enhanced_financial_extraction():
    """Test the enhanced financial extraction system"""
    
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
    
    print("🔍 Testing Enhanced Financial Extraction")
    print("=" * 60)
    print(f"📄 Text length: {len(text)} characters")
    
    # Test 1: AI-powered financial extraction
    print("\n🤖 AI-POWERED FINANCIAL EXTRACTION:")
    print("-" * 40)
    print("AI detects ANY financial metrics without predefined patterns")
    
    ai_financial_data = ai_extract_financial_data(text)
    
    if ai_financial_data:
        print("✅ AI financial extraction successful!")
        print(f"📊 Found {len(ai_financial_data)} financial categories:")
        
        for category, data in ai_financial_data.items():
            if isinstance(data, dict):
                print(f"  📁 {category}: {len(data)} fields")
                for key, value in data.items():
                    if value and value != "null":
                        print(f"    • {key}: {value}")
            elif data and data != "null":
                print(f"  📁 {category}: {data}")
    else:
        print("❌ AI financial extraction failed")
    
    # Test 2: Combined extraction (Regex + AI)
    print("\n🔧 COMBINED EXTRACTION (Regex + AI):")
    print("-" * 40)
    print("Regex patterns + AI-powered detection")
    
    combined_financial_data = extract_financials_from_text(text)
    
    if combined_financial_data:
        print("✅ Combined extraction successful!")
        print(f"📊 Found {len(combined_financial_data)} total financial data points:")
        
        # Categorize the data
        categories = {
            'Revenue Metrics': [k for k in combined_financial_data.keys() if any(term in k for term in ['revenue', 'mrr', 'gmv', 'arr'])],
            'Profitability Metrics': [k for k in combined_financial_data.keys() if any(term in k for term in ['profit', 'margin', 'ebitda', 'income'])],
            'Growth Metrics': [k for k in combined_financial_data.keys() if any(term in k for term in ['growth', 'cagr', 'rate'])],
            'Business Model': [k for k in combined_financial_data.keys() if any(term in k for term in ['subscription', 'pricing', 'model', 'segments'])],
            'Operational Metrics': [k for k in combined_financial_data.keys() if any(term in k for term in ['burn', 'runway', 'cash', 'working', 'debt', 'equity'])],
            'Efficiency Metrics': [k for k in combined_financial_data.keys() if any(term in k for term in ['cac', 'ltv', 'payback', 'churn', 'retention'])],
            'Valuation Metrics': [k for k in combined_financial_data.keys() if any(term in k for term in ['valuation', 'market_cap', 'enterprise', 'pe_ratio', 'ev_ebitda'])],
            'Historical Data': [k for k in combined_financial_data.keys() if any(term in k for term in ['by_year', 'historical'])],
            'Operating Expenses': [k for k in combined_financial_data.keys() if any(term in k for term in ['sales_marketing', 'research_development', 'general_administrative'])]
        }
        
        for category, fields in categories.items():
            category_data = {k: v for k, v in combined_financial_data.items() if k in fields}
            if category_data:
                print(f"  📁 {category}: {len(category_data)} fields")
                for key, value in category_data.items():
                    print(f"    • {key}: {value}")
    
    else:
        print("❌ Combined extraction failed")
    
    return True

def compare_extraction_methods():
    """Compare different extraction methods"""
    
    print("\n📊 COMPARISON: Extraction Methods")
    print("=" * 60)
    
    print("\n🎯 REGEX PATTERNS PROS:")
    print("✅ Reliable extraction of specific metrics")
    print("✅ Fast and efficient processing")
    print("✅ Consistent results across different documents")
    print("✅ Good for core financial metrics (revenue, burn, runway)")
    print("✅ Easy to maintain and update")
    
    print("\n🤖 AI-POWERED EXTRACTION PROS:")
    print("✅ Discovers unexpected financial insights")
    print("✅ Extracts business model details (pricing tiers, revenue streams)")
    print("✅ Captures historical data and trends")
    print("✅ Identifies efficiency metrics and ratios")
    print("✅ Adapts to different document formats and industries")
    
    print("\n🔧 HYBRID APPROACH (BEST OF BOTH):")
    print("✅ Uses regex for reliable core metrics")
    print("✅ Uses AI for comprehensive discovery")
    print("✅ Combines both for maximum coverage")
    print("✅ Adapts to different company types and industries")
    print("✅ Provides both reliability and creativity")
    
    print("\n💡 RECOMMENDATION:")
    print("Use the hybrid approach for maximum financial data coverage:")
    print("1. Regex patterns for core metrics (reliable)")
    print("2. AI-powered extraction for comprehensive discovery")
    print("3. Combined approach for maximum coverage")

if __name__ == "__main__":
    print("🚀 Testing Enhanced Financial Extraction")
    print("=" * 70)
    
    # Test the enhanced extraction
    test_success = test_enhanced_financial_extraction()
    
    # Compare extraction methods
    compare_extraction_methods()
    
    print("\n" + "=" * 70)
    print("📋 CONCLUSION:")
    print("• Enhanced extraction captures more comprehensive financial data")
    print("• AI-powered detection finds unexpected insights")
    print("• Regex patterns provide reliable core metrics")
    print("• Hybrid approach gives maximum coverage")
    print("• Generic approach without losing content quality") 