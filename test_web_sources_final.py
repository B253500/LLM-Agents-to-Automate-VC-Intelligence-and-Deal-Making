#!/usr/bin/env python3
"""
Final test to verify web sources are properly preserved and displayed
"""

from core.schemas import StartupProfile
from main import format_enhanced_financials_section
from datetime import datetime

def test_web_sources_final():
    """Test that web sources are properly preserved and displayed"""
    
    print("🧪 Final Web Sources Test")
    print("=" * 50)
    
    # Create a test profile with web sources (like the financial chain would)
    profile = StartupProfile()
    profile.name = "Test Company"
    profile.implied_valuation = "$9 billion"
    profile.latest_round_amount = "$370 million"
    profile.total_funding_raised = "$2.777 billion"
    profile.web_sources = [
        "https://www.crunchbase.com/organization/octopus-energy",
        "https://www.cbinsights.com/company/octopus-energy",
        "https://www.ionanalytics.com/octopus-energy-funding-round"
    ]
    
    print(f"📊 Initial web_sources: {profile.web_sources}")
    print(f"📊 Initial web_sources length: {len(profile.web_sources)}")
    
    # Test the enhanced financial formatting (this will call the agent)
    current_date = datetime.now().strftime("%B %d, %Y")
    
    try:
        formatted_section = format_enhanced_financials_section(profile, current_date)
        
        print(f"\n📊 Final web_sources: {profile.web_sources}")
        print(f"📊 Final web_sources length: {len(profile.web_sources) if profile.web_sources else 0}")
        
        # Check if web sources are in the output
        if "🔗 Data Sources" in formatted_section:
            print("\n✅ Web sources section found in output!")
            if "crunchbase.com" in formatted_section:
                print("✅ Crunchbase link found!")
            if "cbinsights.com" in formatted_section:
                print("✅ CB Insights link found!")
            if "ionanalytics.com" in formatted_section:
                print("✅ ION Analytics link found!")
        else:
            print("\n❌ Web sources section NOT found in output!")
            print("\n📋 Formatted section preview:")
            print(formatted_section[:500] + "..." if len(formatted_section) > 500 else formatted_section)
            
    except Exception as e:
        print(f"\n❌ Error in enhanced financial section: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("✅ Final web sources test completed")

if __name__ == "__main__":
    test_web_sources_final() 