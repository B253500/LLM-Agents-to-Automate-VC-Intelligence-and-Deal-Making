#!/usr/bin/env python3
"""
Test Mermaid syntax cleaning without external services
"""

def test_mermaid_syntax_cleaning():
    """Test the Mermaid syntax cleaning logic."""
    
    # Test cases
    test_cases = [
        {
            "name": "Semicolon Problem (Original)",
            "input": "graph TD; StoreDot --> Licensing_Fees; StoreDot --> Direct_Sales;",
            "expected": "graph TD\n StoreDot --> Licensing_Fees\n StoreDot --> Direct_Sales\n"
        },
        {
            "name": "Correct Syntax (Should Stay Same)",
            "input": """graph TD
    StoreDot --> Licensing_Fees
    StoreDot --> Direct_Sales""",
            "expected": """graph TD
    StoreDot --> Licensing_Fees
    StoreDot --> Direct_Sales"""
        },
        {
            "name": "Mixed Semicolons",
            "input": "graph TD; A --> B; B --> C;",
            "expected": "graph TD\n A --> B\n B --> C\n"
        }
    ]
    
    print("🧪 Testing Mermaid Syntax Cleaning")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases):
        print(f"\n📋 Test Case {i+1}: {test_case['name']}")
        print(f"Input:  {test_case['input']}")
        
        # Apply the same cleaning logic as in main.py
        code = test_case['input'].strip()
        code = code.replace(';', '\n')  # Replace semicolons with newlines
        
        print(f"Output: {code}")
        print(f"Expected: {test_case['expected']}")
        
        # Check if the cleaning worked
        if code == test_case['expected']:
            print("✅ PASS - Syntax cleaning worked correctly")
        else:
            print("❌ FAIL - Syntax cleaning didn't match expected")
            print(f"   Difference: '{code}' vs '{test_case['expected']}'")
    
    print("\n" + "=" * 50)
    print("🎯 Syntax Test Complete!")

if __name__ == "__main__":
    test_mermaid_syntax_cleaning() 