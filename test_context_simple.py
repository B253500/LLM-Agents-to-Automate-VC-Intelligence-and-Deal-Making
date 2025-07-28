#!/usr/bin/env python3
"""
Simple test to show how extracted context works
"""

import json
import re

def test_extracted_context():
    """Test how extracted context works with real StoreDot data"""
    
    # Load the actual extracted data from StoreDot PDF
    cache_file = "extraction_cache/storedot.pdf_70f0efbe04165831c2d2b807ff7d3227ce6f59d2.json"
    
    try:
        with open(cache_file, 'r') as f:
            extracted_data = json.load(f)
        
        print("=" * 80)
        print("HOW EXTRACTED CONTEXT WORKS")
        print("=" * 80)
        
        # Extract key information from the text
        text = extracted_data["text"]
        
        print("\n1. RAW EXTRACTED TEXT (first 500 chars):")
        print("-" * 50)
        print(text[:500])
        print("...")
        
        print(f"\nTotal text length: {len(text)} characters")
        
        print("\n\n2. KEY METRICS EXTRACTED FROM TEXT:")
        print("-" * 50)
        
        # Extract key metrics using regex
        metrics = {}
        
        # Company name
        metrics['company'] = "StoreDot"
        
        # Funding
        funding_match = re.search(r'\$(\d+)M.*invested', text)
        if funding_match:
            metrics['funding'] = f"${int(funding_match.group(1))}M"
        
        # Employees
        employees_match = re.search(r'(\d+)\s*employees', text)
        if employees_match:
            metrics['employees'] = employees_match.group(1)
        
        # Patents
        patents_match = re.search(r'(\d+)\+?\s*patents', text)
        if patents_match:
            metrics['patents'] = patents_match.group(1)
        
        # Energy density
        energy_match = re.search(r'(\d+)\s*Wh/kg', text)
        if energy_match:
            metrics['energy_density'] = f"{energy_match.group(1)} Wh/kg"
        
        # Cycle life
        cycle_match = re.search(r'>(\d+)\s*consecutive.*cycles', text)
        if cycle_match:
            metrics['cycle_life'] = f"{cycle_match.group(1)} cycles"
        
        # Market size
        market_match = re.search(r'\$(\d+)B.*Addressable.*Market', text)
        if market_match:
            metrics['TAM'] = f"${market_match.group(1)}B"
        
        # Print extracted metrics
        for key, value in metrics.items():
            print(f"  {key.title()}: {value}")
        
        print("\n\n3. HOW CONTEXT IS BUILT:")
        print("-" * 50)
        print("The system builds context by:")
        print("  1. Extracting structured data from PDF text")
        print("  2. Mapping it to profile fields")
        print("  3. Prioritizing key fields (technical, financial, market)")
        print("  4. Formatting for AI agents")
        
        print("\n\n4. CONTEXT PRIORITIZATION:")
        print("-" * 50)
        print("Priority fields (shown first in context):")
        priority_fields = [
            'energy_density_wh_kg', 'cycle_life_count', 'TAM', 'SAM', 'SOM',
            'revenue', 'funding_amount', 'patents', 'employees_count',
            'tech_maturity', 'moat_strength', 'product_description'
        ]
        
        for field in priority_fields:
            if field in metrics or field.replace('_', ' ') in metrics:
                print(f"  ✓ {field}: Found")
            else:
                print(f"  ✗ {field}: Not found")
        
        print("\n\n5. CONTEXT QUALITY ASSESSMENT:")
        print("-" * 50)
        
        # Check what data is actually being extracted
        technical_data = any(keyword in text.lower() for keyword in ['wh/kg', 'cycles', 'energy density'])
        financial_data = any(keyword in text.lower() for keyword in ['funding', 'million', 'employees', 'patents'])
        market_data = any(keyword in text.lower() for keyword in ['billion', 'market', 'tam', 'addressable'])
        
        print(f"Technical data present: {'✓' if technical_data else '✗'}")
        print(f"Financial data present: {'✓' if financial_data else '✗'}")
        print(f"Market data present: {'✓' if market_data else '✗'}")
        
        print(f"\nContext quality: {'Good' if len(text) > 1000 else 'Poor'}")
        print(f"Text length: {len(text)} characters")
        
        print("\n\n6. ISSUES WITH CURRENT EXTRACTION:")
        print("-" * 50)
        
        issues = []
        
        if not technical_data:
            issues.append("❌ Technical data not being extracted properly")
        
        if not financial_data:
            issues.append("❌ Financial data not being extracted properly")
        
        if not market_data:
            issues.append("❌ Market data not being extracted properly")
        
        if len(text) < 1000:
            issues.append("❌ Extracted text too short")
        
        if not issues:
            print("✅ No major issues identified")
        else:
            for issue in issues:
                print(issue)
        
        print("\n\n7. WHY CONTEXT MATTERS:")
        print("-" * 50)
        print("• Financial agents need funding, revenue, employee data")
        print("• Technical agents need energy density, cycle life, patent data")
        print("• Market agents need TAM, SAM, SOM data")
        print("• Without proper context, agents generate generic responses")
        print("• Good context = specific, accurate analysis")
        print("• Poor context = generic, inaccurate analysis")
        
        print("\n\n8. RECOMMENDATIONS:")
        print("-" * 50)
        print("🔧 Improve regex patterns for better extraction")
        print("🔧 Add more field mappings in enhanced extraction")
        print("🔧 Ensure structured data is properly stored in profile")
        print("🔧 Test context generation with different PDF types")
        print("🔧 Validate that agents receive the right context")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_extracted_context() 