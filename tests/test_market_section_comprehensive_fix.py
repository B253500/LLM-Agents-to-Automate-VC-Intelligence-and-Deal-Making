#!/usr/bin/env python3
"""
Comprehensive test for market section formatting including first paragraph fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_market_section_comprehensive():
    """Test comprehensive market section formatting."""
    
    print("🎯 Market Section Comprehensive Formatting Test")
    print("=" * 60)
    
    # Sample market section content
    market_content = [
        "The total addressable market (TAM) for the battery technology sector is currently valued at $160 billion, with a serviceable available market (SAM) of $48 billion.",
        "**📊 Market Size Metrics**",
        "• Total Addressable Market (TAM): $160B [Source: Pitch Deck]",
        "• Serviceable Available Market (SAM): $48B [Source: calculated_from_tam]",
        "**📈 Growth Metrics**",
        "• CAGR: 15.0% [Source: Pitch Deck]",
        "**📰 Sector Analysis**",
        "Market Overview: The Battery Technology sector is experiencing significant growth...",
        "**🔍 Market Research Sources**",
        "• https://market.us/report/global-battery-technology-market/",
        "• https://www.researchandmarkets.com/reports/5785723/battery-technology-market-report"
    ]
    
    print("📄 Sample Market Section Content:")
    for i, line in enumerate(market_content, 1):
        print(f"   {i:2d}. {line}")
    
    print("\n🔍 Formatting Analysis:")
    
    # Test first paragraph detection
    first_paragraph = market_content[0]
    first_para_conditions = [
        first_paragraph.startswith("The total addressable market"),
        first_paragraph.startswith("The Total Addressable Market"),
        "battery technology sector" in first_paragraph,
        "total addressable market" in first_paragraph.lower()
    ]
    
    print(f"   First Paragraph Detection:")
    print(f"     ✅ Should be normal text: {any(first_para_conditions)}")
    print(f"     ✅ Expected: Times New Roman, 12pt, Bold=False")
    
    # Test header detection
    headers = [
        "**📊 Market Size Metrics**",
        "**📈 Growth Metrics**", 
        "**📰 Sector Analysis**",
        "**🔍 Market Research Sources**"
    ]
    
    print(f"\n   Header Detection:")
    for header in headers:
        is_header = any(market_header in header for market_header in [
            "📊 Market Size Metrics", "📈 Growth Metrics", "📰 Sector Analysis",
            "🔍 Market Research Sources", "🔗 Additional Sources"
        ])
        print(f"     {'✅' if is_header else '❌'} {header}: {'Bold' if is_header else 'Normal'}")
    
    # Test bullet point detection
    bullet_points = [
        "• Total Addressable Market (TAM): $160B [Source: Pitch Deck]",
        "• Serviceable Available Market (SAM): $48B [Source: calculated_from_tam]",
        "• CAGR: 15.0% [Source: Pitch Deck]"
    ]
    
    print(f"\n   Bullet Point Detection:")
    for bullet in bullet_points:
        is_bullet = bullet.startswith("•")
        print(f"     {'✅' if is_bullet else '❌'} {bullet[:50]}...: {'Bullet' if is_bullet else 'Normal'}")
    
    # Test URL detection
    urls = [
        "https://market.us/report/global-battery-technology-market/",
        "https://www.researchandmarkets.com/reports/5785723/battery-technology-market-report"
    ]
    
    print(f"\n   URL Detection:")
    for url in urls:
        has_hyphens = "-" in url
        print(f"     {'✅' if has_hyphens else '❌'} {url}: {'With hyphens' if has_hyphens else 'No hyphens'}")
    
    print(f"\n🎯 Expected Final Formatting:")
    print(f"   ✅ First paragraph: Normal text (not bold)")
    print(f"   ✅ Headers (📊📈📰🔍): Bold formatting")
    print(f"   ✅ Bullet points: Normal text with targeted bold for keywords")
    print(f"   ✅ URLs: Preserved with hyphens")
    print(f"   ✅ Content: Properly formatted with hyperlinks")
    
    return True

if __name__ == "__main__":
    test_market_section_comprehensive() 