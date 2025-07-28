#!/usr/bin/env python3
"""
Test script for technical DD agent and chain
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.schemas import StartupProfile
from chains.technical_dd_chain import run_technical_dd_chain
from agents.technical_dd_agent import build_technical_dd_agent, format_technical_dd_section
from core.download_utils import load_from_cache

def test_technical_chain():
    """Test the technical DD chain directly"""
    print("=" * 60)
    print("TESTING TECHNICAL DD CHAIN")
    print("=" * 60)
    
    # Create a test profile with some data
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Add some test technical data
    profile.energy_density_wh_kg = 300
    profile.cycle_life_count = 1200
    profile.patent_portfolio = "15 patents covering battery technology"
    profile.energy_density_source = "enhanced_extraction"
    profile.cycle_life_source = "enhanced_extraction"
    
    print(f"Initial profile:")
    print(f"  Energy Density: {profile.energy_density_wh_kg} Wh/kg")
    print(f"  Cycle Life: {profile.cycle_life_count} cycles")
    print(f"  Patent Portfolio: {profile.patent_portfolio}")
    print()
    
    # Test the chain
    try:
        updated_profile = run_technical_dd_chain(profile)
        print("✅ Technical chain completed successfully")
        print(f"Updated profile has {len(updated_profile.model_fields)} fields")
        
        # Check what technical data was added
        technical_fields = [
            'tech_stack', 'product_description', 'product_roadmap', 'patent_portfolio',
            'complexity', 'security', 'implementation', 'regulatory', 'testing',
            'product_specifications', 'energy_density_wh_kg', 'cycle_life_count',
            'energy_density_source', 'cycle_life_source'
        ]
        
        print("\nTechnical data after chain:")
        for field in technical_fields:
            value = getattr(updated_profile, field, None)
            if value:
                print(f"  {field}: {value}")
        
    except Exception as e:
        print(f"❌ Technical chain failed: {e}")
        import traceback
        traceback.print_exc()

def test_technical_agent():
    """Test the technical DD agent directly"""
    print("\n" + "=" * 60)
    print("TESTING TECHNICAL DD AGENT")
    print("=" * 60)
    
    # Create a test profile
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Add some test data
    profile.energy_density_wh_kg = 300
    profile.cycle_life_count = 1200
    profile.patent_portfolio = "15 patents covering battery technology"
    
    print(f"Initial profile:")
    print(f"  Energy Density: {profile.energy_density_wh_kg} Wh/kg")
    print(f"  Cycle Life: {profile.cycle_life_count} cycles")
    print(f"  Patent Portfolio: {profile.patent_portfolio}")
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

def test_technical_formatting():
    """Test the technical formatting function"""
    print("\n" + "=" * 60)
    print("TESTING TECHNICAL FORMATTING")
    print("=" * 60)
    
    # Create test profiles with different scenarios
    test_cases = [
        {
            "name": "Profile with technical data",
            "profile": StartupProfile(
                name="StoreDot",
                sector="Battery Technology",
                energy_density_wh_kg=300,
                cycle_life_count=1200,
                patent_portfolio="15 patents covering battery technology",
                tech_stack="Lithium-ion battery technology, solid-state electrolytes",
                product_description="Fast-charging battery technology",
                product_roadmap="Phase 1: Prototype, Phase 2: Pilot, Phase 3: Production"
            )
        },
        {
            "name": "Profile with no technical data",
            "profile": StartupProfile(
                name="StoreDot",
                sector="Battery Technology"
            )
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_case['name']} ---")
        profile = test_case['profile']
        
        print(f"Input data:")
        print(f"  Energy Density: {getattr(profile, 'energy_density_wh_kg', 'None')}")
        print(f"  Cycle Life: {getattr(profile, 'cycle_life_count', 'None')}")
        print(f"  Patent Portfolio: {getattr(profile, 'patent_portfolio', 'None')}")
        print(f"  Tech Stack: {getattr(profile, 'tech_stack', 'None')}")
        
        # Test the formatting
        try:
            formatted = format_technical_dd_section(profile)
            print(f"\nFormatted output:")
            print(formatted)
            print(f"Output length: {len(formatted)} characters")
            
        except Exception as e:
            print(f"❌ Formatting failed: {e}")
            import traceback
            traceback.print_exc()

def test_technical_section_generation():
    """Test the full technical section generation"""
    print("\n" + "=" * 60)
    print("TESTING TECHNICAL SECTION GENERATION")
    print("=" * 60)
    
    # Create test profiles
    test_cases = [
        {
            "name": "Profile with technical data",
            "profile": StartupProfile(
                name="StoreDot",
                sector="Battery Technology",
                energy_density_wh_kg=300,
                cycle_life_count=1200,
                patent_portfolio="15 patents covering battery chemistry and charging technology",
                tech_stack="Lithium-ion battery technology, solid-state electrolytes",
                product_description="Fast-charging battery technology with 5-minute charge capability",
                product_roadmap="Phase 1: Prototype (2024), Phase 2: Pilot (2025), Phase 3: Production (2026)",
                complexity="High - Advanced battery chemistry and manufacturing processes",
                security="IP protection through patents and trade secrets",
                implementation="Requires specialized manufacturing facilities and expertise",
                regulatory="Must comply with battery safety standards and transportation regulations",
                testing="Extensive safety and performance testing required"
            )
        },
        {
            "name": "Profile with minimal technical data",
            "profile": StartupProfile(
                name="StoreDot",
                sector="Battery Technology",
                energy_density_wh_kg=300
            )
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_case['name']} ---")
        profile = test_case['profile']
        
        print(f"Input data:")
        print(f"  Energy Density: {getattr(profile, 'energy_density_wh_kg', 'None')}")
        print(f"  Cycle Life: {getattr(profile, 'cycle_life_count', 'None')}")
        print(f"  Patent Portfolio: {getattr(profile, 'patent_portfolio', 'None')}")
        print(f"  Tech Stack: {getattr(profile, 'tech_stack', 'None')}")
        
        # Test the technical section generation
        try:
            technical_section = format_technical_dd_section(profile)
            print(f"\nTechnical section output:")
            print(technical_section)
            print(f"Output length: {len(technical_section)} characters")
            
            # Check if extracted technical specs are included
            if "300 Wh/kg" in technical_section or "300" in technical_section:
                print("✅ Energy density correctly included")
            else:
                print("⚠️  Energy density not found in output")
                
            if "1200" in technical_section or "cycle" in technical_section.lower():
                print("✅ Cycle life correctly included")
            else:
                print("⚠️  Cycle life not found in output")
                
        except Exception as e:
            print(f"❌ Technical section generation failed: {e}")
            import traceback
            traceback.print_exc()

def test_with_real_data():
    """Test with real extracted data from StoreDot"""
    print("\n" + "=" * 60)
    print("TESTING WITH REAL STOREDOT DATA")
    print("=" * 60)
    
    # Try to load cached StoreDot data
    cache_file = "extraction_cache/storedot.pdf_70f0efbe04165831c2d2b807ff7d3227ce6f59d2.json"
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                extracted_data = json.load(f)
            
            print("✅ Loaded cached StoreDot data")
            text = extracted_data.get('text', '')
            print(f"Text length: {len(text)} characters")
            
            # Create profile with real data
            profile = StartupProfile()
            profile.name = "StoreDot"
            profile.sector = "Battery Technology"
            
            # Extract technical specifications directly from text
            from chains.technical_dd_chain import extract_technical_specs_from_text
            tech_specs = extract_technical_specs_from_text(text)
            
            print(f"Extracted technical specs: {tech_specs}")
            
            # Map extracted data to profile
            if tech_specs.get('energy_density'):
                profile.energy_density_wh_kg = tech_specs['energy_density']
                profile.energy_density_source = "technical_extraction"
            if tech_specs.get('cycle_life'):
                profile.cycle_life_count = tech_specs['cycle_life']
                profile.cycle_life_source = "technical_extraction"
            if tech_specs.get('patents'):
                profile.patent_portfolio = f"{tech_specs['patents']} patents covering battery technology"
            
            # Add additional extracted specs
            if tech_specs.get('charging_speed_miles') and tech_specs.get('charging_speed_minutes'):
                profile.charging_speed_miles = tech_specs['charging_speed_miles']
                profile.charging_speed_minutes = tech_specs['charging_speed_minutes']
            if tech_specs.get('low_temp_performance'):
                profile.low_temp_performance = tech_specs['low_temp_performance']
            if tech_specs.get('cell_capacity'):
                profile.cell_capacity = tech_specs['cell_capacity']
            if tech_specs.get('cell_dimensions'):
                profile.cell_dimensions = tech_specs['cell_dimensions']
            if tech_specs.get('charging_power'):
                profile.charging_power = tech_specs['charging_power']
            if tech_specs.get('power_performance'):
                profile.power_performance = tech_specs['power_performance']
            if tech_specs.get('employees'):
                profile.employees_count = tech_specs['employees']
            if tech_specs.get('phds'):
                profile.phds = tech_specs['phds']
            if tech_specs.get('professionals'):
                profile.professionals = tech_specs['professionals']
            if tech_specs.get('roadmap_100in_speed') and tech_specs.get('roadmap_100in_year'):
                profile.roadmap_100in_speed = tech_specs['roadmap_100in_speed']
                profile.roadmap_100in_year = tech_specs['roadmap_100in_year']
            if tech_specs.get('roadmap_technologies'):
                profile.roadmap_technologies = tech_specs['roadmap_technologies']
            if tech_specs.get('roadmap_production_year'):
                profile.roadmap_production_year = tech_specs['roadmap_production_year']
            
            print(f"\nProfile with real data:")
            print(f"  Energy Density: {getattr(profile, 'energy_density_wh_kg', 'None')}")
            print(f"  Cycle Life: {getattr(profile, 'cycle_life_count', 'None')}")
            print(f"  Patent Portfolio: {getattr(profile, 'patent_portfolio', 'None')}")
            print(f"  Charging Speed: {getattr(profile, 'charging_speed_miles', 'None')} miles in {getattr(profile, 'charging_speed_minutes', 'None')} minutes")
            print(f"  Team Size: {getattr(profile, 'employees_count', 'None')} employees")
            print(f"  Roadmap: {getattr(profile, 'roadmap_technologies', 'None')}")
            
            # Test technical section generation
            technical_section = format_technical_dd_section(profile)
            print(f"\nTechnical section with real data:")
            print(technical_section)
            
        except Exception as e:
            print(f"❌ Failed to process real data: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ No cached StoreDot data found")

if __name__ == "__main__":
    print("🧪 Testing Technical DD Components")
    print("=" * 60)
    
    # Test the chain
    test_technical_chain()
    
    # Test the agent
    test_technical_agent()
    
    # Test the formatting
    test_technical_formatting()
    
    # Test technical section generation
    test_technical_section_generation()
    
    # Test with real data
    test_with_real_data()
    
    print("\n" + "=" * 60)
    print("✅ Testing completed!")
    print("=" * 60) 