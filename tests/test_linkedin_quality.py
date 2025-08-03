#!/usr/bin/env python3
"""
Test LinkedIn enrichment quality for Monzo executives
"""
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chains.team_chain import get_linkedin_profile_perplexity, generate_executive_background_summary

def test_linkedin_quality():
    print("🔍 Testing LinkedIn enrichment quality for Monzo executives...")
    print("=" * 60)
    
    test_executives = [
        ("Paul Rippon", "Deputy CEO & Co-Founder", "Monzo"),
        ("Gary Dolman", "CFO & Co-Founder", "Monzo"), 
        ("Jonas Huckstein", "CTO & Co-Founder", "Monzo")
    ]
    
    for name, role, company in test_executives:
        print(f"\n📋 Testing: {name} - {role} at {company}")
        print("-" * 40)
        
        # Get LinkedIn data
        linkedin_data = get_linkedin_profile_perplexity(name, company)
        
        if linkedin_data:
            print(f"✅ LinkedIn URL: {linkedin_data.get('profile_url', 'N/A')}")
            print(f"✅ Headline: {linkedin_data.get('headline', 'N/A')}")
            print(f"✅ Summary: {linkedin_data.get('summary', 'N/A')[:200]}...")
            print(f"✅ Experiences: {linkedin_data.get('experiences', [])}")
            
            # Generate background summary
            background = generate_executive_background_summary(name, role, linkedin_data, company)
            print(f"\n📝 Generated Background Summary:")
            print(f"'{background}'")
        else:
            print("❌ No LinkedIn data found")
            # Test with no LinkedIn data
            background = generate_executive_background_summary(name, role, None, company)
            print(f"\n📝 Generated Background Summary (no LinkedIn data):")
            print(f"'{background}'")
        
        print("\n" + "="*60)

if __name__ == "__main__":
    test_linkedin_quality() 