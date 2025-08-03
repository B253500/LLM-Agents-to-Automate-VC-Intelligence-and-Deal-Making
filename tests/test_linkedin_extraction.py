#!/usr/bin/env python3
"""
Test LinkedIn URL extraction for Monzo executives
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.team_chain import get_linkedin_profile_perplexity

def test_linkedin_extraction():
    """Test LinkedIn URL extraction for Monzo executives"""
    print("🔍 Testing LinkedIn URL extraction for Monzo executives...")
    print("=" * 60)
    
    # Test executives from Monzo
    test_executives = [
        ("TS Anil", "Monzo"),
        ("Gary Hoffman", "Monzo"), 
        ("Matej Pfajfar", "Monzo")
    ]
    
    for name, company in test_executives:
        print(f"\n📋 Testing: {name} at {company}")
        print("-" * 40)
        
        try:
            linkedin_data = get_linkedin_profile_perplexity(name, company)
            
            if linkedin_data:
                print(f"✅ Found LinkedIn data for {name}")
                print(f"   Profile URL: {linkedin_data.get('profile_url', 'None')}")
                print(f"   Headline: {linkedin_data.get('headline', 'None')}")
                print(f"   Summary: {linkedin_data.get('summary', 'None')[:100]}...")
                
                if linkedin_data.get('profile_url'):
                    print(f"   ✅ LinkedIn URL found!")
                else:
                    print(f"   ❌ No LinkedIn URL found")
            else:
                print(f"❌ No LinkedIn data found for {name}")
                
        except Exception as e:
            print(f"❌ Error extracting LinkedIn data for {name}: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 LinkedIn extraction test completed!")

if __name__ == "__main__":
    test_linkedin_extraction() 