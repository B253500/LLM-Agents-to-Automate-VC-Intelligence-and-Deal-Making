#!/usr/bin/env python3
"""
Test script to analyze financial data extraction opportunities
"""

import json
import sys
import os
import re

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.financial_analysis_chain import extract_financials_from_text as chain_extract_financials

def analyze_shopify_financial_data():
    """Analyze what financial data is available in Shopify PDF vs what we extract"""
    
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
    
    print("🔍 Analyzing Financial Data Extraction Opportunities")
    print("=" * 70)
    print(f"📄 Text length: {len(text)} characters")
    
    # Extract all financial patterns from the text
    financial_patterns = {
        # Revenue & Growth
        'revenue': r'\$[\d,\.]+[KMB]?\s*(?:revenue|sales|income)',
        'mrr': r'\$[\d,\.]+[KMB]?\s*MRR',
        'gmv': r'\$[\d,\.]+[KMB]?\s*GMV',
        'cagr': r'(\d+\.?\d*)\s*%\s*CAGR',
        'growth_rate': r'\+(\d+\.?\d*)\s*%',
        
        # Profitability
        'gross_profit': r'\$[\d,\.]+[KMB]?\s*(?:gross\s+)?profit',
        'gross_margin': r'(\d+\.?\d*)%\s*(?:gross\s+)?margin',
        'operating_margin': r'(\d+\.?\d*)%\s*operating\s+margin',
        
        # Business Metrics
        'merchants': r'(\d+[,.]?\d*)\+?\s*(?:merchants|customers|users)',
        'revenue_per_merchant': r'\$[\d,\.]+[KMB]?\s*(?:per\s+)?(?:merchant|customer)',
        'subscription_fees': r'\$[\d,\.]+[KMB]?\s*(?:subscription|monthly|annual)',
        
        # Market Data
        'tam': r'\$[\d,\.]+[KMB]?\s*(?:TAM|total\s+addressable\s+market)',
        'sam': r'\$[\d,\.]+[KMB]?\s*(?:SAM|serviceable\s+available\s+market)',
        'som': r'\$[\d,\.]+[KMB]?\s*(?:SOM|serviceable\s+obtainable\s+market)',
        
        # Valuation & Funding
        'valuation': r'\$[\d,\.]+[KMB]?\s*(?:valuation|market\s+cap)',
        'funding': r'\$[\d,\.]+[KMB]?\s*(?:funding|raised|investment)',
        
        # Operating Metrics
        'cash_burn': r'\$[\d,\.]+[KMB]?\s*(?:burn|burn\s+rate)',
        'runway': r'(\d+\.?\d*)\s*(?:months|mo)\s*(?:runway)',
        'cash_on_hand': r'\$[\d,\.]+[KMB]?\s*(?:cash|cash\s+on\s+hand)',
        
        # Efficiency Metrics
        'cac': r'\$[\d,\.]+[KMB]?\s*(?:CAC|customer\s+acquisition\s+cost)',
        'ltv': r'\$[\d,\.]+[KMB]?\s*(?:LTV|lifetime\s+value)',
        'payback_period': r'(\d+\.?\d*)\s*(?:months|mo)\s*(?:payback)',
        
        # Year-over-year data
        'revenue_2012': r'\$[\d,\.]+[KMB]?\s*2012',
        'revenue_2013': r'\$[\d,\.]+[KMB]?\s*2013',
        'revenue_2014': r'\$[\d,\.]+[KMB]?\s*2014',
        'revenue_2015': r'\$[\d,\.]+[KMB]?\s*2015',
        
        # Operating expenses
        's_m_expense': r'(\d+\.?\d*)%\s*(?:S&M|sales\s+and\s+marketing)',
        'r_d_expense': r'(\d+\.?\d*)%\s*(?:R&D|research\s+and\s+development)',
        'g_a_expense': r'(\d+\.?\d*)%\s*(?:G&A|general\s+and\s+administrative)',
    }
    
    print("\n📊 AVAILABLE FINANCIAL DATA IN SHOPIFY PDF:")
    print("-" * 50)
    
    found_data = {}
    for metric, pattern in financial_patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            found_data[metric] = matches
            print(f"✅ {metric.upper()}: {len(matches)} matches")
            for match in matches[:3]:  # Show first 3 matches
                print(f"   • {match}")
            if len(matches) > 3:
                print(f"   • ... and {len(matches) - 3} more")
    
    # Test current extraction methods
    print("\n🔧 CURRENT EXTRACTION METHODS:")
    print("-" * 50)
    
    # Test regex extraction from chains
    print("1. Regex extraction from chains:")
    chain_results = chain_extract_financials(text)
    if chain_results:
        print("   ✅ Found data:")
        for key, value in chain_results.items():
            print(f"   • {key}: {value}")
    else:
        print("   ❌ No data found")
    
    # Test download_utils extraction
    print("\n2. Download utils extraction:")
    print("   ⚠️  Function not available in download_utils")
    
    # Identify missing opportunities
    print("\n🎯 MISSING EXTRACTION OPPORTUNITIES:")
    print("-" * 50)
    
    missing_opportunities = []
    
    # Check for specific patterns that should be extracted
    specific_patterns = {
        'Revenue Growth': r'\$[\d,\.]+[KMB]?\s*revenue\s+growth',
        'MRR Growth': r'\$[\d,\.]+[KMB]?\s*MRR\s+growth',
        'GMV Growth': r'\$[\d,\.]+[KMB]?\s*GMV\s+growth',
        'Gross Profit Growth': r'\$[\d,\.]+[KMB]?\s*gross\s+profit\s+growth',
        'Operating Leverage': r'(\d+\.?\d*)%\s*operating\s+leverage',
        'Revenue per Merchant': r'\$[\d,\.]+[KMB]?\s*per\s+merchant',
        'Subscription Pricing': r'\$[\d,\.]+[KMB]?\s*(?:basic|professional|enterprise)',
        'Year-over-Year Growth': r'\+(\d+\.?\d*)%\s*(?:yoy|year\s+over\s+year)',
        'Quarter-over-Quarter Growth': r'\+(\d+\.?\d*)%\s*(?:qoq|quarter\s+over\s+quarter)',
        'Customer Growth': r'(\d+\.?\d*)%\s*customer\s+growth',
        'Merchant Growth': r'(\d+\.?\d*)%\s*merchant\s+growth',
        'Revenue Growth Rate': r'(\d+\.?\d*)%\s*revenue\s+growth',
        'Profit Margin': r'(\d+\.?\d*)%\s*profit\s+margin',
        'Gross Margin': r'(\d+\.?\d*)%\s*gross\s+margin',
        'Operating Margin': r'(\d+\.?\d*)%\s*operating\s+margin',
        'EBITDA Margin': r'(\d+\.?\d*)%\s*EBITDA\s+margin',
        'Cash Flow': r'\$[\d,\.]+[KMB]?\s*cash\s+flow',
        'Free Cash Flow': r'\$[\d,\.]+[KMB]?\s*free\s+cash\s+flow',
        'Working Capital': r'\$[\d,\.]+[KMB]?\s*working\s+capital',
        'Debt': r'\$[\d,\.]+[KMB]?\s*debt',
        'Equity': r'\$[\d,\.]+[KMB]?\s*equity',
        'Market Cap': r'\$[\d,\.]+[KMB]?\s*market\s+cap',
        'Enterprise Value': r'\$[\d,\.]+[KMB]?\s*enterprise\s+value',
        'P/E Ratio': r'(\d+\.?\d*)\s*P/E\s+ratio',
        'EV/EBITDA': r'(\d+\.?\d*)\s*EV/EBITDA',
        'Price to Sales': r'(\d+\.?\d*)\s*price\s+to\s+sales',
        'Return on Equity': r'(\d+\.?\d*)%\s*ROE',
        'Return on Assets': r'(\d+\.?\d*)%\s*ROA',
        'Return on Investment': r'(\d+\.?\d*)%\s*ROI',
        'Customer Acquisition Cost': r'\$[\d,\.]+[KMB]?\s*CAC',
        'Lifetime Value': r'\$[\d,\.]+[KMB]?\s*LTV',
        'Churn Rate': r'(\d+\.?\d*)%\s*churn',
        'Retention Rate': r'(\d+\.?\d*)%\s*retention',
        'Net Promoter Score': r'(\d+\.?\d*)\s*NPS',
        'Customer Satisfaction': r'(\d+\.?\d*)%\s*satisfaction',
    }
    
    for metric, pattern in specific_patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            missing_opportunities.append({
                'metric': metric,
                'pattern': pattern,
                'matches': matches,
                'count': len(matches)
            })
    
    if missing_opportunities:
        print(f"Found {len(missing_opportunities)} missing extraction opportunities:")
        for opp in missing_opportunities:
            print(f"   • {opp['metric']}: {opp['count']} matches")
            for match in opp['matches'][:2]:  # Show first 2 matches
                print(f"     - {match}")
    else:
        print("   ✅ All major financial patterns are being extracted")
    
    # Suggest improvements
    print("\n💡 SUGGESTED IMPROVEMENTS:")
    print("-" * 50)
    
    print("1. **Generic AI-Powered Financial Extraction**")
    print("   - Use AI to detect ANY financial metrics without predefined patterns")
    print("   - Extract year-over-year growth rates, margins, efficiency metrics")
    print("   - Capture business model details (subscription tiers, pricing)")
    
    print("\n2. **Enhanced Regex Patterns**")
    print("   - Add patterns for operating expenses (S&M, R&D, G&A)")
    print("   - Extract efficiency metrics (CAC, LTV, payback period)")
    print("   - Capture growth rates and CAGR data")
    
    print("\n3. **Business Model Extraction**")
    print("   - Extract subscription pricing tiers")
    print("   - Identify revenue streams and pricing models")
    print("   - Capture customer segments and pricing strategies")
    
    print("\n4. **Historical Data Extraction**")
    print("   - Extract year-over-year financial data")
    print("   - Capture quarterly growth rates")
    print("   - Identify trends and patterns")
    
    print("\n5. **Generic vs Specific Approach**")
    print("   - Use AI for generic detection (finds unexpected metrics)")
    print("   - Use regex for specific, reliable extraction")
    print("   - Combine both for maximum coverage")
    
    return True

def test_generic_financial_extraction():
    """Test a more generic approach to financial data extraction"""
    
    print("\n🤖 TESTING GENERIC FINANCIAL EXTRACTION")
    print("=" * 50)
    
    # Load Shopify text
    shopify_cache_file = "extraction_cache/shopify.pdf_68adaa0de2223b7b38fe146a2cfe826b7a21dd8b.json"
    
    try:
        with open(shopify_cache_file, 'r') as f:
            data = json.load(f)
            text = data.get('text', '')
    except FileNotFoundError:
        print(f"❌ Shopify cache file not found: {shopify_cache_file}")
        return False
    
    # Generic financial extraction patterns
    generic_patterns = {
        # Any dollar amounts with context
        'dollar_amounts': r'\$[\d,\.]+[KMB]?',
        # Any percentages
        'percentages': r'(\d+\.?\d*)%',
        # Any growth rates
        'growth_rates': r'\+(\d+\.?\d*)%',
        # Any CAGR mentions
        'cagr_mentions': r'(\d+\.?\d*)\s*CAGR',
        # Any year references with financial data
        'year_financials': r'(\d{4})\s*\$[\d,\.]+[KMB]?',
        # Any "per" metrics
        'per_metrics': r'\$[\d,\.]+[KMB]?\s*per\s+\w+',
        # Any margin mentions
        'margin_mentions': r'(\d+\.?\d*)%\s*margin',
        # Any ratio mentions
        'ratio_mentions': r'(\d+\.?\d*)\s*ratio',
    }
    
    print("Generic financial data found:")
    for metric, pattern in generic_patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            print(f"   • {metric}: {len(matches)} matches")
            # Show a few examples
            for match in matches[:3]:
                print(f"     - {match}")
            if len(matches) > 3:
                print(f"     - ... and {len(matches) - 3} more")
    
    return True

if __name__ == "__main__":
    print("🚀 Analyzing Financial Data Extraction Opportunities")
    print("=" * 70)
    
    # Analyze current extraction vs available data
    analyze_success = analyze_shopify_financial_data()
    
    # Test generic extraction
    generic_success = test_generic_financial_extraction()
    
    print("\n" + "=" * 70)
    print("📋 SUMMARY:")
    print("• Current extraction focuses on core metrics (revenue, burn, runway)")
    print("• Many additional financial metrics are available but not extracted")
    print("• Generic AI extraction could capture more comprehensive data")
    print("• Enhanced regex patterns could improve reliability")
    print("• Hybrid approach (AI + regex) would provide maximum coverage") 