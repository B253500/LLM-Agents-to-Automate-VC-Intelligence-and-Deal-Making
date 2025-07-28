#!/usr/bin/env python3
"""
Test to show exactly what content is being included in the extracted context
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_context_content():
    """Show exactly what's being included in the extracted context"""
    
    # Load the actual extracted data from StoreDot PDF
    cache_file = "extraction_cache/storedot.pdf_70f0efbe04165831c2d2b807ff7d3227ce6f59d2.json"
    
    try:
        with open(cache_file, 'r') as f:
            extracted_data = json.load(f)
        
        print("=" * 80)
        print("EXTRACTED CONTEXT CONTENT ANALYSIS")
        print("=" * 80)
        
        # Extract key information from the text
        text = extracted_data["text"]
        tables = extracted_data.get("tables", [])
        charts = extracted_data.get("charts", [])
        
        print(f"\n1. RAW EXTRACTED TEXT LENGTH: {len(text)} characters")
        print("-" * 50)
        
        # Use the enhanced extraction function
        from core.download_utils import extract_financial_metrics_enhanced
        extracted_metrics = extract_financial_metrics_enhanced(text, tables, charts)
        
        # Add company info
        extracted_metrics['company'] = "StoreDot"
        extracted_metrics['sector'] = "Battery Technology"
        
        print("\n2. ENHANCED EXTRACTION RESULTS:")
        print("-" * 50)
        for key, value in extracted_metrics.items():
            print(f"  {key}: {value}")
        
        print("\n\n3. SIMULATING CONTEXT GENERATION:")
        print("-" * 50)
        
        # Simulate the context generation process
        context_parts = []
        
        # Priority fields (as defined in orchestration)
        priority_fields = [
            'energy_density_wh_kg', 'cycle_life_count', 'TAM', 'SAM', 'SOM',
            'revenue', 'funding_amount', 'patents', 'employees_count',
            'tech_maturity', 'moat_strength', 'product_description'
        ]
        
        # Map enhanced extraction results to priority fields
        field_mapping = {
            'energy_density': 'energy_density_wh_kg',
            'cycle_life': 'cycle_life_count',
            'market_size': 'TAM',
            'funding': 'funding_amount',
            'patents': 'patent_count',
            'employees': 'employees_count'
        }
        
        print("Priority fields being checked:")
        for field in priority_fields:
            # Check if we have this field directly
            value = extracted_metrics.get(field)
            
            # If not found, check if we have it under a different name
            if not value:
                for enhanced_field, priority_field in field_mapping.items():
                    if priority_field == field and enhanced_field in extracted_metrics:
                        value = extracted_metrics[enhanced_field]
                        break
            
            if value:
                display_name = field.replace('_', ' ').title()
                context_parts.append(f"**{display_name}**: {value}")
                print(f"  ✓ {field}: {value}")
            else:
                print(f"  ✗ {field}: Not found")
        
        print("\n\n4. WHAT WOULD BE IN THE CONTEXT:")
        print("-" * 50)
        
        if context_parts:
            print("Context would include:")
            for part in context_parts:
                print(f"  • {part}")
        else:
            print("No priority fields found - context would be empty!")
        
        print(f"\nContext length: {sum(len(part) for part in context_parts)} characters")
        
        print("\n\n5. ISSUES IDENTIFIED:")
        print("-" * 50)
        
        issues = []
        
        # Check if technical data is missing
        if not extracted_metrics.get('energy_density') and not extracted_metrics.get('energy_density_wh_kg'):
            issues.append("❌ Energy density not extracted")
        if not extracted_metrics.get('cycle_life') and not extracted_metrics.get('cycle_life_count'):
            issues.append("❌ Cycle life not extracted")
        
        # Check if financial data is missing
        if not extracted_metrics.get('funding') and not extracted_metrics.get('funding_amount'):
            issues.append("❌ Funding amount not extracted")
        if not extracted_metrics.get('employees') and not extracted_metrics.get('employees_count'):
            issues.append("❌ Employee count not extracted")
        
        # Check if market data is missing
        if not extracted_metrics.get('market_size') and not extracted_metrics.get('TAM'):
            issues.append("❌ TAM not extracted")
        
        if not issues:
            print("✅ No major issues identified")
        else:
            for issue in issues:
                print(issue)
        
        print("\n\n6. RECOMMENDATIONS:")
        print("-" * 50)
        
        if not extracted_metrics.get('energy_density') and not extracted_metrics.get('energy_density_wh_kg'):
            print("🔧 Improve energy density extraction regex")
            print("   - Look for patterns like '300 Wh/kg', '330 Wh/kg'")
        
        if not extracted_metrics.get('cycle_life') and not extracted_metrics.get('cycle_life_count'):
            print("🔧 Improve cycle life extraction regex")
            print("   - Look for patterns like '>1000 cycles', '1200 cycles'")
        
        if not extracted_metrics.get('funding') and not extracted_metrics.get('funding_amount'):
            print("🔧 Improve funding extraction regex")
            print("   - Look for patterns like '$200M invested', '$200 million'")
        
        if not extracted_metrics.get('market_size') and not extracted_metrics.get('TAM'):
            print("🔧 Improve market size extraction regex")
            print("   - Look for patterns like '$160B TAM', '$160 billion'")
        
        print("🔧 Verify that enhanced extraction is working correctly")
        print("🔧 Check if structured data is being properly mapped to profile fields")
        
        print("\n\n7. ACTUAL TEXT SEGMENTS FOUND:")
        print("-" * 50)
        
        # Show actual text segments that contain the data
        text_segments = []
        
        import re
        
        # Look for energy density
        energy_density_segments = re.findall(r'[^.]*\d+\s*Wh/kg[^.]*', text)
        if energy_density_segments:
            text_segments.append(f"Energy Density segments: {energy_density_segments[:2]}")
        
        # Look for cycle life
        cycle_life_segments = re.findall(r'[^.]*\d+\s*cycles[^.]*', text)
        if cycle_life_segments:
            text_segments.append(f"Cycle Life segments: {cycle_life_segments[:2]}")
        
        # Look for funding
        funding_segments = re.findall(r'[^.]*\$\d+M[^.]*', text)
        if funding_segments:
            text_segments.append(f"Funding segments: {funding_segments[:2]}")
        
        # Look for market size
        market_size_segments = re.findall(r'[^.]*\$\d+B[^.]*', text)
        if market_size_segments:
            text_segments.append(f"Market Size segments: {market_size_segments[:2]}")
        
        for segment in text_segments:
            print(f"  {segment}")
        
        if not text_segments:
            print("  No relevant text segments found!")
        
        # Print new fields
        print(f"  Tech Stack: {extracted_metrics.get('tech_stack', None)}")
        print(f"  Product Roadmap: {extracted_metrics.get('product_roadmap', None)}")
        print(f"  Product Description: {extracted_metrics.get('product_description', None)}")
        
        # Print new market fields
        print(f"  CAGR: {extracted_metrics.get('cagr', None)}")
        print(f"  BEV Penetration: {extracted_metrics.get('bev_penetration', None)}")
        print(f"  OEM Investment: {extracted_metrics.get('oem_investment', None)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_context_content() 