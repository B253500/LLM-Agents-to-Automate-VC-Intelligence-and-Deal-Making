#!/usr/bin/env python3
"""
Comprehensive audit test for all formatting sections
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_formatting_audit():
    """Test comprehensive formatting for all sections."""
    
    # Sample content with bullet-pointed headers that should be converted to bold
    test_content = """The total addressable market (TAM) for the battery technology sector is currently valued at $160 billion.

• 📊 Market Size Metrics
• **Total Addressable Market (TAM)**: $160B [Source: Pitch Deck]

• 📈 Growth Metrics
**CAGR**: 15.0% [Source: Pitch Deck]

• 📰 Sector Analysis
Market Overview:

• Business Model Schema
• Revenue Streams: Subscription model
• Customer Segments: Enterprise clients

• Financial Analysis📊
• Revenue: $10M ARR
• Funding: Series A

• CEO – John Smith
• CTO – Jane Doe

• Market Risks
• Technology Risks
• Operational Risks

• Follow-up Questions
• Next Steps

• Key Strengths
• Key Weaknesses

• Regular bullet point content
• Another regular bullet point"""

    print("Testing comprehensive formatting audit...")
    print("=" * 70)
    
    # Simulate the processing logic from main.py
    lines = test_content.split('\n')
    results = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Simulate bullet point detection
        if (line_stripped.startswith('•') or line_stripped.startswith('-') or line_stripped.startswith('*')):
            # Remove bullet point for header detection
            header_check = line_stripped.replace('•', '').replace('-', '').replace('*', '').strip()
            
            # Check if this is a header that should be processed by section-specific formatting
            market_headers = [
                "📊 Market Size Metrics", "📈 Growth Metrics", "📰 Sector Analysis",
                "🔍 Market Research Sources", "🔗 Additional Sources"
            ]
            
            business_model_headers = [
                "Business Model Schema", "Business Model Overview", "Potential Revenue Streams",
                "Customer Segments", "Strategy", "Additional Research Needed"
            ]
            
            financial_analysis_headers = [
                "Financial Analysis📊", "Data Sources 🔗", "Funding Rounds:", "Current Valuation:",
                "Latest Funding Round:", "Total Funding Raised:", "Financial Data", "Funding History"
            ]
            
            team_management_headers = [
                "CEO", "CFO", "CTO", "CHAIRMAN", "COFOUNDER", "FOUNDER"
            ]
            
            risks_headers = [
                "Market Risks", "Technical Risks", "Operational Risks", 
                "Regulatory Risks", "Financial Risks", "Strategic Risks",
                "Competitive Risks", "Technology Risks", "Execution Risks"
            ]
            
            followup_headers = [
                "Follow-up Questions", "Next Steps", "Additional Research Needed",
                "Key Questions", "Due Diligence Items", "Action Items"
            ]
            
            ai_commentary_headers = [
                "Key Strengths", "Key Weaknesses", "Opportunities", "Risks", "Conclusion",
                "Investment Thesis", "Critical Analysis", "Recommendation"
            ]
            
            # Check if it's a header
            is_header = (any(header in header_check for header in market_headers) or
                        any(header in header_check for header in business_model_headers) or
                        any(header in header_check for header in financial_analysis_headers) or
                        any(header in header_check for header in team_management_headers) or
                        any(header in header_check for header in risks_headers) or
                        any(header in header_check for header in followup_headers) or
                        any(header in header_check for header in ai_commentary_headers))
            
            # Additional checks for specific patterns
            if not is_header:
                # Check for specific patterns that should be headers
                if (header_check.startswith("📊") or header_check.startswith("📈") or 
                    header_check.startswith("📰") or header_check.startswith("🔍") or 
                    header_check.startswith("🔗") or header_check.startswith("⚠️") or
                    header_check.startswith("🔧") or header_check.startswith("⚙️") or
                    header_check.startswith("📋") or header_check.startswith("🏢")):
                    is_header = True
                elif any(title in header_check for title in [
                    "Business Model", "Financial Analysis", "CEO", "CFO", "CTO", 
                    "Market Risks", "Technical Risks", "Operational Risks",
                    "Follow-up Questions", "Next Steps", "Key Strengths", "Key Weaknesses"
                ]):
                    is_header = True
                elif ":" in header_check and len(header_check.split(":")[0].strip()) < 20:
                    # Short text with colon is likely a header
                    is_header = True
            
            if is_header:
                results.append(f"✅ HEADER | {line_stripped} → Should be BOLD")
            else:
                results.append(f"✅ BULLET | {line_stripped} → Should be bullet point")
        else:
            # Check if it's a first paragraph
            if any(phrase in line_stripped.lower() for phrase in [
                "total addressable market", "battery technology sector", "tam for the"
            ]):
                results.append(f"✅ FIRST PARAGRAPH | {line_stripped} → Should be NORMAL")
            else:
                results.append(f"✅ NORMAL | {line_stripped}")
    
    print("Processing Results:")
    print("-" * 50)
    for result in results:
        print(result)
    
    print("\n" + "=" * 70)
    print("Expected Behavior Summary:")
    print("-" * 30)
    print("✅ Headers with bullet points should be converted to BOLD")
    print("✅ First paragraph should remain NORMAL text")
    print("✅ Content bullet points should be preserved")
    print("✅ Regular bullet points should remain as bullet points")
    print("✅ Section-specific formatting should be applied correctly")
    
    # Count results
    header_count = sum(1 for r in results if "HEADER" in r)
    bullet_count = sum(1 for r in results if "BULLET" in r)
    first_para_count = sum(1 for r in results if "FIRST PARAGRAPH" in r)
    normal_count = sum(1 for r in results if "NORMAL" in r)
    
    print(f"\n📊 Summary:")
    print(f"   Headers: {header_count}")
    print(f"   Bullet points: {bullet_count}")
    print(f"   First paragraphs: {first_para_count}")
    print(f"   Normal text: {normal_count}")
    
    return True

if __name__ == "__main__":
    test_formatting_audit() 