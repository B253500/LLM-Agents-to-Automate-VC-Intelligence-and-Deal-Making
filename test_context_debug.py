#!/usr/bin/env python3
"""
Test script to debug the context formatting issue
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_context_debug():
    """Debug what's in the context causing formatting issues"""
    
    # Load the extracted StoreDot document
    with open('extraction_cache/storedot.pdf_70f0efbe04165831c2d2b807ff7d3227ce6f59d2.json', 'r') as f:
        data = json.load(f)
    
    text = data['text']
    context = text[:8000]
    
    print("=" * 80)
    print("CONTEXT DEBUG")
    print("=" * 80)
    print(f"Context length: {len(context)} characters")
    
    # Look for problematic strings
    problematic_strings = [
        '"tech_maturity"', '"moat_strength"', '"tech_stack"', 
        '"product_specifications"', '"product_roadmap"', '"patent_portfolio"',
        '"complexity"', '"security"', '"implementation"', '"regulatory"', '"testing"'
    ]
    
    print("\nSearching for problematic strings in context:")
    for string in problematic_strings:
        if string in context:
            print(f"❌ Found problematic string: {string}")
            # Find the context around this string
            idx = context.find(string)
            start = max(0, idx - 50)
            end = min(len(context), idx + 50)
            print(f"   Context: ...{context[start:end]}...")
        else:
            print(f"✅ No problematic string: {string}")
    
    # Look for curly braces
    print(f"\nCurly braces count: {{: {context.count('{')}, }}: {context.count('}')}")
    
    # Check if there are any JSON-like structures in the context
    import re
    json_patterns = [
        r'\{[^}]*"[^"]*"[^}]*\}',
        r'"[^"]*"\s*:\s*"[^"]*"',
    ]
    
    print("\nSearching for JSON-like patterns:")
    for pattern in json_patterns:
        matches = re.findall(pattern, context)
        if matches:
            print(f"Found JSON-like pattern: {matches[:3]}")  # Show first 3 matches
    
    # Test the cleaning function
    print("\nTesting context cleaning:")
    clean_context = context.replace('"', "'").replace('\n', ' ').replace('{', '{{').replace('}', '}}').strip()
    print(f"Cleaned context length: {len(clean_context)}")
    print(f"Cleaned context preview: {clean_context[:200]}...")

if __name__ == "__main__":
    test_context_debug() 