#!/usr/bin/env python3
"""
Test script for risks section formatting
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from main import format_risks_section

def test_risks_formatting():
    """Test the format_risks_section function with various inputs."""
    
    # Test cases
    test_cases = [
        # Risk headers (should be bold)
        "Market Risks",
        "Technical Risks", 
        "Operational Risks",
        "Regulatory Risks",
        "Financial Risks",
        "Strategic Risks",
        "Competitive Risks",
        "Technology Risks",
        "Execution Risks",
        
        # Content (should be normal text/bullet points)
        "• Market Adoption Uncertainty: StoreDot's technology is in the early prototype stage",
        "• Technology Maturity Uncertainty: StoreDot's technology is described as an early-stage prototype",
        "• Manufacturing Scalability Challenges: The transition from prototype to mass production",
        "• Compliance with Safety Standards: StoreDot may need to navigate complex safety regulations",
        "• Unknown Funding Stage: The current funding stage of StoreDot is unclear",
        
        # Mixed content
        "• Performance and Reliability Concerns: As the technology is still in the prototype phase",
        "• Supply Chain Vulnerabilities: The production of advanced battery technologies often requires specific raw materials",
        "• Environmental Regulations: Battery disposal and recycling are subject to stringent environmental regulations",
        "• Lack of Revenue Data: The absence of revenue data makes it difficult to evaluate StoreDot's financial performance"
    ]
    
    # Create a test document
    doc = Document()
    
    print("Testing risks section formatting...")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        para = doc.add_paragraph()
        format_risks_section(para, test_case)
        
        # Check if the run is bold (for headers) or not (for content)
        is_bold = para.runs[0].bold if para.runs else False
        expected_bold = any(header in test_case for header in [
            "Market Risks", "Technical Risks", "Operational Risks", 
            "Regulatory Risks", "Financial Risks", "Strategic Risks",
            "Competitive Risks", "Technology Risks", "Execution Risks"
        ])
        
        status = "✅ PASS" if is_bold == expected_bold else "❌ FAIL"
        print(f"{i:2d}. {status} | {'BOLD' if is_bold else 'NORMAL':6} | {test_case[:60]}...")
        
        if is_bold != expected_bold:
            print(f"     Expected: {'BOLD' if expected_bold else 'NORMAL'}")
    
    # Save test document
    output_path = "test_risks_formatting_output.docx"
    doc.save(output_path)
    print(f"\n✅ Test document saved to: {output_path}")
    print("\nExpected behavior:")
    print("- Risk headers (Market Risks, Technical Risks, etc.) should be BOLD")
    print("- Risk content (bullet points with descriptions) should be NORMAL text")
    
    return True

if __name__ == "__main__":
    test_risks_formatting() 