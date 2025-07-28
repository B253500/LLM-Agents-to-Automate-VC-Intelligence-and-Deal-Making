#!/usr/bin/env python3
"""
Test script to see what technical specifications are being extracted from StoreDot document
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.technical_dd_chain import extract_technical_specs_from_text

def test_technical_extraction():
    """Test what technical specifications are extracted from StoreDot document"""
    
    # Load the extracted StoreDot document
    with open('extraction_cache/storedot.pdf_70f0efbe04165831c2d2b807ff7d3227ce6f59d2.json', 'r') as f:
        data = json.load(f)
    
    text = data['text']
    print("=" * 80)
    print("TECHNICAL SPECIFICATIONS EXTRACTION TEST")
    print("=" * 80)
    print(f"Document length: {len(text)} characters")
    print(f"Document preview: {text[:500]}...")
    print()
    
    # Test the extraction function
    specs = extract_technical_specs_from_text(text)
    
    print("EXTRACTED TECHNICAL SPECIFICATIONS:")
    print("-" * 50)
    for key, value in specs.items():
        print(f"{key}: {value}")
    
    print()
    print("MISSING INFORMATION ANALYSIS:")
    print("-" * 50)
    
    # Check what key information should be extracted
    expected_keys = [
        'energy_density', 'cycle_life', 'patents', 'charging_speed_miles', 
        'charging_speed_minutes', 'cell_capacity', 'cell_format', 'roadmap_technologies'
    ]
    
    for key in expected_keys:
        if key in specs:
            print(f"✅ {key}: {specs[key]}")
        else:
            print(f"❌ {key}: NOT FOUND")
    
    print()
    print("KEY TECHNICAL DATA FOUND IN DOCUMENT:")
    print("-" * 50)
    
    # Look for specific technical data in the text
    key_phrases = [
        "energy density", "cycle life", "patents", "charging", "100in", 
        "cell", "temperature", "performance", "roadmap"
    ]
    
    for phrase in key_phrases:
        if phrase.lower() in text.lower():
            # Find the context around this phrase
            idx = text.lower().find(phrase.lower())
            start = max(0, idx - 100)
            end = min(len(text), idx + 100)
            context = text[start:end]
            print(f"Found '{phrase}' in context: ...{context}...")
        else:
            print(f"❌ '{phrase}' NOT FOUND in document")

if __name__ == "__main__":
    test_technical_extraction() 