#!/usr/bin/env python3
"""
Test script to demonstrate how extracted context generation works
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.schemas import StartupProfile
from core.orchestration import build_extracted_data_context
from core.hybrid_context import get_hybrid_context

def test_context_generation():
    """Test how extracted context is generated"""
    
    # Create a sample profile with extracted data
    profile = StartupProfile()
    
    # Simulate extracted data from enhanced extraction
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    profile.revenue = 5000000  # $5M revenue
    profile.funding_amount = 100000000  # $100M funding
    profile.energy_density_wh_kg = 450  # 450 Wh/kg
    profile.cycle_life_count = 1000  # 1000 cycles
    profile.patent_count = 25  # 25 patents
    profile.employees_count = 150  # 150 employees
    profile.TAM = 160000000000  # $160B TAM
    profile.SAM = 32000000000   # $32B SAM
    profile.SOM = 8000000000    # $8B SOM
    
    # Simulate structured data from enhanced extraction
    profile.structured_data = {
        "market_size": 160000000000,
        "funding": 100000000,
        "patents": 25,
        "employees": 150,
        "energy_density": 450,
        "cycle_life": 1000
    }
    
    # Simulate extracted text
    full_text = """
    StoreDot is a battery technology company developing fast-charging batteries.
    The company has raised $100M in funding and has 25 patents.
    Their batteries achieve 450 Wh/kg energy density and 1000 cycle life.
    The total addressable market is $160 billion.
    """
    
    print("=" * 60)
    print("EXTRACTED CONTEXT GENERATION TEST")
    print("=" * 60)
    
    # Test 1: Build extracted data context
    print("\n1. BUILDING EXTRACTED DATA CONTEXT:")
    print("-" * 40)
    extracted_context = build_extracted_data_context(profile, full_text)
    print(f"Context length: {len(extracted_context)} characters")
    print("\nContext content:")
    print(extracted_context)
    
    # Test 2: Get hybrid context for different topics
    print("\n\n2. HYBRID CONTEXT FOR DIFFERENT TOPICS:")
    print("-" * 40)
    
    topics = [
        "financial analysis",
        "technical analysis", 
        "market sizing",
        "competitive landscape"
    ]
    
    for topic in topics:
        print(f"\n--- {topic.upper()} ---")
        hybrid_context = get_hybrid_context(profile, topic, use_reports=False)
        print(f"Context length: {len(hybrid_context)} characters")
        print(f"First 200 chars: {hybrid_context[:200]}...")
    
    # Test 3: Show what data is prioritized
    print("\n\n3. DATA PRIORITIZATION:")
    print("-" * 40)
    print("Priority fields (shown first in context):")
    priority_fields = [
        'energy_density_wh_kg', 'cycle_life_count', 'TAM', 'SAM', 'SOM',
        'revenue', 'funding_amount', 'patents', 'employees_count',
        'tech_maturity', 'moat_strength', 'product_description'
    ]
    
    for field in priority_fields:
        value = getattr(profile, field, None)
        if value:
            print(f"  ✓ {field}: {value}")
        else:
            print(f"  ✗ {field}: Not available")
    
    print("\n\n4. CONTEXT QUALITY ASSESSMENT:")
    print("-" * 40)
    
    # Check if technical data is present
    technical_keywords = ['energy density', 'cycle life', 'wh/kg', 'cycles']
    technical_found = any(keyword in extracted_context.lower() for keyword in technical_keywords)
    print(f"Technical data present: {'✓' if technical_found else '✗'}")
    
    # Check if financial data is present
    financial_keywords = ['revenue', 'funding', 'patents', 'employees']
    financial_found = any(keyword in extracted_context.lower() for keyword in financial_keywords)
    print(f"Financial data present: {'✓' if financial_found else '✗'}")
    
    # Check if market data is present
    market_keywords = ['tam', 'sam', 'som', 'market']
    market_found = any(keyword in extracted_context.lower() for keyword in market_keywords)
    print(f"Market data present: {'✓' if market_found else '✗'}")
    
    # Check context length
    print(f"Context length: {len(extracted_context)} characters")
    print(f"Context quality: {'Good' if len(extracted_context) > 500 else 'Poor'}")

if __name__ == "__main__":
    test_context_generation() 