#!/usr/bin/env python3
"""
Test script to compare open-ended AI detection vs guided detection
"""

import json
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.download_utils import ai_detect_any_market_data, ai_extract_market_data, extract_market_size_from_text

def test_open_ended_vs_guided():
    """Compare open-ended AI detection vs guided detection"""
    
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
    
    print("🔍 Comparing Open-Ended vs Guided AI Detection")
    print("=" * 60)
    print(f"📄 Text length: {len(text)} characters")
    
    # Test 1: Open-Ended Detection
    print("\n🤖 OPEN-ENDED AI DETECTION:")
    print("-" * 40)
    print("AI finds ANY market-related data without predefined categories")
    
    open_ended_data = ai_detect_any_market_data(text)
    
    if open_ended_data:
        print("✅ Open-ended detection successful!")
        print(f"📊 Found {len(open_ended_data)} market insights:")
        
        for key, value in open_ended_data.items():
            print(f"  • {key}: {value}")
    else:
        print("❌ Open-ended detection failed")
    
    # Test 2: Guided Detection
    print("\n🎯 GUIDED AI DETECTION:")
    print("-" * 40)
    print("AI extracts data into predefined categories")
    
    guided_data = ai_extract_market_data(text)
    
    if guided_data:
        print("✅ Guided detection successful!")
        print(f"📊 Found {len(guided_data)} categories:")
        
        for category, data in guided_data.items():
            if isinstance(data, dict):
                print(f"  📁 {category}: {len(data)} fields")
                for key, value in data.items():
                    if value and value != "null":
                        print(f"    • {key}: {value}")
            elif data and data != "null":
                print(f"  📁 {category}: {data}")
    else:
        print("❌ Guided detection failed")
    
    # Test 3: Combined Approach (Regex + Both AI methods)
    print("\n🔧 COMBINED APPROACH:")
    print("-" * 40)
    print("Regex patterns + Open-ended AI + Guided AI")
    
    combined_data = extract_market_size_from_text(text)
    
    if combined_data:
        print("✅ Combined approach successful!")
        print(f"📊 Found {len(combined_data)} total data points:")
        
        # Categorize the data
        categories = {
            'Regex Patterns': [k for k in combined_data.keys() if not k.startswith('ai_') and not any(prefix in k for prefix in ['market_metrics_', 'geographic_data_', 'growth_metrics_', 'competitive_data_', 'source_attribution_'])],
            'Open-Ended AI': [k for k in combined_data.keys() if k.startswith('ai_detected_')],
            'Guided AI': [k for k in combined_data.keys() if any(prefix in k for prefix in ['market_metrics_', 'geographic_data_', 'growth_metrics_', 'competitive_data_', 'source_attribution_'])]
        }
        
        for category, fields in categories.items():
            category_data = {k: v for k, v in combined_data.items() if k in fields}
            if category_data:
                print(f"  📁 {category}: {len(category_data)} fields")
                for key, value in category_data.items():
                    print(f"    • {key}: {value}")
    else:
        print("❌ Combined approach failed")
    
    return True

def analyze_differences():
    """Analyze the differences between approaches"""
    
    print("\n📊 ANALYSIS: Open-Ended vs Guided Detection")
    print("=" * 60)
    
    print("\n🎯 GUIDED DETECTION PROS:")
    print("✅ Consistent structure - always gets TAM, SAM, SOM")
    print("✅ Reliable extraction - knows exactly what to look for")
    print("✅ Easier memo formatting - predictable data structure")
    print("✅ Better validation - can check if required fields are found")
    print("✅ Industry-specific patterns - optimized for different sectors")
    
    print("\n🤖 OPEN-ENDED DETECTION PROS:")
    print("✅ Discovers unexpected insights (e.g., 'synonymous with ecommerce')")
    print("✅ Adapts to any industry (battery tech, fintech, ecommerce)")
    print("✅ Finds hidden patterns (e.g., 'Build-a-Business competition winners')")
    print("✅ No maintenance - doesn't need pattern updates")
    print("✅ Creative insights - finds market validation signals")
    
    print("\n🔧 HYBRID APPROACH (BEST OF BOTH):")
    print("✅ Uses regex for reliable core metrics (TAM, SAM, CAGR)")
    print("✅ Uses guided AI for structured categories")
    print("✅ Uses open-ended AI for unexpected insights")
    print("✅ Combines all three for comprehensive coverage")
    print("✅ Adapts to different company types and industries")
    
    print("\n💡 RECOMMENDATION:")
    print("Use the hybrid approach for maximum coverage:")
    print("1. Regex patterns for core metrics (reliable)")
    print("2. Guided AI for structured categories (consistent)")
    print("3. Open-ended AI for unexpected insights (creative)")

if __name__ == "__main__":
    print("🚀 Testing Open-Ended vs Guided AI Market Detection")
    print("=" * 70)
    
    # Test the approaches
    test_success = test_open_ended_vs_guided()
    
    # Analyze differences
    analyze_differences()
    
    print("\n" + "=" * 70)
    print("📋 CONCLUSION:")
    print("• Open-ended detection finds unexpected insights")
    print("• Guided detection provides consistent structure")
    print("• Hybrid approach gives maximum coverage")
    print("• Best approach depends on your needs:")
    print("  - Need reliability? → Use guided + regex")
    print("  - Want creativity? → Use open-ended")
    print("  - Want both? → Use hybrid approach") 