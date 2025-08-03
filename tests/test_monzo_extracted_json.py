#!/usr/bin/env python3
"""
Test with actual extracted Monzo JSON to debug the pipeline
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.pitch_deck_chain import run_pitch_deck_chain_with_text
from chains.team_chain import run_team_chain
from core.schemas import StartupProfile

def test_monzo_extracted_json():
    """Test with actual extracted Monzo JSON"""
    print("🔍 Testing with actual extracted Monzo JSON...")
    print("=" * 60)
    
    # Load the actual extracted JSON
    with open('extraction_cache/monzo.pdf_d06d31d63c647966f5a338a9a24972575ee36161.json', 'r') as f:
        extracted_data = json.load(f)
    
    deck_text = extracted_data['text']
    print(f"📄 Extracted text length: {len(deck_text)} characters")
    print(f"📄 First 500 characters: {deck_text[:500]}...")
    
    # Find the team section
    team_section_start = deck_text.find("The team has the right blend of product, tech, and banking skills.")
    if team_section_start != -1:
        team_section = deck_text[team_section_start:team_section_start + 2000]
        print(f"\n📋 Team section found:")
        print(f"📋 Team section: {team_section[:500]}...")
    else:
        print("❌ Team section not found!")
    
    print(f"\n📄 Step 1: Running pitch deck chain...")
    profile = StartupProfile()
    profile = run_pitch_deck_chain_with_text(deck_text, profile)
    
    print(f"📊 After pitch deck chain:")
    print(f"  - Company name: {profile.name}")
    print(f"  - Executives count: {len(profile.executives) if profile.executives else 0}")
    if profile.executives:
        for i, exec_info in enumerate(profile.executives, 1):
            print(f"    {i}. {exec_info.get('name', 'N/A')} - {exec_info.get('role', 'N/A')}")
    else:
        print("    ❌ No executives found!")
    
    print(f"\n📄 Step 2: Running team chain...")
    profile = run_team_chain(profile)
    
    print(f"📊 After team chain:")
    print(f"  - Company name: {profile.name}")
    print(f"  - Executives count: {len(profile.executives) if profile.executives else 0}")
    if profile.executives:
        for i, exec_info in enumerate(profile.executives, 1):
            print(f"    {i}. {exec_info.get('name', 'N/A')} - {exec_info.get('role', 'N/A')}")
            if exec_info.get('linkedin'):
                print(f"       LinkedIn: {exec_info.get('linkedin')}")
            if exec_info.get('background_summary'):
                print(f"       Background: {exec_info.get('background_summary')[:100]}...")
    else:
        print("    ❌ No executives found!")
    
    print(f"\n🎯 Summary:")
    print(f"  - Pitch deck chain found executives: {'✅' if profile.executives else '❌'}")
    print(f"  - Team chain preserved executives: {'✅' if profile.executives else '❌'}")

if __name__ == "__main__":
    test_monzo_extracted_json() 