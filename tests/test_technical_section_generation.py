#!/usr/bin/env python3
"""
Test script to simulate technical section generation from main.py using real extracted data
"""

import sys
import os
# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_technical_section_generation():
    """Test the technical section generation process using real extracted data."""
    
    print("🔧 Testing Technical Section Generation with Real Data")
    print("=" * 60)
    
    # Import necessary modules
    from core.schemas import StartupProfile
    from agents.technical_dd_agent import format_technical_dd_section
    from chains.technical_dd_chain import run_technical_dd_chain
    from core.download_utils import load_from_cache
    from core.hybrid_context import get_hybrid_context
    
    # Create a profile like main.py does
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Load actual extracted data from cache (like main.py does)
    cache_file = "data/storedot.pdf"
    extracted = load_from_cache(cache_file)
    
    if extracted:
        print("✅ Loaded extracted data from cache")
        text = extracted.get("text", "")
        tables = extracted.get("tables", [])
        figures = extracted.get("figures", [])
        
        # Set the full text context (like main.py does)
        profile._full_text = text
        profile.tables = tables
        profile.figures = figures
        
        # Add structured data if available
        structured_data = extracted.get("structured_data", {})
        if structured_data:
            print(f"📊 Found structured data: {list(structured_data.keys())}")
            profile.structured_data = structured_data
            
            # Map key fields from structured data
            field_mapping = {
                'market_size': 'TAM',
                'funding': 'funding_amount', 
                'patents': 'patent_count',
                'employees': 'employees_count',
                'energy_density': 'energy_density_wh_kg',
                'cycle_life': 'cycle_life_count'
            }
            
            for source_key, profile_key in field_mapping.items():
                if source_key in structured_data and hasattr(profile, profile_key):
                    value = structured_data[source_key]
                    setattr(profile, profile_key, value)
                    print(f"   • Set {profile_key} = {value}")
        
        print(f"\n📄 Text length: {len(text)} characters")
        print(f"📊 Tables found: {len(tables)}")
        print(f"🖼️ Figures found: {len(figures)}")
        
    else:
        print("❌ No cached data found, using sample data")
        # Fallback to sample data if no cache
        profile._full_text = "StoreDot extreme fast charging battery technology 100in5 charging speed"
    
    print("\n🔍 Running Technical DD Chain with Real Context...")
    try:
        # Run the technical DD chain with the real extracted text
        profile = run_technical_dd_chain(profile)
        print("✅ Technical DD Chain completed")
    except Exception as e:
        print(f"❌ Error in Technical DD Chain: {e}")
    
    print("\n📝 Generating Technical Section...")
    try:
        # Generate the technical section
        technical_section = format_technical_dd_section(profile)
        print("✅ Technical Section generated")
        
        print("\n📄 Generated Technical Section:")
        print("-" * 50)
        print(technical_section)
        print("-" * 50)
        
        # Check for issues
        issues = []
        
        # Check for duplicate headers
        if technical_section.count("Technical Due Diligence") > 1:
            issues.append("❌ Duplicate 'Technical Due Diligence' headers found")
        
        # Check for generic language
        generic_phrases = [
            "not detailed in the provided context",
            "not explicitly detailed",
            "not available",
            "suggesting a need for",
            "may include",
            "appears to be",
            "require additional research",
            "unavailable"
        ]
        
        generic_count = sum(1 for phrase in generic_phrases if phrase in technical_section)
        if generic_count > 3:
            issues.append(f"❌ Too many generic phrases ({generic_count} found)")
        
        # Check for technical specifications
        tech_specs = [
            "Energy Density", "Cycle Life", "Charging Speed", "Cell Capacity",
            "Volumetric Energy Density", "Patent Portfolio", "OEM Partners",
            "Safety Certifications", "Employees", "Low Temperature Performance"
        ]
        
        found_specs = []
        for spec in tech_specs:
            if spec.lower() in technical_section.lower():
                found_specs.append(spec)
        
        if found_specs:
            print(f"\n✅ Found technical specifications: {', '.join(found_specs)}")
        else:
            issues.append("❌ No technical specifications found")
        
        print("\n🔍 Analysis Results:")
        if issues:
            for issue in issues:
                print(f"   {issue}")
        else:
            print("   ✅ No major issues detected")
        
        return technical_section
        
    except Exception as e:
        print(f"❌ Error generating technical section: {e}")
        return None

if __name__ == "__main__":
    test_technical_section_generation() 