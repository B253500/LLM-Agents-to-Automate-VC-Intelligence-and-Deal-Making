#!/usr/bin/env python3
"""
Test script to debug technical data extraction from real document
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_technical_extraction_debug():
    """Debug what technical data is being extracted from the real document."""
    
    print("🔧 Debugging Technical Data Extraction")
    print("=" * 50)
    
    from core.download_utils import load_from_cache
    from core.schemas import StartupProfile
    from chains.technical_dd_chain import extract_technical_specs_from_text
    
    # Load actual extracted data
    cache_file = "data/storedot.pdf"
    extracted = load_from_cache(cache_file)
    
    if not extracted:
        print("❌ No cached data found")
        return
    
    text = extracted.get("text", "")
    print(f"📄 Text length: {len(text)} characters")
    
    # Extract technical specs from the real text
    print("\n🔍 Extracting technical specifications from real text...")
    technical_specs = extract_technical_specs_from_text(text)
    
    print("\n📊 Extracted Technical Specifications:")
    for key, value in technical_specs.items():
        if value is not None:
            print(f"   ✅ {key}: {value}")
        else:
            print(f"   ❌ {key}: Not found")
    
    # Check what's in the structured data
    structured_data = extracted.get("structured_data", {})
    if structured_data:
        print(f"\n📊 Structured Data Found:")
        for key, value in structured_data.items():
            print(f"   • {key}: {value}")
    
    # Create a profile and set the extracted data
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    profile._full_text = text
    
    # Set the extracted technical specs on the profile
    for key, value in technical_specs.items():
        if hasattr(profile, key) and value is not None:
            setattr(profile, key, value)
            print(f"   ✅ Set {key} = {value}")
    
    # Check what technical fields are populated
    print(f"\n🔍 Profile Technical Fields:")
    technical_fields = [
        'energy_density_wh_kg', 'cycle_life_count', 'charging_speed_miles',
        'charging_speed_minutes', 'volumetric_energy_density', 'granted_patents',
        'pending_patents', 'oem_partners', 'safety_certifications', 'employees_count',
        'low_temp_performance', 'power_performance', 'cell_capacity'
    ]
    
    for field in technical_fields:
        value = getattr(profile, field, None)
        if value is not None:
            print(f"   ✅ {field}: {value}")
        else:
            print(f"   ❌ {field}: Not set")
    
    return profile

if __name__ == "__main__":
    test_technical_extraction_debug() 