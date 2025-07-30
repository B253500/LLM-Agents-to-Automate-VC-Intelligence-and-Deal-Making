#!/usr/bin/env python3
"""
Simple test script to test Mermaid diagram functionality
"""

import re
import requests
import base64

def test_mermaid_rendering():
    """Test Mermaid diagram rendering with different syntax examples."""
    
    # Test cases with different syntax
    test_cases = [
        {
            "name": "Correct Syntax",
            "code": """graph TD
    StoreDot --> Licensing_Fees
    StoreDot --> Direct_Sales
    StoreDot --> Partnerships
    Licensing_Fees --> Automotive_Manufacturers
    Direct_Sales --> Consumer_Electronics
    Partnerships --> Industrial_Firms"""
        },
        {
            "name": "Semicolon Syntax (Problematic)",
            "code": """graph TD; StoreDot --> Licensing_Fees; StoreDot --> Direct_Sales; StoreDot --> Partnerships; Licensing_Fees --> Automotive_Manufacturers; Direct_Sales --> Consumer_Electronics; Partnerships --> Industrial_Firms"""
        },
        {
            "name": "Simple Syntax",
            "code": """graph TD
    A --> B
    B --> C"""
        }
    ]
    
    services = [
        ('https://kroki.io/mermaid/png', 'Kroki.io'),
        ('https://mermaid.ink/img/', 'Mermaid.ink'),
    ]
    
    print("🧪 Testing Mermaid Diagram Rendering")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases):
        print(f"\n📋 Test Case {i+1}: {test_case['name']}")
        print(f"Code: {test_case['code'][:100]}...")
        
        # Clean the code (simplified version)
        code = test_case['code'].strip()
        code = code.replace(';', '\n')  # Replace semicolons with newlines
        
        print(f"Cleaned: {code[:100]}...")
        
        rendered = False
        for service_url, service_name in services:
            try:
                if service_name == 'Kroki.io':
                    headers = {'Content-Type': 'text/plain'}
                    resp = requests.post(service_url, data=code.encode('utf-8'), headers=headers, timeout=30)
                elif service_name == 'Mermaid.ink':
                    encoded = base64.b64encode(code.encode('utf-8')).decode('utf-8')
                    resp = requests.get(f"{service_url}{encoded}", timeout=30)
                
                if resp.status_code == 200:
                    print(f"✅ {service_name}: SUCCESS")
                    rendered = True
                    break
                else:
                    print(f"❌ {service_name}: FAILED ({resp.status_code})")
                    if resp.status_code == 400:
                        try:
                            error_details = resp.text[:200]
                            print(f"   Error: {error_details}")
                        except:
                            pass
            except Exception as e:
                print(f"❌ {service_name}: EXCEPTION - {e}")
        
        if not rendered:
            print("❌ All services failed for this test case")
        else:
            print("✅ Test case passed!")
    
    print("\n" + "=" * 50)
    print("🎯 Test Complete!")

if __name__ == "__main__":
    test_mermaid_rendering() 