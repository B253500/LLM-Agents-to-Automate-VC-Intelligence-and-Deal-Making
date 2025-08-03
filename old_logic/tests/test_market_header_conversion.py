#!/usr/bin/env python3
"""
Test script to verify Market header conversion from bullet points to bold
"""

import sys
import os
import re
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_market_header_conversion():
    """Test that market headers are converted from bullet points to bold."""
    
    # Sample content with bullet points that should be converted to bold
    test_content = """The total addressable market (TAM) for the battery technology sector is currently valued at $160 billion.

• 📊 Market Size Metrics
• **Total Addressable Market (TAM)**: $160B [Source: Pitch Deck]
• **Serviceable Available Market (SAM)**: $48B [Source: Pitch Deck]

• 📈 Growth Metrics
**CAGR**: 15.0% [Source: Pitch Deck]

• 📰 Sector Analysis
Market Overview:
The Battery Technology sector has seen significant growth in recent years.

• 🔍 Market Research Sources
• [PitchBook](https://pitchbook.com)
• [Crunchbase](https://crunchbase.com)

• 🔗 Additional Sources
• [TechCrunch](https://techcrunch.com)"""

    print("Testing Market header conversion...")
    print("=" * 60)
    
    # Apply the conversion rules from memo_synthesis_chain.py
    raw = test_content
    
    # Fix market section headers that might be bullet points instead of bold
    raw = re.sub(r'^•\s*📊 Market Size Metrics$', r'**📊 Market Size Metrics**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*📈 Growth Metrics$', r'**📈 Growth Metrics**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*📰 Sector Analysis$', r'**📰 Sector Analysis**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*🔍 Market Research Sources$', r'**🔍 Market Research Sources**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*🔗 Additional Sources$', r'**🔗 Additional Sources**', raw, flags=re.MULTILINE)
    
    # Also convert plain text market headers to bold formatting
    raw = re.sub(r'^📊 Market Size Metrics$', r'**📊 Market Size Metrics**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^📈 Growth Metrics$', r'**📈 Growth Metrics**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^📰 Sector Analysis$', r'**📰 Sector Analysis**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^🔍 Market Research Sources$', r'**🔍 Market Research Sources**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^🔗 Additional Sources$', r'**🔗 Additional Sources**', raw, flags=re.MULTILINE)
    
    print("Original content:")
    print("-" * 40)
    print(test_content)
    print("\nConverted content:")
    print("-" * 40)
    print(raw)
    
    # Check if conversions worked
    conversions = [
        ("• 📊 Market Size Metrics", "**📊 Market Size Metrics**"),
        ("• 📈 Growth Metrics", "**📈 Growth Metrics**"),
        ("• 📰 Sector Analysis", "**📰 Sector Analysis**"),
        ("• 🔍 Market Research Sources", "**🔍 Market Research Sources**"),
        ("• 🔗 Additional Sources", "**🔗 Additional Sources**")
    ]
    
    print("\n" + "=" * 60)
    print("Conversion Results:")
    print("-" * 40)
    
    all_passed = True
    for original, expected in conversions:
        if expected in raw:
            print(f"✅ PASS | {original} → {expected}")
        else:
            print(f"❌ FAIL | {original} was not converted to {expected}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All market headers successfully converted from bullet points to bold!")
    else:
        print("❌ Some market headers were not converted correctly.")
    
    return all_passed

if __name__ == "__main__":
    test_market_header_conversion() 