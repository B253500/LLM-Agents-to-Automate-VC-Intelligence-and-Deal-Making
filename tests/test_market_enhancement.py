#!/usr/bin/env python3
"""
Test script to verify enhanced market extraction from Shopify PDF
"""

import json
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.download_utils import extract_market_size_from_text

def test_shopify_market_extraction():
    """Test the enhanced market extraction on Shopify PDF text"""
    
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
    
    print("🔍 Testing enhanced market extraction on Shopify PDF...")
    print(f"📄 Text length: {len(text)} characters")
    
    # Extract market data
    market_data = extract_market_size_from_text(text)
    
    print("\n📊 Extracted Market Data:")
    print("=" * 50)
    
    # Expected data from Shopify PDF
    expected_data = {
        'TAM': 46000000000.0,  # $46B
        'SAM': 10000000000.0,  # $10B
        'total_merchants': 200000.0,  # 200,000+
        'global_merchants': 46000000.0,  # 46M
        'core_geography_merchants': 10000000.0,  # 10M
        'revenue_per_merchant': 1000.0,  # $1,000
        'market_definition': 'retailers with less than 500 employees',
        'geographic_focus': 'U.S., Canada, U.K., Western Europe, Australia and New Zealand',
        'market_source': 'AMI Partners'
    }
    
    # Check each expected field
    success_count = 0
    total_checks = len(expected_data)
    
    for field, expected_value in expected_data.items():
        extracted_value = market_data.get(field)
        
        if extracted_value:
            # For numeric values, allow some tolerance
            if isinstance(expected_value, (int, float)) and isinstance(extracted_value, (int, float)):
                if abs(extracted_value - expected_value) < expected_value * 0.1:  # 10% tolerance
                    print(f"✅ {field}: {extracted_value} (expected: {expected_value})")
                    success_count += 1
                else:
                    print(f"⚠️  {field}: {extracted_value} (expected: {expected_value}) - value mismatch")
            else:
                # For text values, check if expected is contained in extracted
                if isinstance(expected_value, str) and isinstance(extracted_value, str):
                    if expected_value.lower() in extracted_value.lower():
                        print(f"✅ {field}: {extracted_value}")
                        success_count += 1
                    else:
                        print(f"⚠️  {field}: {extracted_value} (expected: {expected_value}) - text mismatch")
                else:
                    print(f"✅ {field}: {extracted_value}")
                    success_count += 1
        else:
            print(f"❌ {field}: NOT FOUND (expected: {expected_value})")
    
    print(f"\n📈 Success Rate: {success_count}/{total_checks} ({success_count/total_checks*100:.1f}%)")
    
    # Additional analysis
    print(f"\n🔍 Additional Analysis:")
    print(f"• Total fields extracted: {len(market_data)}")
    print(f"• Raw extracted data: {market_data}")
    
    # Test market penetration calculation
    if market_data.get('total_merchants') and market_data.get('global_merchants'):
        try:
            total_merchants = float(str(market_data['total_merchants']).replace(',', '').replace('+', ''))
            global_merchants = float(str(market_data['global_merchants']).replace('M', '000000'))
            penetration = (total_merchants / global_merchants) * 100
            print(f"• Market Penetration: {penetration:.2f}%")
        except:
            print("• Market Penetration: Could not calculate")
    
    return success_count >= total_checks * 0.7  # 70% success rate

def test_market_section_generation():
    """Test the enhanced market section generation"""
    
    print("\n🧪 Testing market section generation...")
    
    # Create a mock profile with Shopify data
    from core.schemas import StartupProfile
    
    profile = StartupProfile(
        name="Shopify",
        TAM=46000000000.0,  # $46B
        SAM=10000000000.0,  # $10B
        total_merchants=200000,
        global_merchants=46000000,
        core_geography_merchants=10000000,
        revenue_per_merchant=1000,
        market_definition="retailers with less than 500 employees",
        geographic_focus="U.S., Canada, U.K., Western Europe, Australia and New Zealand",
        market_source="AMI Partners",
        sector="ecommerce"
    )
    
    # Import and test the market section generation
    from agents.market_sizing_agent import generate_market_size_section
    
    try:
        market_section = generate_market_size_section(profile)
        print("✅ Market section generation successful")
        print(f"📄 Section length: {len(market_section)} characters")
        
        # Check for key content
        key_phrases = [
            "Market Penetration",
            "Active Merchants", 
            "Global Addressable Merchants",
            "Core Geography Merchants",
            "Revenue per Merchant",
            "Market Definition",
            "Geographic Focus",
            "Market Data Source"
        ]
        
        found_phrases = []
        for phrase in key_phrases:
            if phrase in market_section:
                found_phrases.append(phrase)
                print(f"✅ Found: {phrase}")
            else:
                print(f"❌ Missing: {phrase}")
        
        print(f"\n📊 Enhanced content found: {len(found_phrases)}/{len(key_phrases)} phrases")
        
        return len(found_phrases) >= len(key_phrases) * 0.8  # 80% success rate
        
    except Exception as e:
        print(f"❌ Market section generation failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Enhanced Market Extraction and Generation")
    print("=" * 60)
    
    # Test 1: Market extraction
    extraction_success = test_shopify_market_extraction()
    
    # Test 2: Market section generation
    generation_success = test_market_section_generation()
    
    print("\n" + "=" * 60)
    print("📋 FINAL RESULTS:")
    print(f"• Market Extraction: {'✅ PASS' if extraction_success else '❌ FAIL'}")
    print(f"• Market Generation: {'✅ PASS' if generation_success else '❌ FAIL'}")
    
    if extraction_success and generation_success:
        print("\n🎉 All tests passed! Enhanced market data utilization is working.")
    else:
        print("\n⚠️  Some tests failed. Review the output above for details.") 