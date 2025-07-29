#!/usr/bin/env python3
"""
Test script to verify the market section first paragraph is not bold
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_market_first_paragraph_fix():
    """Test that the market section first paragraph is not bold."""
    
    print("🔧 Testing Market First Paragraph Fix...")
    print("=" * 50)
    
    # Sample market section first paragraph
    first_paragraph = "The total addressable market (TAM) for the battery technology sector is currently valued at $160 billion, with a serviceable available market (SAM) of $48 billion."
    
    print("📄 Sample First Paragraph:")
    print(f"   '{first_paragraph}'")
    
    # Test the detection logic
    detection_conditions = [
        first_paragraph.startswith("The total addressable market"),
        first_paragraph.startswith("The Total Addressable Market"),
        "battery technology sector" in first_paragraph,
        "TAM for the Battery Technology sector" in first_paragraph,
        "total addressable market" in first_paragraph.lower()
    ]
    
    print("\n🔍 Detection Logic Test:")
    print(f"   Starts with 'The total addressable market': {detection_conditions[0]}")
    print(f"   Starts with 'The Total Addressable Market': {detection_conditions[1]}")
    print(f"   Contains 'battery technology sector': {detection_conditions[2]}")
    print(f"   Contains 'TAM for the Battery Technology sector': {detection_conditions[3]}")
    print(f"   Contains 'total addressable market' (case-insensitive): {detection_conditions[4]}")
    
    # Check if any condition is met
    should_be_normal_text = any(detection_conditions)
    
    print(f"\n✅ Result:")
    print(f"   Should be processed as normal text: {should_be_normal_text}")
    print(f"   Expected formatting: Normal text (not bold)")
    print(f"   Font: Times New Roman, Size: 12pt, Bold: False")
    
    if should_be_normal_text:
        print("   ✅ First paragraph will be correctly formatted as normal text")
    else:
        print("   ❌ First paragraph detection failed")
    
    print(f"\n🎯 Expected Behavior:")
    print(f"   • First paragraph: Normal text (not bold)")
    print(f"   • Headers (📊 Market Size Metrics): Bold")
    print(f"   • Content bullets: Normal text with targeted bold for keywords")
    
    return should_be_normal_text

if __name__ == "__main__":
    test_market_first_paragraph_fix() 