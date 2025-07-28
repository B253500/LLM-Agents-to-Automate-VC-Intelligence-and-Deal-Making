#!/usr/bin/env python3
"""
Test script to see what the LLM-based technical analysis generates from StoreDot document
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.technical_dd_chain import run_technical_dd_chain_with_text
from core.schemas import StartupProfile

def test_technical_llm_analysis():
    """Test what the LLM-based technical analysis generates from StoreDot document"""
    
    # Load the extracted StoreDot document
    with open('extraction_cache/storedot.pdf_70f0efbe04165831c2d2b807ff7d3227ce6f59d2.json', 'r') as f:
        data = json.load(f)
    
    text = data['text']
    print("=" * 80)
    print("LLM-BASED TECHNICAL ANALYSIS TEST")
    print("=" * 80)
    print(f"Document length: {len(text)} characters")
    print()
    
    # Create a test profile
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Run the technical DD chain with the full text
    print("Running technical DD chain with full text...")
    updated_profile = run_technical_dd_chain_with_text(text, profile)
    
    print()
    print("TECHNICAL ANALYSIS RESULTS:")
    print("-" * 50)
    
    # Check what technical fields were populated
    technical_fields = [
        'tech_maturity', 'moat_strength', 'tech_stack', 'product_specifications',
        'product_roadmap', 'patent_portfolio', 'complexity', 'security', 
        'implementation', 'regulatory', 'testing'
    ]
    
    for field in technical_fields:
        value = getattr(updated_profile, field, None)
        if value:
            print(f"✅ {field}: {value}")
        else:
            print(f"❌ {field}: NOT POPULATED")
    
    print()
    print("EXTRACTED TECHNICAL SPECIFICATIONS:")
    print("-" * 50)
    
    # Check extracted technical specifications
    tech_specs = [
        'energy_density_wh_kg', 'cycle_life_count', 'patent_portfolio',
        'charging_speed_miles', 'charging_speed_minutes', 'cell_capacity',
        'cell_dimensions', 'low_temp_performance'
    ]
    
    for field in tech_specs:
        value = getattr(updated_profile, field, None)
        if value:
            print(f"✅ {field}: {value}")
        else:
            print(f"❌ {field}: NOT POPULATED")

if __name__ == "__main__":
    test_technical_llm_analysis() 