#!/usr/bin/env python3
"""
Test improved team section generation
"""
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schemas import StartupProfile
from chains.team_chain import generate_team_section

def test_improved_team_section():
    print("🔍 Testing improved team section generation...")
    print("=" * 60)
    
    # Create a test profile with executives from Monzo
    profile = StartupProfile(
        name="Monzo",
        executives=[
            {
                "name": "Paul Rippon",
                "role": "Deputy CEO & Co-Founder",
                "linkedin": "https://www.linkedin.com/in/paul-rippon",
                "bio": "",
                "background_summary": "Paul Rippon serves as Deputy CEO & Co-Founder at Monzo. Paul Rippon has extensive experience in the industry. Paul Rippon focuses on driving growth and innovation at Monzo. Paul Rippon brings valuable expertise to Monzo.",
                "prior_exits": []
            },
            {
                "name": "Gary Dolman", 
                "role": "CFO & Co-Founder",
                "linkedin": "https://www.linkedin.com/in/gary-dolman",
                "bio": "",
                "background_summary": "Gary Dolman serves as CFO & Co-Founder at Monzo. Gary Dolman has extensive experience in the industry. Gary Dolman focuses on driving growth and innovation at Monzo. Gary Dolman brings valuable expertise to Monzo.",
                "prior_exits": []
            },
            {
                "name": "Jonas Huckstein",
                "role": "CTO & Co-Founder", 
                "linkedin": "https://www.linkedin.com/in/jonas-huckstein",
                "bio": "",
                "background_summary": "Jonas Huckstein serves as CTO & Co-Founder at Monzo. Jonas Huckstein has extensive experience in the industry. Jonas Huckstein focuses on driving growth and innovation at Monzo. Jonas Huckstein brings valuable expertise to Monzo.",
                "prior_exits": []
            }
        ]
    )
    
    # Generate team section
    team_section = generate_team_section(profile)
    
    print("📝 Generated Team Section:")
    print("=" * 60)
    print(team_section)
    print("=" * 60)

if __name__ == "__main__":
    test_improved_team_section() 