#!/usr/bin/env python3
"""
Test script to demonstrate how extracted context works with real StoreDot data
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.schemas import StartupProfile
from core.orchestration import build_extracted_data_context
from core.hybrid_context import get_hybrid_context

def test_real_context_generation():
    """Test how extracted context is generated with real StoreDot data"""
    
    # Load the actual extracted data from StoreDot PDF
    cache_file = "extraction_cache/storedot.pdf_70f0efbe04165831c2d2b807ff7d3227ce6f59d2.json"
    
    try:
        with open(cache_file, 'r') as f:
            extracted_data = json.load(f)
        
        print("=" * 80)
        print("REAL EXTRACTED CONTEXT GENERATION TEST")
        print("=" * 80)
        
        # Create a profile with the extracted data
        profile = StartupProfile()
        
        # Extract key information from the text
        text = extracted_data["text"]
        
        # Parse key metrics from the text
        import re
        
        # Extract company name
        profile.name = "StoreDot"
        
        # Extract sector
        profile.sector = "Battery Technology"
        
        # Extract funding information
        funding_match = re.search(r'\$(\d+)M.*invested', text)
        if funding_match:
            profile.funding_amount = int(funding_match.group(1)) * 1_000_000
        
        # Extract employee count
        employees_match = re.search(r'(\d+)\s*employees', text)
        if employees_match:
            profile.employees_count = int(employees_match.group(1))
        
        # Extract patent count
        patents_match = re.search(r'(\d+)\+?\s*patents', text)
        if patents_match:
            profile.patent_count = int(patents_match.group(1))
        
        # Extract energy density
        energy_match = re.search(r'(\d+)\s*Wh/kg', text)
        if energy_match:
            profile.energy_density_wh_kg = int(energy_match.group(1))
        
        # Extract cycle life
        cycle_match = re.search(r'>(\d+)\s*consecutive.*cycles', text)
        if cycle_match:
            profile.cycle_life_count = int(cycle_match.group(1))
        
        # Extract market size
        market_match = re.search(r'\$(\d+)B.*Addressable.*Market', text)
        if market_match:
            profile.TAM = int(market_match.group(1)) * 1_000_000_000
        
        # Extract revenue (if mentioned)
        revenue_match = re.search(r'\$(\d+)M.*revenue', text)
        if revenue_match:
            profile.revenue = int(revenue_match.group(1)) * 1_000_000
        
        # Add structured data from enhanced extraction
        profile.structured_data = {
            "market_size": profile.TAM if hasattr(profile, 'TAM') and profile.TAM else None,
            "funding": profile.funding_amount if hasattr(profile, 'funding_amount') and profile.funding_amount else None,
            "patents": profile.patent_count if hasattr(profile, 'patent_count') and profile.patent_count else None,
            "employees": profile.employees_count if hasattr(profile, 'employees_count') and profile.employees_count else None,
            "energy_density": profile.energy_density_wh_kg if hasattr(profile, 'energy_density_wh_kg') and profile.energy_density_wh_kg else None,
            "cycle_life": profile.cycle_life_count if hasattr(profile, 'cycle_life_count') and profile.cycle_life_count else None
        }
        
        print("\n1. EXTRACTED DATA FROM STOREDOT PDF:")
        print("-" * 50)
        print(f"Company: {profile.name}")
        print(f"Sector: {profile.sector}")
        print(f"Funding: ${profile.funding_amount:,}" if hasattr(profile, 'funding_amount') and profile.funding_amount else "Funding: Not found")
        print(f"Employees: {profile.employees_count}" if hasattr(profile, 'employees_count') and profile.employees_count else "Employees: Not found")
        print(f"Patents: {profile.patent_count}" if hasattr(profile, 'patent_count') and profile.patent_count else "Patents: Not found")
        print(f"Energy Density: {profile.energy_density_wh_kg} Wh/kg" if hasattr(profile, 'energy_density_wh_kg') and profile.energy_density_wh_kg else "Energy Density: Not found")
        print(f"Cycle Life: {profile.cycle_life_count} cycles" if hasattr(profile, 'cycle_life_count') and profile.cycle_life_count else "Cycle Life: Not found")
        print(f"TAM: ${profile.TAM:,}" if hasattr(profile, 'TAM') and profile.TAM else "TAM: Not found")
        print(f"Revenue: ${profile.revenue:,}" if hasattr(profile, 'revenue') and profile.revenue else "Revenue: Not found")
        
        print("\n\n2. BUILDING EXTRACTED DATA CONTEXT:")
        print("-" * 50)
        
        # Build the extracted data context
        extracted_context = build_extracted_data_context(profile, text[:2000])  # Use first 2000 chars of text
        
        print(f"Context length: {len(extracted_context)} characters")
        print("\nContext content:")
        print(extracted_context)
        
        print("\n\n3. HYBRID CONTEXT FOR DIFFERENT AGENTS:")
        print("-" * 50)
        
        # Test different agent contexts
        agent_contexts = [
            ("Financial Analysis Agent", "financial analysis OR revenue OR funding OR valuation OR burn rate OR runway"),
            ("Technical DD Agent", "technical analysis OR energy density OR cycle life OR battery technology OR technical specifications"),
            ("Market Sizing Agent", "market sizing OR TAM OR SAM OR SOM OR market size OR addressable market"),
            ("Competitive Intel Agent", "competitive landscape OR competitors OR market positioning OR competitive advantage")
        ]
        
        for agent_name, query in agent_contexts:
            print(f"\n--- {agent_name.upper()} ---")
            hybrid_context = get_hybrid_context(profile, query, use_reports=False)
            print(f"Context length: {len(hybrid_context)} characters")
            print(f"First 300 chars: {hybrid_context[:300]}...")
        
        print("\n\n4. CONTEXT QUALITY ASSESSMENT:")
        print("-" * 50)
        
        # Check what data is actually being included
        context_lower = extracted_context.lower()
        
        # Check for technical data
        technical_indicators = {
            "Energy Density": any(keyword in context_lower for keyword in ['energy density', 'wh/kg', '330']),
            "Cycle Life": any(keyword in context_lower for keyword in ['cycle life', 'cycles', '1000']),
            "Patents": any(keyword in context_lower for keyword in ['patents', '100']),
            "Technology": any(keyword in context_lower for keyword in ['technology', 'battery', 'silicon'])
        }
        
        # Check for financial data
        financial_indicators = {
            "Funding": any(keyword in context_lower for keyword in ['funding', '200m', 'million']),
            "Employees": any(keyword in context_lower for keyword in ['employees', '130']),
            "Revenue": any(keyword in context_lower for keyword in ['revenue', 'sales'])
        }
        
        # Check for market data
        market_indicators = {
            "TAM": any(keyword in context_lower for keyword in ['tam', '160b', 'billion', 'addressable market']),
            "Market Size": any(keyword in context_lower for keyword in ['market size', 'market'])
        }
        
        print("Technical Data Present:")
        for indicator, present in technical_indicators.items():
            print(f"  {'✓' if present else '✗'} {indicator}")
        
        print("\nFinancial Data Present:")
        for indicator, present in financial_indicators.items():
            print(f"  {'✓' if present else '✗'} {indicator}")
        
        print("\nMarket Data Present:")
        for indicator, present in market_indicators.items():
            print(f"  {'✓' if present else '✗'} {indicator}")
        
        print(f"\nOverall Context Quality:")
        print(f"  Context length: {len(extracted_context)} characters")
        print(f"  Technical data: {sum(technical_indicators.values())}/{len(technical_indicators)} present")
        print(f"  Financial data: {sum(financial_indicators.values())}/{len(financial_indicators)} present")
        print(f"  Market data: {sum(market_indicators.values())}/{len(market_indicators)} present")
        
        quality_score = (sum(technical_indicators.values()) + sum(financial_indicators.values()) + sum(market_indicators.values())) / (len(technical_indicators) + len(financial_indicators) + len(market_indicators))
        print(f"  Overall quality score: {quality_score:.1%}")
        
        print("\n\n5. ISSUES IDENTIFIED:")
        print("-" * 50)
        
        # Identify potential issues
        issues = []
        
        if not any(technical_indicators.values()):
            issues.append("❌ No technical data found in context")
        
        if not any(financial_indicators.values()):
            issues.append("❌ No financial data found in context")
        
        if not any(market_indicators.values()):
            issues.append("❌ No market data found in context")
        
        if len(extracted_context) < 500:
            issues.append("❌ Context too short (< 500 characters)")
        
        if len(extracted_context) > 4000:
            issues.append("⚠️ Context too long (> 4000 characters)")
        
        if not issues:
            print("✅ No major issues identified")
        else:
            for issue in issues:
                print(issue)
        
        print("\n\n6. RECOMMENDATIONS:")
        print("-" * 50)
        
        if not any(technical_indicators.values()):
            print("🔧 Improve technical data extraction from PDF")
            print("   - Look for energy density, cycle life, technical specifications")
        
        if not any(financial_indicators.values()):
            print("🔧 Improve financial data extraction from PDF")
            print("   - Look for funding amounts, revenue, employee count")
        
        if not any(market_indicators.values()):
            print("🔧 Improve market data extraction from PDF")
            print("   - Look for TAM, SAM, SOM, market size information")
        
        print("🔧 Ensure enhanced extraction patterns are working correctly")
        print("🔧 Verify that structured data is being properly mapped to profile fields")
        
    except Exception as e:
        print(f"Error loading cached data: {e}")

if __name__ == "__main__":
    test_real_context_generation() 