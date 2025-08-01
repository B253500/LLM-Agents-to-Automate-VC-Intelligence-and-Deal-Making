#!/usr/bin/env python3
"""
Simple test script for company name and website extraction
"""

import pdfplumber
from pathlib import Path
from chains.pitch_deck_chain import extract_company_name_with_ai, extract_website_with_ai, extract_common_term

def test_extraction(pdf_path: str):
    """Test company name and website extraction on a PDF"""
    print(f"🔍 Testing extraction on: {pdf_path}")
    print("=" * 60)
    
    # Extract text from PDF
    with pdfplumber.open(pdf_path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
        full_text = "\n".join(pages)
    
    print(f"📄 Extracted {len(full_text)} characters from PDF")
    print(f"📄 First 500 chars: {full_text[:500]}...")
    print()
    
    # Test company name extraction
    print("🏢 TESTING COMPANY NAME EXTRACTION")
    print("-" * 40)
    
    # Test AI extraction
    print("🤖 AI Company Name Detection:")
    ai_company_name = extract_company_name_with_ai(full_text[:3000])
    print(f"   Result: '{ai_company_name}'")
    print()
    
    # Test regex extraction
    print("🔍 Regex Company Name Detection:")
    regex_company_name = extract_common_term(full_text[:3000], pdf_path)
    print(f"   Result: '{regex_company_name}'")
    print()
    
    # Test website extraction
    print("🌐 TESTING WEBSITE EXTRACTION")
    print("-" * 40)
    
    # Use the better company name for website detection
    company_name = ai_company_name if ai_company_name and ai_company_name.lower() != "unknown" else regex_company_name
    
    print(f"🤖 AI Website Detection (for company: {company_name}):")
    ai_website = extract_website_with_ai(full_text[:3000], company_name)
    print(f"   Result: '{ai_website}'")
    print()
    
    print("✅ Extraction test complete!")
    print("=" * 60)

if __name__ == "__main__":
    # Test on Shopify PDF
    test_extraction("data/shopify.pdf") 