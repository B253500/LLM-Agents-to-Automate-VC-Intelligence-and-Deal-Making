#!/usr/bin/env python3
"""
Test script to debug the prompt template issue
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.technical_dd_chain import PROMPT, SYSTEM

def test_prompt_debug():
    """Debug the prompt template issue"""
    
    print("=" * 80)
    print("PROMPT DEBUG")
    print("=" * 80)
    
    # Check the SYSTEM prompt for problematic strings
    print("Checking SYSTEM prompt for problematic strings:")
    problematic_strings = [
        '"tech_maturity"', '"moat_strength"', '"tech_stack"', 
        '"product_specifications"', '"product_roadmap"', '"patent_portfolio"',
        '"complexity"', '"security"', '"implementation"', '"regulatory"', '"testing"'
    ]
    
    for string in problematic_strings:
        if string in SYSTEM:
            print(f"❌ Found problematic string in SYSTEM: {string}")
            # Find the context around this string
            idx = SYSTEM.find(string)
            start = max(0, idx - 100)
            end = min(len(SYSTEM), idx + 100)
            print(f"   Context: ...{SYSTEM[start:end]}...")
        else:
            print(f"✅ No problematic string in SYSTEM: {string}")
    
    # Check for curly braces in SYSTEM
    print(f"\nCurly braces in SYSTEM: {{: {SYSTEM.count('{')}, }}: {SYSTEM.count('}')}")
    
    # Test the prompt formatting with a simple context
    print("\nTesting prompt formatting with simple context:")
    try:
        simple_context = "This is a test context for StoreDot battery technology."
        formatted_prompt = PROMPT.format(context=simple_context)
        print("✅ Prompt formatting successful with simple context")
    except Exception as e:
        print(f"❌ Prompt formatting failed with simple context: {e}")
    
    # Test with the actual context
    print("\nTesting prompt formatting with actual context:")
    try:
        # Load the extracted StoreDot document
        with open('extraction_cache/storedot.pdf_70f0efbe04165831c2d2b807ff7d3227ce6f59d2.json', 'r') as f:
            data = json.load(f)
        
        text = data['text']
        context = text[:8000]
        clean_context = context.replace('"', "'").replace('\n', ' ').replace('{', '{{').replace('}', '}}').strip()
        
        formatted_prompt = PROMPT.format(context=clean_context)
        print("✅ Prompt formatting successful with actual context")
        print(f"Formatted prompt length: {len(formatted_prompt)} characters")
        
    except Exception as e:
        print(f"❌ Prompt formatting failed with actual context: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_prompt_debug() 