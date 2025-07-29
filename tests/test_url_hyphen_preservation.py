#!/usr/bin/env python3
"""
Test script to verify URL hyphen preservation during bullet point processing
"""

import sys
import os
import re
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_url_hyphen_preservation():
    """Test that URLs with hyphens are preserved during bullet point processing."""
    
    # Sample content with URLs containing hyphens
    test_content = [
        "• https://market.us/report/global-battery-technology-market/",
        "• https://www.researchandmarkets.com/reports/5785723/battery-technology-market-report",
        "• https://www.linkedin.com/in/meir-halberstam-b986a117/",
        "• https://example.com/path-with-hyphens/",
        "• Regular bullet point with no URL",
        "• Another bullet point with text"
    ]
    
    print("Testing URL hyphen preservation...")
    print("=" * 60)
    
    for i, line in enumerate(test_content, 1):
        line_stripped = line.strip()
        
        # Simulate the bullet point processing logic from main.py
        if (line_stripped.startswith('•') or line_stripped.startswith('-') or line_stripped.startswith('*')):
            bullet_line = re.sub(r"^[•\-*#]+\s*", "• ", line_stripped)
            
            # Only remove hyphens that are not part of URLs
            # First, temporarily replace URL hyphens to protect them
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, bullet_line)
            for j, url in enumerate(urls):
                # Replace hyphens in URLs with a temporary marker
                protected_url = url.replace('-', '___HYPHEN___')
                bullet_line = bullet_line.replace(url, protected_url)
            
            # Now remove hyphens from bullet point markers (but not from URLs)
            bullet_line = bullet_line.replace('*', '').replace('-', '').strip()
            
            # Restore hyphens in URLs
            for j, url in enumerate(urls):
                protected_url = url.replace('-', '___HYPHEN___')
                restored_url = protected_url.replace('___HYPHEN___', '-')
                bullet_line = bullet_line.replace(protected_url, restored_url)
            
            if not bullet_line.startswith('•'):
                bullet_line = '• ' + bullet_line.lstrip()
            
            # Check if URLs are preserved
            original_urls = re.findall(url_pattern, line_stripped)
            processed_urls = re.findall(url_pattern, bullet_line)
            
            print(f"{i:2d}. Original: {line_stripped}")
            print(f"    Processed: {bullet_line}")
            
            if original_urls:
                print(f"    Original URLs: {original_urls}")
                print(f"    Processed URLs: {processed_urls}")
                
                if original_urls == processed_urls:
                    print(f"    ✅ PASS | URLs preserved correctly")
                else:
                    print(f"    ❌ FAIL | URLs changed")
                    print(f"    Original: {original_urls}")
                    print(f"    Processed: {processed_urls}")
            else:
                print(f"    ✅ PASS | No URLs in this line")
            
            print()
    
    print("=" * 60)
    print("Expected behavior:")
    print("- URLs with hyphens should be preserved exactly")
    print("- Bullet point markers should be normalized")
    print("- Non-URL hyphens should be removed")
    
    return True

if __name__ == "__main__":
    test_url_hyphen_preservation() 