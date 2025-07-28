#!/usr/bin/env python3
"""
Test to verify what context the technical agent is receiving
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context
from agents.technical_dd_agent import build_technical_dd_agent

def test_technical_context():
    """Test what context the technical agent is receiving"""
    
    # Create a test profile with the extracted StoreDot data
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Add the extracted technical data from the JSON you provided
    profile.energy_density_wh_kg = 300
    profile.cycle_life_count = 1200
    profile.patent_portfolio = "78 US granted and allowed patents, 22 US pending patents"
    profile.tech_stack = "Silicon-dominant anode, NMC811 cathode"
    profile.product_description = "Extreme fast charging battery technology"
    profile.product_roadmap = "100in5 (2024), 100in3 (2028), 100in1 (2032)"
    
    # Build the extracted data context (simulate what orchestration does)
    def build_extracted_data_context(profile, full_text):
        """Build comprehensive context from all extracted data for agents"""
        context_parts = []
        
        # Prioritize technical and key business data
        priority_fields = [
            'energy_density_wh_kg', 'cycle_life_count', 'TAM', 'SAM', 'SOM',
            'revenue', 'funding_amount', 'patents', 'employees_count',
            'tech_maturity', 'moat_strength', 'product_description'
        ]
        
        # Add priority fields first
        for field_name in priority_fields:
            try:
                value = getattr(profile, field_name)
                if value and value not in [None, '', 0, '0', 'Unknown', 'N/A']:
                    display_name = field_name.replace('_', ' ').title()
                    context_parts.append(f"**{display_name}**: {value}")
            except Exception:
                continue
        
        return "\n\n".join(context_parts)
    
    # Build the context
    extracted_context = build_extracted_data_context(profile, "StoreDot battery technology text...")
    profile.extracted_data_context = extracted_context
    
    print("=" * 80)
    print("TECHNICAL AGENT CONTEXT TEST")
    print("=" * 80)
    
    print(f"\n1. PROFILE DATA:")
    print("-" * 50)
    print(f"Name: {profile.name}")
    print(f"Sector: {profile.sector}")
    print(f"Energy Density: {getattr(profile, 'energy_density_wh_kg', 'None')}")
    print(f"Cycle Life: {getattr(profile, 'cycle_life_count', 'None')}")
    print(f"Patent Portfolio: {getattr(profile, 'patent_portfolio', 'None')}")
    print(f"Tech Stack: {getattr(profile, 'tech_stack', 'None')}")
    
    print(f"\n2. EXTRACTED DATA CONTEXT:")
    print("-" * 50)
    print(extracted_context)
    
    print(f"\n3. HYBRID CONTEXT (what technical agent receives):")
    print("-" * 50)
    hybrid_context = get_hybrid_context(profile, "technical analysis OR energy density OR cycle life OR battery technology", use_reports=False)
    print(hybrid_context)
    
    print(f"\n4. TECHNICAL AGENT CALLBACK TEST:")
    print("-" * 50)
    
    # Test the technical agent callback
    try:
        tech_agent, tech_task = build_technical_dd_agent(profile)
        print("✅ Technical agent built successfully")
        
        # Test the callback
        result = tech_task.callback()
        print("✅ Technical agent callback completed")
        
        # Parse the result
        if result:
            try:
                result_data = json.loads(result)
                print(f"Agent result keys: {list(result_data.keys())}")
                
                # Check for technical data in the result
                if 'tech_stack' in result_data:
                    print(f"  Tech Stack in result: {result_data['tech_stack']}")
                if 'product_description' in result_data:
                    print(f"  Product Description in result: {result_data['product_description']}")
                if 'patent_portfolio' in result_data:
                    print(f"  Patent Portfolio in result: {result_data['patent_portfolio']}")
                    
            except json.JSONDecodeError:
                print("Result is not valid JSON")
                print(f"Result preview: {result[:200]}...")
        
    except Exception as e:
        print(f"❌ Technical agent failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n5. CONTEXT ANALYSIS:")
    print("-" * 50)
    print(f"Extracted Context Length: {len(extracted_context)} characters")
    print(f"Hybrid Context Length: {len(hybrid_context)} characters")
    
    if "No relevant information found" in hybrid_context:
        print("❌ ISSUE: Technical agent is getting 'No relevant information found'")
        print("   This means the extracted data context is not being used properly")
    else:
        print("✅ Technical agent is receiving context properly")
    
    if "Energy Density" in hybrid_context or "300" in hybrid_context:
        print("✅ Energy density data is in the context")
    else:
        print("❌ Energy density data is missing from context")
    
    if "Cycle Life" in hybrid_context or "1200" in hybrid_context:
        print("✅ Cycle life data is in the context")
    else:
        print("❌ Cycle life data is missing from context")

if __name__ == "__main__":
    test_technical_context() 