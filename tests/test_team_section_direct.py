#!/usr/bin/env python3
"""
Test team section generation directly (bypassing validation)
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_direct_team_section():
    """Test team section generation directly"""
    print("🔍 Testing direct team section generation...")
    print("=" * 60)
    
    # Simulate the executives data structure directly
    executives = [
        {
            'name': 'TS Anil',
            'role': 'Group Chief Executive Officer',
            'linkedin': '',  # Empty LinkedIn URL
            'bio': '',
            'background_summary': 'TS Anil serves as Group Chief Executive Officer at Monzo. Previously, TS Anil was Chief Executive Officer at Visa Europe. TS Anil has extensive experience in the industry. TS Anil focuses on driving growth and innovation at Monzo.'
        },
        {
            'name': 'Gary Hoffman',
            'role': 'Chairman',
            'linkedin': '',  # Empty LinkedIn URL
            'bio': '',
            'background_summary': 'Gary Hoffman serves as Chairman at Monzo. Previously, Gary Hoffman was Chairman at Virgin Money. Gary Hoffman has extensive experience in the industry. Gary Hoffman focuses on driving growth and innovation at Monzo.'
        },
        {
            'name': 'Matej Pfajfar',
            'role': 'Group Chief Technology Officer',
            'linkedin': '',  # Empty LinkedIn URL
            'bio': '',
            'background_summary': 'Matej Pfajfar serves as Group Chief Technology Officer at Monzo. Previously, Matej Pfajfar was Chief Technology Officer at Revolut. Matej Pfajfar has extensive experience in the industry. Matej Pfajfar focuses on driving growth and innovation at Monzo.'
        }
    ]
    
    # Simulate the team section generation logic directly
    lines = []
    count = 0
    
    for exec in executives:
        if count >= 3:  # Limit to 3 executives
            break
            
        name = exec.get('name', 'Unknown')
        role = exec.get('role', '').title()
        linkedin = exec.get('linkedin', '')
        bio = exec.get('bio', '')
        
        # Format the executive entry
        lines.append(f"{count + 1}. **{name} – {role.upper()}**")
        
        if linkedin:
            lines.append(f"   LinkedIn: {linkedin}")
        
        # Use background summary if available, otherwise use bio
        background = exec.get('background_summary', '') or bio
        
        if background:
            # Clean up the background
            import re
            background = re.sub(r'<think>.*?</think>', '', background, flags=re.DOTALL)
            background = re.sub(r'(Okay, so I need to figure out|First, from the|Looking at the|Based on the|From the search results|Let me start by|I need to analyze|Let me examine).*?(?=\n|$)', '', background, flags=re.DOTALL)
            background = background.strip()
            
            if background and len(background) > 20:
                lines.append(f"   {background}")
        
        lines.append("")
        count += 1
    
    team_section = '\n'.join(lines)
    
    print("📋 Input executives:")
    for i, exec in enumerate(executives, 1):
        print(f"  {i}. {exec['name']} - {exec['role']}")
        print(f"     LinkedIn: '{exec['linkedin']}'")
        print(f"     Background: {exec['background_summary'][:100]}...")
        print()
    
    # Generate team section
    print("🎯 Generated team section:")
    print("-" * 40)
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
    print("🎯 Direct team section test completed!")

if __name__ == "__main__":
    test_direct_team_section() 