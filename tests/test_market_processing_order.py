#!/usr/bin/env python3
"""
Test script to verify Market Size processing order
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_market_processing_order():
    """Test that Market Size first paragraph is processed before section-specific formatting."""
    
    # Simulate the processing order from main.py
    test_content = [
        "The total addressable market (TAM) for the battery technology sector is currently valued at $160 billion.",
        "📊 Market Size Metrics",
        "• **Total Addressable Market (TAM)**: $160B [Source: Pitch Deck]",
        "📈 Growth Metrics",
        "**CAGR**: 15.0% [Source: Pitch Deck]",
        "📰 Sector Analysis",
        "Market Overview:",
        "The Battery Technology sector has seen significant growth in recent years."
    ]
    
    print("Testing Market Size processing order...")
    print("=" * 60)
    
    # Simulate the detection logic
    current_section = "default"
    
    for i, line in enumerate(test_content, 1):
        line_stripped = line.strip()
        
        # Check for market section headers
        if any(header in line_stripped for header in [
            "📊 Market Size Metrics", "📈 Growth Metrics", "📰 Sector Analysis",
            "🔍 Market Research Sources", "🔗 Additional Sources"
        ]):
            current_section = "market"
            print(f"{i:2d}. SET current_section = 'market' | {line_stripped}")
        else:
            print(f"{i:2d}. current_section = '{current_section}' | {line_stripped}")
        
        # Simulate the formatting logic
        if (line_stripped.startswith("The Total Addressable Market") or 
            line_stripped.startswith("The total addressable market") or
            line_stripped.startswith("The global battery technology market") or
            "battery technology sector" in line_stripped or
            "TAM for the Battery Technology sector" in line_stripped or
            "total addressable market" in line_stripped.lower()):
            print(f"     → FIRST PARAGRAPH DETECTED: Normal formatting (not bold)")
        elif current_section == "market":
            print(f"     → MARKET SECTION: Using format_market_section()")
        else:
            print(f"     → DEFAULT: Using process_text_with_hyperlinks_and_targeted_bold()")
    
    print("\n" + "=" * 60)
    print("Expected behavior:")
    print("1. First paragraph should be detected BEFORE section-specific formatting")
    print("2. Market headers should set current_section = 'market'")
    print("3. Content after headers should use format_market_section()")
    print("4. First paragraph should be NORMAL text (not bold)")
    
    return True

if __name__ == "__main__":
    test_market_processing_order() 