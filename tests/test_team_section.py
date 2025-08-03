#!/usr/bin/env python3
"""
Test team section generation with extracted Monzo executives
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.team_chain import generate_team_section
from core.schemas import StartupProfile

def test_team_section_generation():
    """Test team section generation with Monzo executives"""
    print("🔍 Testing team section generation with Monzo executives...")
    print("=" * 60)
    
    # Create a profile with the extracted Monzo executives
    profile = StartupProfile(
        name="Monzo",
        executives=[
            {
                'name': 'TS Anil',
                'role': 'Group Chief Executive Officer',
                'linkedin': '',  # Empty - as we saw in the logs
                'bio': '',
                'background_summary': 'TS Anil serves as Group Chief Executive Officer at Monzo. Previously, TS Anil was Chief Executive Officer at Visa Europe. TS Anil has extensive experience in the industry. TS Anil focuses on driving growth and innovation at Monzo.'
            },
            {
                'name': 'Gary Hoffman',
                'role': 'Chairman',
                'linkedin': '',  # Empty - as we saw in the logs
                'bio': '',
                'background_summary': 'Gary Hoffman serves as Chairman at Monzo. Previously, Gary Hoffman was Chairman at Virgin Money. Gary Hoffman has extensive experience in the industry. Gary Hoffman focuses on driving growth and innovation at Monzo.'
            },
            {
                'name': 'Matej Pfajfar',
                'role': 'Group Chief Technology Officer',
                'linkedin': '',  # Empty - as we saw in the logs
                'bio': '',
                'background_summary': 'Matej Pfajfar serves as Group Chief Technology Officer at Monzo. Previously, Matej Pfajfar was Chief Technology Officer at Revolut. Matej Pfajfar has extensive experience in the industry. Matej Pfajfar focuses on driving growth and innovation at Monzo.'
            }
        ]
    )
    
    print("📋 Input executives:")
    for i, exec in enumerate(profile.executives, 1):
        print(f"  {i}. {exec['name']} - {exec['role']}")
        print(f"     LinkedIn: '{exec['linkedin']}'")
        print(f"     Background: {exec['background_summary'][:100]}...")
        print()
    
    # Generate team section
    print("🎯 Generated team section:")
    print("-" * 40)
    team_section = generate_team_section(profile)
    print(team_section)
    
    print()
    print("📊 Analysis:")
    print("-" * 40)
    
    # Check if LinkedIn URLs appear
    if "LinkedIn:" in team_section:
        print("✅ LinkedIn URLs are included in the memo")
    else:
        print("❌ LinkedIn URLs are NOT included in the memo")
    
    # Check if background summaries appear
    if "TS Anil" in team_section and "Gary Hoffman" in team_section and "Matej Pfajfar" in team_section:
        print("✅ Executive names are included in the memo")
    else:
        print("❌ Executive names are missing from the memo")
    
    # Check if roles appear
    if "GROUP CHIEF EXECUTIVE OFFICER" in team_section and "CHAIRMAN" in team_section and "GROUP CHIEF TECHNOLOGY OFFICER" in team_section:
        print("✅ Executive roles are included in the memo")
    else:
        print("❌ Executive roles are missing from the memo")
    
    # Check if background summaries appear
    if "serves as" in team_section and "extensive experience" in team_section:
        print("✅ Background summaries are included in the memo")
    else:
        print("❌ Background summaries are missing from the memo")
    
    print("=" * 60)
    print("🎯 Team section test completed!")

if __name__ == "__main__":
    test_team_section_generation() 