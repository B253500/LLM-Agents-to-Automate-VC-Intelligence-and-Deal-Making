#!/usr/bin/env python3
"""
Test script for enhanced PDF extraction
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

from core.download_utils import enhanced_pdf_extraction, validate_extraction_quality

def test_enhanced_extraction():
    """Test the enhanced extraction on the StoreDot deck"""
    
    # Look for the StoreDot PDF in the data directory
    data_dir = Path("data")
    store_dot_pdf = None
    
    for pdf_file in data_dir.glob("*.pdf"):
        if "store" in pdf_file.name.lower() or "storedot" in pdf_file.name.lower():
            store_dot_pdf = pdf_file
            break
    
    if not store_dot_pdf:
        print("❌ StoreDot PDF not found in data directory")
        return
    
    print(f"🔍 Testing enhanced extraction on: {store_dot_pdf}")
    
    try:
        # Run enhanced extraction
        extracted = enhanced_pdf_extraction(str(store_dot_pdf), return_structured=True)
        
        # Validate quality
        quality_report = validate_extraction_quality(extracted)
        
        print("\n" + "="*60)
        print("ENHANCED EXTRACTION RESULTS")
        print("="*60)
        
        print(f"📄 Text length: {len(extracted['text'])} characters")
        print(f"📊 Tables found: {len(extracted['tables'])}")
        print(f"📈 Charts found: {len(extracted['charts'])}")
        print(f"🔍 Structured data: {list(extracted.get('structured_data', {}).keys())}")
        
        print(f"\n📊 Quality Score: {quality_report['quality_score']}")
        print(f"✅ Recommendation: {quality_report['recommendation']}")
        
        if quality_report['missing_critical']:
            print(f"⚠️ Missing: {quality_report['missing_critical']}")
        
        # Show structured data
        structured_data = extracted.get('structured_data', {})
        if structured_data:
            print("\n💰 STRUCTURED DATA FOUND:")
            for key, value in structured_data.items():
                print(f"  {key}: {value}")
        
        # Show sample of extracted text
        print(f"\n📝 SAMPLE TEXT (first 500 chars):")
        print("-" * 40)
        print(extracted['text'][:500] + "...")
        
        # Show tables
        if extracted['tables']:
            print(f"\n📊 TABLES FOUND ({len(extracted['tables'])}):")
            for i, table in enumerate(extracted['tables'][:3]):  # Show first 3 tables
                print(f"  Table {i+1} (Page {table.get('page', 'N/A')}):")
                if 'text' in table:
                    print(f"    {table['text'][:200]}...")
        
        return extracted
        
    except Exception as e:
        print(f"❌ Error during enhanced extraction: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_enhanced_extraction() 