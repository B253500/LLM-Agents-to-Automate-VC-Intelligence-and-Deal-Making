"""
Test the fixed team section generation without thinking process.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schemas import StartupProfile
from chains.memo_synthesis_chain import run_team_section_chain


def test_team_section_no_thinking():
    """Test that team section doesn't include thinking process."""
    
    # Create a test profile with executives
    profile = StartupProfile(
        name="Test Company",
        executives=[
            {
                "name": "John Smith",
                "role": "Chief Executive Officer",
                "linkedin": "https://linkedin.com/in/johnsmith"
            },
            {
                "name": "Jane Doe", 
                "role": "Chief Financial Officer",
                "linkedin": "https://linkedin.com/in/janedoe"
            },
            {
                "name": "Bob Wilson",
                "role": "Chief Technology Officer", 
                "linkedin": "https://linkedin.com/in/bobwilson"
            }
        ]
    )
    
    # Generate team section
    team_section = run_team_section_chain(profile)
    
    print("=== TEAM SECTION OUTPUT ===")
    print(team_section)
    print("==========================")
    
    # Check that no thinking process is included
    thinking_indicators = [
        "thinking", "thought", "let me", "based on", "first", "looking at",
        "analyzing", "examining", "putting this together", "need to"
    ]
    
    team_section_lower = team_section.lower()
    found_thinking = []
    
    for indicator in thinking_indicators:
        if indicator in team_section_lower:
            found_thinking.append(indicator)
    
    if found_thinking:
        print(f"❌ Found thinking indicators: {found_thinking}")
        return False
    else:
        print("✅ No thinking process detected in team section")
        return True


def test_team_section_formatting():
    """Test that team section uses proper formatting."""
    
    profile = StartupProfile(
        name="Test Company",
        founder_name="John Smith",
        executives=[
            {
                "name": "John Smith",
                "role": "Chief Executive Officer"
            }
        ]
    )
    
    team_section = run_team_section_chain(profile)
    
    # Check for proper formatting
    expected_formats = [
        "**John Smith – FOUNDER**",
        "**John Smith – CHIEF EXECUTIVE OFFICER**"
    ]
    
    found_formats = []
    for expected in expected_formats:
        if expected in team_section:
            found_formats.append(expected)
    
    if found_formats:
        print(f"✅ Found proper formatting: {found_formats}")
        return True
    else:
        print("❌ Proper formatting not found")
        return False


if __name__ == "__main__":
    print("Testing team section fixes...")
    
    test1_passed = test_team_section_no_thinking()
    test2_passed = test_team_section_formatting()
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Team section is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.") 