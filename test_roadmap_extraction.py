#!/usr/bin/env python3

from core.schemas import StartupProfile
from chains.technical_dd_chain import run_technical_dd_chain

def test_roadmap_extraction():
    """Test roadmap extraction with generic system"""
    
    # Create a profile with extracted data context
    profile = StartupProfile()
    profile.name = 'TestCompany'
    profile.extracted_data_context = '''TestCompany Advanced Battery Technology. 
    Energy density >300 Wh/kg. Cycle life >1200 cycles. 
    100 miles charged in 5 minutes. 
    100in5 technology by 2024. 100in3 technology by 2028. 
    100 patents. 130 employees. 40 PhDs.'''
    
    print("Testing roadmap extraction...")
    print(f"Company: {profile.name}")
    print(f"Context length: {len(profile.extracted_data_context)} characters")
    
    try:
        # Run the technical chain
        updated = run_technical_dd_chain(profile)
        
        print("\n✅ SUCCESS! Technical data extracted:")
        print(f"• Energy Density: {getattr(updated, 'energy_density_wh_kg', None)} Wh/kg")
        print(f"• Cycle Life: {getattr(updated, 'cycle_life_count', None)} cycles")
        print(f"• Patents: {getattr(updated, 'patent_portfolio', None)}")
        print(f"• Charging Speed: {getattr(updated, 'charging_speed_miles', None)} miles in {getattr(updated, 'charging_speed_minutes', None)} minutes")
        print(f"• Roadmap Technologies: {getattr(updated, 'roadmap_technologies', None)}")
        print(f"• Team Size: {getattr(updated, 'employees_count', None)} employees")
        print(f"• R&D Team: {getattr(updated, 'phds', None)} PhDs")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    test_roadmap_extraction() 