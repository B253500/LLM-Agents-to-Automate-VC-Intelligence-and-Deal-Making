#!/usr/bin/env python3
"""
Test CoreSignal extraction with comprehensive field mapping
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.coresignal_utils import get_full_company_data

def test_comprehensive_mapping():
    """Test CoreSignal extraction with comprehensive field mapping"""
    print("🔍 Testing CoreSignal comprehensive field mapping...")
    print("=" * 60)
    
    # Test companies in our mapping
    test_companies = [
        "Monzo",
        "Lunchbox", 
        "Dropbox"
    ]
    
    for i, company in enumerate(test_companies, 1):
        print(f"{i}. Testing comprehensive mapping for: '{company}'")
        result = get_full_company_data(company)
        
        if result:
            print(f"✅ Found company: {result.get('name', 'Unknown')}")
            print(f"   Industry: {result.get('industry', 'Unknown')}")
            print(f"   Website: {result.get('website', 'Unknown')}")
            print(f"   Founded: {result.get('founded', 'Unknown')}")
            print(f"   Status: {result.get('type', 'Unknown')}")
            print(f"   HQ City: {result.get('headquarters_city', 'Unknown')}")
            print(f"   Revenue: {result.get('estimated_revenue_range', 'Unknown')}")
            print(f"   Funding: {result.get('last_funding_round_amount_raised', 'Unknown')}")
            print(f"   Size: {result.get('size', 'Unknown')}")
            print(f"   LinkedIn Followers: {result.get('followers', 'Unknown')}")
            print(f"   News Counts: {result.get('news_counts', 'Unknown')}")
            print(f"   Technographics: {result.get('technographics', 'Unknown')}")
            print(f"   Emails: {result.get('emails', 'Unknown')}")
            print(f"   Phones: {result.get('phones', 'Unknown')}")
            print(f"   LinkedIn: {result.get('linkedin', 'Unknown')}")
            print(f"   Twitter: {result.get('twitter', 'Unknown')}")
            print(f"   Facebook: {result.get('facebook', 'Unknown')}")
        else:
            print("❌ No company found")
        
        print()
    
    print("=" * 60)
    print("🎯 Comprehensive mapping test completed!")

if __name__ == "__main__":
    test_comprehensive_mapping() 