#!/usr/bin/env python3
"""
Test to debug extraction function output
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_extraction_debug():
    """Debug what the extraction function returns."""
    
    print("🔧 Debugging Extraction Function Output")
    print("=" * 40)
    
    from core.download_utils import load_from_cache
    from chains.technical_dd_chain import extract_technical_specs_from_text
    
    # Load actual extracted data
    cache_file = "data/storedot.pdf"
    extracted = load_from_cache(cache_file)
    
    if not extracted:
        print("❌ No cached data found")
        return
    
    text = extracted.get("text", "")
    print(f"📄 Text length: {len(text)} characters")
    
    # Extract technical specs
    print("\n🔍 Extracting technical specifications...")
    tech_specs = extract_technical_specs_from_text(text)
    
    print("\n📊 Raw Extraction Output:")
    for key, value in tech_specs.items():
        print(f"   • {key}: {value}")
    
    # Check which fields should be mapped
    print("\n🔍 Field Mapping Analysis:")
    expected_mappings = {
        'energy_density': 'energy_density_wh_kg',
        'cycle_life': 'cycle_life_count',
        'volumetric_energy_density': 'volumetric_energy_density',
        'granted_patents': 'granted_patents',
        'pending_patents': 'pending_patents',
        'patent_details': 'patent_details',
        'oem_partners': 'oem_partners',
        'safety_certifications': 'safety_certifications',
        'employees_count': 'employees_count',
        'low_temp_performance': 'low_temp_performance',
        'power_performance': 'power_performance',
        'cell_capacity': 'cell_capacity'
    }
    
    for extracted_key, profile_key in expected_mappings.items():
        if extracted_key in tech_specs:
            value = tech_specs[extracted_key]
            print(f"   ✅ {extracted_key} → {profile_key}: {value}")
        else:
            print(f"   ❌ {extracted_key} → {profile_key}: Not found in extraction")
    
    return tech_specs

if __name__ == "__main__":
    test_extraction_debug() 