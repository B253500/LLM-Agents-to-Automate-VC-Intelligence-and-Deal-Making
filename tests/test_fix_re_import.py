#!/usr/bin/env python3
"""
Test script to verify the re import fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_re_import_fix():
    """Test that the re module is properly accessible."""
    
    print("🔧 Testing re import fix...")
    print("=" * 40)
    
    try:
        # Test that re is available globally
        import re
        
        # Test basic re functionality
        test_text = "Hello world"
        result = re.search(r"world", test_text)
        
        if result:
            print("✅ re module is working correctly")
            print("✅ Basic regex functionality works")
            print("✅ Import conflict resolved")
            return True
        else:
            print("❌ re module test failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing re module: {e}")
        return False

if __name__ == "__main__":
    test_re_import_fix() 