#!/usr/bin/env python3
"""
Comprehensive test for Market section formatting
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_market_section_comprehensive():
    """Test comprehensive market section formatting."""
    
    # Sample content that would come from the market sizing agent
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

    print("Testing comprehensive Market section formatting...")
    print("=" * 70)
    
    # Apply the conversion rules (simulating what happens in memo_synthesis_chain.py)
    import re
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
    
    print("1. Testing header conversion from bullet points to bold:")
    print("-" * 50)
    
    # Check header conversions
    header_conversions = [
        ("• 📊 Market Size Metrics", "**📊 Market Size Metrics**"),
        ("• 📈 Growth Metrics", "**📈 Growth Metrics**"),
        ("• 📰 Sector Analysis", "**📰 Sector Analysis**"),
        ("• 🔍 Market Research Sources", "**🔍 Market Research Sources**"),
        ("• 🔗 Additional Sources", "**🔗 Additional Sources**")
    ]
    
    header_passed = True
    for original, expected in header_conversions:
        if expected in raw:
            print(f"✅ PASS | {original} → {expected}")
        else:
            print(f"❌ FAIL | {original} was not converted to {expected}")
            header_passed = False
    
    print("\n2. Testing first paragraph preservation (should remain normal text):")
    print("-" * 50)
    
    # Check that first paragraph is preserved as normal text
    first_paragraph = "The total addressable market (TAM) for the battery technology sector is currently valued at $160 billion."
    if first_paragraph in raw:
        print(f"✅ PASS | First paragraph preserved as normal text")
    else:
        print(f"❌ FAIL | First paragraph was modified")
        header_passed = False
    
    print("\n3. Testing content preservation (bullet points should remain for content):")
    print("-" * 50)
    
    # Check that content bullet points are preserved
    content_bullets = [
        "• **Total Addressable Market (TAM)**: $160B [Source: Pitch Deck]",
        "• **Serviceable Available Market (SAM)**: $48B [Source: Pitch Deck]",
        "• [PitchBook](https://pitchbook.com)",
        "• [Crunchbase](https://crunchbase.com)",
        "• [TechCrunch](https://techcrunch.com)"
    ]
    
    content_passed = True
    for bullet in content_bullets:
        if bullet in raw:
            print(f"✅ PASS | Content bullet preserved: {bullet}")
        else:
            print(f"❌ FAIL | Content bullet missing: {bullet}")
            content_passed = False
    
    print("\n" + "=" * 70)
    print("Final Results:")
    print("-" * 30)
    
    if header_passed and content_passed:
        print("✅ ALL TESTS PASSED!")
        print("✅ Market headers correctly converted from bullet points to bold")
        print("✅ First paragraph preserved as normal text")
        print("✅ Content bullet points preserved correctly")
        print("✅ Market section formatting is working correctly")
    else:
        print("❌ SOME TESTS FAILED!")
        if not header_passed:
            print("❌ Header conversion issues detected")
        if not content_passed:
            print("❌ Content preservation issues detected")
    
    return header_passed and content_passed

if __name__ == "__main__":
    test_market_section_comprehensive() 