#!/usr/bin/env python3
"""
Final debug test to see what technical data is being set and displayed
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_technical_section_debug_final():
    """Final debug to see what technical data is being set and displayed."""
    
    print("🔧 Final Technical Section Debug")
    print("=" * 40)
    
    from core.schemas import StartupProfile
    from agents.technical_dd_agent import format_technical_dd_section
    from chains.technical_dd_chain import run_technical_dd_chain
    from core.download_utils import load_from_cache
    
    # Create profile and load real data
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Load actual extracted data
    cache_file = "data/storedot.pdf"
    extracted = load_from_cache(cache_file)
    
    if extracted:
        text = extracted.get("text", "")
        profile._full_text = text
        
        print("✅ Loaded real extracted data")
        print(f"📄 Text length: {len(text)} characters")
    
    # Run technical DD chain
    print("\n🔍 Running Technical DD Chain...")
    profile = run_technical_dd_chain(profile)
    
    # Check what technical fields are populated
    print("\n📊 Technical Fields After Chain:")
    technical_fields = [
        'energy_density_wh_kg', 'cycle_life_count', 'charging_speed_miles',
        'charging_speed_minutes', 'volumetric_energy_density', 'granted_patents',
        'pending_patents', 'patent_details', 'oem_partners', 'safety_certifications', 
        'employees_count', 'low_temp_performance', 'power_performance', 'cell_capacity'
    ]
    
    populated_fields = []
    for field in technical_fields:
        value = getattr(profile, field, None)
        if value is not None:
            print(f"   ✅ {field}: {value}")
            populated_fields.append(field)
        else:
            print(f"   ❌ {field}: Not set")
    
    print(f"\n📈 Summary: {len(populated_fields)}/{len(technical_fields)} fields populated")
    
    # Generate technical section
    print("\n📝 Generating Technical Section...")
    technical_section = format_technical_dd_section(profile)
    
    print("\n📄 Generated Technical Section:")
    print("-" * 40)
    print(technical_section)
    print("-" * 40)
    
    # Check what technical specs are actually displayed
    print("\n🔍 Technical Specifications Found in Output:")
    tech_specs_to_find = [
        "Energy Density", "Cycle Life", "Charging Speed", "Cell Capacity",
        "Volumetric Energy Density", "Patent Portfolio", "OEM Partners",
        "Safety Certifications", "Employees", "Low Temperature Performance",
        "Power Performance"
    ]
    
    found_specs = []
    for spec in tech_specs_to_find:
        if spec.lower() in technical_section.lower():
            found_specs.append(spec)
            print(f"   ✅ {spec}")
        else:
            print(f"   ❌ {spec}")
    
    print(f"\n📊 Display Summary: {len(found_specs)}/{len(tech_specs_to_find)} specs displayed")
    
    # Check for issues
    issues = []
    
    # Check for duplicate headers
    if technical_section.count("Technical Due Diligence") > 1:
        issues.append("❌ Duplicate headers found")
    
    # Check for generic language
    generic_phrases = [
        "require additional research", "unavailable", "not available"
    ]
    
    generic_count = sum(1 for phrase in generic_phrases if phrase in technical_section)
    if generic_count > 2:
        issues.append(f"❌ Too many generic phrases ({generic_count})")
    
    print(f"\n🔍 Issues Found:")
    if issues:
        for issue in issues:
            print(f"   {issue}")
    else:
        print("   ✅ No major issues detected")
    
    return technical_section

if __name__ == "__main__":
    test_technical_section_debug_final() 