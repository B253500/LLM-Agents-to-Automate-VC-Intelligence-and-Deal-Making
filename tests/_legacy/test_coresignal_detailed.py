#!/usr/bin/env python3
"""
Test CoreSignal extraction with detailed field inspection
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.coresignal_utils import get_full_company_data

def test_detailed_mapping():
    """Test CoreSignal extraction with detailed field inspection"""
    print("🔍 Testing CoreSignal detailed field inspection...")
    print("=" * 60)
    
    # Test with Monzo to see all available fields
    company_name = "Monzo"
    print(f"Testing detailed mapping for: '{company_name}'")
    
    result = get_full_company_data(company_name)
    
    if result:
        print(f"✅ Found company: {result.get('name', 'Unknown')}")
        print(f"Company ID: {result.get('id', 'Unknown')}")
        print()
        
        print("📋 ALL AVAILABLE FIELDS:")
        print("-" * 40)
        
        # Sort fields alphabetically for better readability
        sorted_fields = sorted(result.keys())
        
        for field in sorted_fields:
            value = result.get(field)
            if value is not None:
                # Truncate long values for readability
                if isinstance(value, str) and len(value) > 100:
                    display_value = value[:100] + "..."
                elif isinstance(value, (list, dict)) and len(str(value)) > 100:
                    display_value = str(value)[:100] + "..."
                else:
                    display_value = value
                
                print(f"{field}: {display_value}")
        
        print()
        print("🎯 EXECUTIVE-RELATED FIELDS:")
        print("-" * 40)
        
        # Look for any executive-related fields
        executive_keywords = ['executive', 'officer', 'director', 'ceo', 'cfo', 'cto', 'founder', 'management', 'leadership', 'team', 'employee', 'staff']
        executive_fields = []
        
        for field in sorted_fields:
            field_lower = field.lower()
            if any(keyword in field_lower for keyword in executive_keywords):
                value = result.get(field)
                if value is not None:
                    executive_fields.append((field, value))
        
        if executive_fields:
            for field, value in executive_fields:
                print(f"{field}: {value}")
        else:
            print("❌ No executive-related fields found in CoreSignal data")
        
        print()
        print("📊 FIELD SUMMARY:")
        print("-" * 40)
        print(f"Total fields available: {len(sorted_fields)}")
        print(f"Fields with data: {len([f for f in sorted_fields if result.get(f) is not None])}")
        print(f"Executive-related fields: {len(executive_fields)}")
        
    else:
        print("❌ No company found")
    
    print("=" * 60)
    print("🎯 Detailed mapping test completed!")

if __name__ == "__main__":
    test_detailed_mapping() 