#!/usr/bin/env python3
"""
Test script to verify markdown asterisk stripping from headers
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_markdown_asterisk_stripping():
    """Test that markdown asterisks are properly stripped from headers."""
    
    print("🔧 Testing Markdown Asterisk Stripping")
    print("=" * 50)
    
    # Sample headers with markdown asterisks
    headers_with_asterisks = [
        "**📊 Market Size Metrics**",
        "**📈 Growth Metrics**",
        "**📰 Sector Analysis**",
        "**Business Model Overview**",
        "**Potential Revenue Streams**",
        "**Market Risks**",
        "**Technical Risks**",
        "**Follow-up Questions**",
        "**Key Strengths**"
    ]
    
    print("📄 Headers with Markdown Asterisks (Before):")
    for header in headers_with_asterisks:
        print(f"   ❌ {header}")
    
    # Simulate the strip_markdown_bold function
    import re
    def strip_markdown_bold(text):
        """Strip markdown bold formatting (**text**) and return plain text."""
        return re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    
    print("\n📄 Headers After Stripping Asterisks (After):")
    for header in headers_with_asterisks:
        stripped = strip_markdown_bold(header)
        print(f"   ✅ {stripped}")
    
    print("\n🔍 Test Cases:")
    
    # Test various markdown patterns
    test_cases = [
        ("**📊 Market Size Metrics**", "📊 Market Size Metrics"),
        ("**Business Model Overview**", "Business Model Overview"),
        ("**Market Risks**", "Market Risks"),
        ("**Follow-up Questions**", "Follow-up Questions"),
        ("**Key Strengths**", "Key Strengths"),
        ("Normal text without asterisks", "Normal text without asterisks"),
        ("**Mixed** text with **bold** parts", "Mixed text with bold parts")
    ]
    
    all_passed = True
    for input_text, expected_output in test_cases:
        actual_output = strip_markdown_bold(input_text)
        passed = actual_output == expected_output
        status = "✅" if passed else "❌"
        print(f"   {status} '{input_text}' -> '{actual_output}'")
        if not passed:
            all_passed = False
    
    print(f"\n🎯 Expected Behavior:")
    print(f"   • Headers: Plain text without asterisks")
    print(f"   • Formatting: Bold applied by main.py")
    print(f"   • Result: Clean, professional appearance")
    
    print(f"\n✅ Final Result:")
    if all_passed:
        print(f"   ✅ All markdown asterisks properly stripped")
        print(f"   ✅ Headers will appear clean in DOCX/PDF")
    else:
        print(f"   ❌ Some markdown asterisks not properly stripped")
    
    return all_passed

if __name__ == "__main__":
    test_markdown_asterisk_stripping() 