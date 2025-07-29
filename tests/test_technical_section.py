#!/usr/bin/env python3
"""
Test script for technical DD chain and agent with StoreDot PDF data
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.schemas import StartupProfile
from chains.technical_dd_chain import run_technical_dd_chain_with_text, extract_technical_specs_from_text
from agents.technical_dd_agent import build_technical_dd_agent, format_technical_dd_section

def test_technical_extraction():
    """Test technical specifications extraction from StoreDot PDF text"""
    print("=" * 80)
    print("TESTING TECHNICAL SPECIFICATIONS EXTRACTION")
    print("=" * 80)
    
    # Load the StoreDot PDF extracted data
    pdf_data_path = "extraction_cache/storedot.pdf_70f0efbe04165831c2d2b807ff7d3227ce6f59d2.json"
    
    try:
        with open(pdf_data_path, 'r') as f:
            pdf_data = json.load(f)
        
        pdf_text = pdf_data.get('text', '')
        print(f"PDF text length: {len(pdf_text)} characters")
        print(f"PDF text preview: {pdf_text[:200]}...")
        print()
        
        # Test technical specifications extraction
        tech_specs = extract_technical_specs_from_text(pdf_text)
        
        print("🔍 EXTRACTED TECHNICAL SPECIFICATIONS:")
        print("-" * 50)
        for key, value in tech_specs.items():
            print(f"  {key}: {value}")
        print()
        
        # Check for key technical data points
        expected_keys = [
            'energy_density', 'cycle_life', 'patents', 'charging_speed_miles',
            'charging_speed_minutes', 'cell_capacity', 'cell_format',
            'roadmap_technologies', 'employees', 'phds'
        ]
        
        print("✅ MISSING TECHNICAL DATA POINTS:")
        print("-" * 50)
        for key in expected_keys:
            if key not in tech_specs:
                print(f"  ❌ {key}: Not found")
            else:
                print(f"  ✅ {key}: {tech_specs[key]}")
        print()
        
        return tech_specs, pdf_text
        
    except Exception as e:
        print(f"❌ Error loading PDF data: {e}")
        return None, None

def test_technical_chain():
    """Test the technical DD chain with StoreDot data"""
    print("=" * 80)
    print("TESTING TECHNICAL DD CHAIN")
    print("=" * 80)
    
    tech_specs, pdf_text = test_technical_extraction()
    
    if not tech_specs or not pdf_text:
        print("❌ Cannot proceed without PDF data")
        return
    
    # Create a test profile
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    print(f"Initial profile:")
    print(f"  Name: {profile.name}")
    print(f"  Sector: {profile.sector}")
    print()
    
    # Test the chain with full text
    try:
        updated_profile = run_technical_dd_chain_with_text(pdf_text, profile)
        print("✅ Technical chain completed successfully")
        
        # Check what technical data was added
        technical_fields = [
            'tech_stack', 'product_specifications', 'product_roadmap', 'patent_portfolio',
            'complexity', 'security', 'implementation', 'regulatory', 'testing',
            'energy_density_wh_kg', 'cycle_life_count', 'charging_speed_miles',
            'energy_density_source', 'cycle_life_source'
        ]
        
        print("\n📊 TECHNICAL DATA AFTER CHAIN:")
        print("-" * 50)
        for field in technical_fields:
            value = getattr(updated_profile, field, None)
            if value:
                print(f"  ✅ {field}: {value}")
            else:
                print(f"  ❌ {field}: Not found")
        
        return updated_profile
        
    except Exception as e:
        print(f"❌ Technical chain failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_technical_agent():
    """Test the technical DD agent with StoreDot data"""
    print("=" * 80)
    print("TESTING TECHNICAL DD AGENT")
    print("=" * 80)
    
    tech_specs, pdf_text = test_technical_extraction()
    
    if not tech_specs or not pdf_text:
        print("❌ Cannot proceed without PDF data")
        return
    
    # Create a test profile with extracted data
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Pre-populate with extracted technical data
    if tech_specs.get('energy_density'):
        profile.energy_density_wh_kg = tech_specs['energy_density']
        profile.energy_density_source = 'technical_extraction'
    if tech_specs.get('cycle_life'):
        profile.cycle_life_count = tech_specs['cycle_life']
        profile.cycle_life_source = 'technical_extraction'
    if tech_specs.get('patents'):
        profile.patent_portfolio = f"{tech_specs['patents']} patents"
    
    # Set the full text context for the agent
    profile.extracted_data_context = pdf_text
    
    print(f"Initial profile with extracted data:")
    print(f"  Energy Density: {getattr(profile, 'energy_density_wh_kg', 'N/A')} Wh/kg")
    print(f"  Cycle Life: {getattr(profile, 'cycle_life_count', 'N/A')} cycles")
    print(f"  Patent Portfolio: {getattr(profile, 'patent_portfolio', 'N/A')}")
    print(f"  Extracted Data Context Length: {len(getattr(profile, 'extracted_data_context', ''))}")
    print()
    
    # Test the agent
    try:
        agent, task = build_technical_dd_agent(profile)
        print("✅ Technical agent built successfully")
        
        # Run the task
        result = task.callback()
        print("✅ Technical agent task completed")
        
        # Parse the result
        if result:
            try:
                result_data = json.loads(result)
                print(f"\n🤖 AGENT RESULT ANALYSIS:")
                print("-" * 50)
                print(f"Result keys: {list(result_data.keys())}")
                
                # Check for technical data in the result
                key_fields = ['tech_stack', 'product_specifications', 'product_roadmap', 
                            'patent_portfolio', 'tech_maturity', 'moat_strength']
                
                for field in key_fields:
                    if field in result_data:
                        value = result_data[field]
                        print(f"  ✅ {field}: {value[:100]}{'...' if len(value) > 100 else ''}")
                    else:
                        print(f"  ❌ {field}: Not found")
                        
            except json.JSONDecodeError as e:
                print(f"❌ Result is not valid JSON: {e}")
                print(f"Result preview: {result[:200]}...")
        
    except Exception as e:
        print(f"❌ Technical agent failed: {e}")
        import traceback
        traceback.print_exc()

def test_technical_formatting():
    """Test the technical section formatting"""
    print("=" * 80)
    print("TESTING TECHNICAL SECTION FORMATTING")
    print("=" * 80)
    
    # Create a profile with technical data
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Add some technical data
    profile.energy_density_wh_kg = 330
    profile.cycle_life_count = 1200
    profile.patent_portfolio = "100 patents (78 granted, 22 pending)"
    profile.tech_maturity = "Production-ready technology with 3-5 year lead"
    profile.moat_strength = "Strong IP portfolio with 100+ patents covering core technology"
    profile.tech_stack = "Silicon-dominant anode battery technology with proprietary additives and cell design"
    profile.product_specifications = "100 miles charged in 5 minutes, >1000 consecutive XFC cycles, 330 Wh/kg energy density"
    profile.product_roadmap = "100in5 production-ready in 2024, 100in3 by 2028, post-lithium by 2032"
    
    print("📝 FORMATTED TECHNICAL SECTION:")
    print("-" * 50)
    
    try:
        formatted_section = format_technical_dd_section(profile)
        print(formatted_section)
        
        # Check if key sections are present
        key_sections = [
            "Technical Maturity", "Moat Strength", "Technical Specifications",
            "Product Roadmap", "Patent Portfolio"
        ]
        
        print(f"\n✅ SECTION COMPLETENESS CHECK:")
        print("-" * 50)
        for section in key_sections:
            if section.lower() in formatted_section.lower():
                print(f"  ✅ {section}: Found")
            else:
                print(f"  ❌ {section}: Missing")
                
    except Exception as e:
        print(f"❌ Formatting failed: {e}")
        import traceback
        traceback.print_exc()

def test_context_verification():
    """Test that the agent gets the full PDF context"""
    print("=" * 80)
    print("TESTING CONTEXT VERIFICATION")
    print("=" * 80)
    
    tech_specs, pdf_text = test_technical_extraction()
    
    if not pdf_text:
        print("❌ Cannot proceed without PDF data")
        return
    
    # Create a test profile
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Set the full text context
    profile.extracted_data_context = pdf_text
    
    print(f"Profile context length: {len(getattr(profile, 'extracted_data_context', ''))}")
    print(f"Context preview: {getattr(profile, 'extracted_data_context', '')[:200]}...")
    
    # Test the hybrid context function
    from core.hybrid_context import get_hybrid_context
    
    context = get_hybrid_context(profile, "technical analysis", use_reports=False)
    print(f"\nHybrid context length: {len(context)}")
    print(f"Hybrid context preview: {context[:200]}...")
    
    if "No relevant information found" in context:
        print("❌ Hybrid context returned 'No relevant information found'")
    else:
        print("✅ Hybrid context contains information")

def main():
    """Run all technical DD tests"""
    print("🚀 STOREDOT TECHNICAL DD TESTING SUITE")
    print("=" * 80)
    
    # Test 1: Technical specifications extraction
    test_technical_extraction()
    
    print("\n" + "=" * 80)
    
    # Test 2: Technical DD chain
    test_technical_chain()
    
    print("\n" + "=" * 80)
    
    # Test 3: Technical DD agent
    test_technical_agent()
    
    print("\n" + "=" * 80)
    
    # Test 4: Technical section formatting
    test_technical_formatting()
    
    print("\n" + "=" * 80)
    
    # Test 5: Context verification
    test_context_verification()
    
    print("\n" + "=" * 80)
    print("🎉 TECHNICAL DD TESTING COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main() 