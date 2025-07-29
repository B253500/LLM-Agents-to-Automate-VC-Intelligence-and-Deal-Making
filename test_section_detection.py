#!/usr/bin/env python3
"""
Test script for the new robust section detection system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from evaluation_metrics.core.evaluation_metrics import MemoEvaluator

def test_section_detection():
    """Test the new section detection system"""
    
    # Sample memo text with numbered sections
    sample_memo = """
1. DETAILED SUMMARY
This is a detailed summary of the company with meaningful content that exceeds the minimum requirements for a valid section.

2. COMPANY OVERVIEW
Company: StoreDot
Sector: Battery Technology
Website: www.storedot.com
This section contains comprehensive company information.

3. PROBLEM STATEMENT
The main problem is slow charging times for electric vehicles. This creates significant barriers to adoption.

4. SOLUTION OVERVIEW
Our solution is ultra-fast charging technology that reduces charging time to minutes.

5. PRODUCT/SERVICE DESCRIPTION
StoreDot develops extreme fast charging battery technology for electric vehicles.

6. MARKET SIZE & ANALYSIS
The global EV market is valued at $500B and growing rapidly.

7. COMPETITORS
Major competitors include Tesla, QuantumScape, and Solid Power.

8. BUSINESS MODEL
Business Model Schema:
```mermaid
graph TD;
Customer-->Product-->Revenue
```
Revenue streams include licensing and partnerships.

9. TECHNICAL DUE DILIGENCE
Energy density: 300 wh/kg
Cycle life: 1200 cycles
Patents: 78 patents

10. FINANCIAL ANALYSIS
Current valuation: $1.2B
Total funding raised: $200M

11. TEAM & MANAGEMENT
Doron Myersdorf – CEO AND CO-FOUNDER
Carl-Peter Forster – CHAIRMAN
Meir Halberstam – CFO

12. ESG CONSIDERATIONS
Focus on sustainable battery materials and reduced environmental impact.

13. RISKS
Technology execution risk and market adoption challenges.

14. INVESTMENT & EXIT STRATEGIES
Strategic partnerships and potential IPO or acquisition.

15. COUNTERFACTUAL ANALYSIS: WHAT IF WE DON'T INVEST?
We would miss the opportunity to invest in breakthrough battery technology.

16. FOLLOW-UP QUESTIONS & NEXT STEPS
Need to validate technical claims and assess competitive landscape.

17. AI DISCUSSION AND COMMENTARY
Key Strengths:
Strong technology innovation and market positioning.

Key Weaknesses:
Execution risk and competitive pressure.

Opportunities:
Growing EV market and regulatory support.

Risks:
Technology scaling and market adoption challenges.

Conclusion:
This investment opportunity presents both significant potential and notable risks.
"""

    # Create evaluator and test section detection
    evaluator = MemoEvaluator()
    
    print("🔍 Testing New Section Detection System")
    print("=" * 50)
    
    # Test the section evaluation
    section_results = evaluator._evaluate_sections(sample_memo)
    
    print(f"✅ All sections present: {section_results['all_present']}")
    print(f"📊 Present sections: {section_results['present_count']}/17")
    print(f"❌ Missing sections: {section_results['missing']}")
    
    print("\n📋 Section Details:")
    for section_name, details in section_results.get('section_details', {}).items():
        quality = evaluator._assess_section_content_quality(details)
        status = "✅ VALID" if quality['is_valid'] else f"❌ INVALID ({quality['reason']})"
        print(f"  {section_name}: {status}")
        print(f"    Words: {details['word_count']}, Lines: {details['line_count']}, Chars: {details['char_count']}")
    
    print("\n🎯 Test Results:")
    if section_results['all_present']:
        print("✅ SUCCESS: All sections detected and validated!")
    else:
        print("❌ ISSUES FOUND:")
        for missing in section_results['missing']:
            print(f"  - {missing}")

if __name__ == "__main__":
    test_section_detection() 