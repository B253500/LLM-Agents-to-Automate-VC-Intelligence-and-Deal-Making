#!/usr/bin/env python3
"""
Test script to see what the technical DD section actually outputs
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schemas import StartupProfile
from agents.technical_dd_agent import format_technical_dd_section

def test_technical_output():
    """Test what the technical DD section actually outputs"""
    
    # Create a comprehensive mock profile with all the data the agent receives
    profile_data = {
        "name": "StoreDot",
        "sector": "Battery Technology",
        "website": "https://storedot.com",
        "TAM": 160.0,
        "patent_count": 100,
        "energy_density_wh_kg": 330,
        "cycle_life_count": 1000,
        "technical_maturity": "Early-stage prototype",
        "moat_strength": "Strong",
        "complexity": "High",
        "security": "Transport safety certified (UN38.3)",
        "implementation": "Manufacturing partnerships with 15+ OEMs",
        "regulatory": "EV battery safety standards compliance",
        "testing": ">1000 consecutive XFC cycles validated",
        
        # Additional technical fields that the function looks for
        "tech_maturity": "Early-stage prototype",
        "tech_stack": "Silicon-dominant anode, Proprietary additives, Standard Li-ion manufacturing",
        "product_specifications": "Energy density: 330 Wh/kg, Cycle life: >1000 XFC cycles, Charging: 100 miles in 5 minutes",
        "product_roadmap": "2024: Production readiness, 2028: 100in3 technology, 2032: Post-lithium solutions",
        "patent_portfolio": "78 US granted and 22 US pending patents covering anodes, cathodes, electrolytes, binders, separators, production processes, and systems",
        "volumetric_energy_density": 740,
        "charging_speed_miles": 100,
        "charging_speed_minutes": 5,
        "low_temp_performance": "76% discharge capacity @ -20°C",
        "power_performance": "92% discharge capacity @ 3C",
        "cell_capacity": 30,
        "cell_dimensions": "300x100mm pouch",
        "employees_count": 130,
        "phds": 40,
        "oem_partners": 15,
        "safety_certifications": "UN38.3 PASSED",
        "roadmap_100in_speed": 3,
        "roadmap_100in_year": 2028,
        "production_readiness": "Commercially ready in 2025",
        "granted_patents": 78,
        "pending_patents": 22,
        
        # Technical DD narrative from agent
        "technical_dd_narrative": "StoreDot's XFC technology represents a significant advancement in battery technology with proven performance metrics and strong IP protection."
    }
    
    profile = StartupProfile(**profile_data)
    
    print("🔍 Testing Technical DD Section Output")
    print("=" * 60)
    
    print(f"📊 Available Profile Data:")
    technical_fields = [
        'energy_density_wh_kg', 'cycle_life_count', 'patent_count',
        'technical_maturity', 'moat_strength', 'complexity', 'security',
        'implementation', 'regulatory', 'testing', 'tech_stack',
        'product_specifications', 'product_roadmap', 'patent_portfolio',
        'volumetric_energy_density', 'charging_speed_miles', 'charging_speed_minutes',
        'low_temp_performance', 'power_performance', 'cell_capacity',
        'cell_dimensions', 'employees_count', 'phds', 'oem_partners',
        'safety_certifications', 'roadmap_100in_speed', 'roadmap_100in_year',
        'production_readiness', 'granted_patents', 'pending_patents'
    ]
    
    for field in technical_fields:
        value = getattr(profile, field, None)
        if value:
            print(f"   ✅ {field}: {value}")
        else:
            print(f"   ❌ {field}: Missing")
    
    print(f"\n📄 Generated Technical DD Section:")
    print("-" * 40)
    
    # Generate the technical DD section
    technical_section = format_technical_dd_section(profile)
    
    print(technical_section)
    
    print(f"\n📊 Output Analysis:")
    print(f"   - Total characters: {len(technical_section)}")
    print(f"   - Estimated tokens: {len(technical_section) // 4}")
    print(f"   - Lines of content: {len(technical_section.split(chr(10)))}")
    
    # Check what specific information is included
    output_lower = technical_section.lower()
    
    key_info_checks = [
        ("energy density", "energy density" in output_lower),
        ("cycle life", "cycle life" in output_lower),
        ("patent", "patent" in output_lower),
        ("charging speed", "charging speed" in output_lower),
        ("technical maturity", "technical maturity" in output_lower),
        ("moat strength", "moat strength" in output_lower),
        ("complexity", "complexity" in output_lower),
        ("security", "security" in output_lower),
        ("implementation", "implementation" in output_lower),
        ("regulatory", "regulatory" in output_lower),
        ("testing", "testing" in output_lower),
        ("product specifications", "product technical specifications" in output_lower),
        ("product roadmap", "product roadmap" in output_lower),
        ("patent portfolio", "patent portfolio" in output_lower)
    ]
    
    print(f"\n🔍 Information Coverage:")
    for info, found in key_info_checks:
        status = "✅" if found else "❌"
        print(f"   {status} {info}")
    
    print(f"\n✅ Test completed successfully!")

if __name__ == "__main__":
    test_technical_output() 