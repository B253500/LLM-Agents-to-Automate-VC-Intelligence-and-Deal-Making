#!/usr/bin/env python3
"""
Test script for financial analysis chain and agent
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.schemas import StartupProfile
from chains.financial_analysis_chain import run_financial_analysis_chain
from agents.financial_analysis_agent import build_financial_analysis_agent
from core.download_utils import load_from_cache

def test_financial_chain():
    """Test the financial analysis chain directly"""
    print("=" * 60)
    print("TESTING FINANCIAL ANALYSIS CHAIN")
    print("=" * 60)
    
    # Create a test profile with some data
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Add some test financial data
    profile.revenue = 2023.0  # This should be filtered out
    profile.cash_burn_12m = 2023.0  # This should be filtered out
    profile.implied_valuation = 2023.0  # This should be filtered out
    
    # Add some valid data
    profile.funding_amount = "206000000"
    profile.implied_valuation = 1500000000
    
    print(f"Initial profile:")
    print(f"  Revenue: {profile.revenue}")
    print(f"  Cash Burn: {profile.cash_burn_12m}")
    print(f"  Valuation: {profile.implied_valuation}")
    print(f"  Total Funding: {profile.funding_amount}")
    print()
    
    # Test the chain
    try:
        updated_profile = run_financial_analysis_chain(profile)
        print("✅ Financial chain completed successfully")
        print(f"Updated profile has {len(updated_profile.model_fields)} fields")
        
        # Check what financial data was added
        financial_fields = [
            'revenue', 'cash_burn_12m', 'runway_months', 'implied_valuation',
            'funding_amount', 'funding_rounds_count', 'latest_round_type',
            'latest_round_date', 'latest_round_amount', 'web_financial_data'
        ]
        
        print("\nFinancial data after chain:")
        for field in financial_fields:
            value = getattr(updated_profile, field, None)
            if value:
                print(f"  {field}: {value}")
        
    except Exception as e:
        print(f"❌ Financial chain failed: {e}")
        import traceback
        traceback.print_exc()

def test_financial_agent():
    """Test the financial analysis agent directly"""
    print("\n" + "=" * 60)
    print("TESTING FINANCIAL ANALYSIS AGENT")
    print("=" * 60)
    
    # Create a test profile
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Add some test data
    profile.revenue = 2023.0  # Should be filtered out
    profile.cash_burn_12m = 2023.0  # Should be filtered out
    profile.funding_amount = "206000000"  # Valid data
    
    print(f"Initial profile:")
    print(f"  Revenue: {profile.revenue}")
    print(f"  Cash Burn: {profile.cash_burn_12m}")
    print(f"  Total Funding: {profile.funding_amount}")
    print()
    
    # Test the agent
    try:
        agent, task = build_financial_analysis_agent(profile)
        print("✅ Financial agent built successfully")
        
        # Run the task
        result = task.callback()
        print("✅ Financial agent task completed")
        
        # Parse the result
        if result:
            try:
                result_data = json.loads(result)
                print(f"Agent result keys: {list(result_data.keys())}")
                
                # Check for financial data in the result
                if 'revenue' in result_data:
                    print(f"  Revenue in result: {result_data['revenue']}")
                if 'cash_burn_12m' in result_data:
                    print(f"  Cash Burn in result: {result_data['cash_burn_12m']}")
                if 'implied_valuation' in result_data:
                    print(f"  Valuation in result: {result_data['implied_valuation']}")
                    
            except json.JSONDecodeError:
                print("Result is not valid JSON")
                print(f"Result preview: {result[:200]}...")
        
    except Exception as e:
        print(f"❌ Financial agent failed: {e}")
        import traceback
        traceback.print_exc()

def test_financial_formatting():
    """Test the financial formatting function"""
    print("\n" + "=" * 60)
    print("TESTING FINANCIAL FORMATTING")
    print("=" * 60)
    
    # Import the formatting function
    from main import format_financials_section_original as format_financials_section
    
    # Create test profiles with different scenarios
    test_cases = [
        {
            "name": "Empty Profile",
            "profile": StartupProfile()
        },
        {
            "name": "Basic Financial Data",
            "profile": StartupProfile(
                revenue=1000000,
                cash_burn_12m=500000,
                implied_valuation=50000000,
                total_funding_raised=2000000
            )
        },
        {
            "name": "Sample Company Profile",
            "profile": StartupProfile(
                name="Sample Company"
            )
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_case['name']} ---")
        profile = test_case['profile']
        
        print(f"Input data:")
        print(f"  Revenue: {getattr(profile, 'revenue', 'None')}")
        print(f"  Cash Burn: {getattr(profile, 'cash_burn_12m', 'None')}")
        print(f"  Valuation: {getattr(profile, 'implied_valuation', 'None')}")
        print(f"  Total Funding: {getattr(profile, 'total_funding_raised', 'None')}")
        
        # Test the formatting
        try:
            formatted = format_financials_section(profile, "December 2024")
            print(f"\nFormatted output:")
            print(formatted)
            print(f"Output length: {len(formatted)} characters")
            
        except Exception as e:
            print(f"❌ Formatting failed: {e}")
            import traceback
            traceback.print_exc()

def test_with_real_data():
    """Test with real extracted data from a sample company"""
    print("\n" + "=" * 60)
    print("TESTING WITH REAL SAMPLE COMPANY DATA")
    print("=" * 60)
    
    # Try to load cached sample company data
    cache_file = "extraction_cache/sample_company.pdf_70f0efbe04165831c2d2b807ff7d3227ce6f59d2.json"
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                extracted_data = json.load(f)
            
            print("✅ Loaded cached sample company data")
            print(f"Text length: {len(extracted_data['text'])} characters")
            
            # Create profile with real data
            profile = StartupProfile()
            profile.name = "Sample Company"
            profile.sector = "Technology"
            
            # Add structured data if available
            if 'structured_data' in extracted_data:
                structured_data = extracted_data['structured_data']
                print(f"Structured data keys: {list(structured_data.keys())}")
                
                # Map structured data to profile
                if 'revenue' in structured_data:
                    profile.revenue = structured_data['revenue']
                if 'funding' in structured_data:
                    profile.total_funding_raised = structured_data['funding']
                if 'market_size' in structured_data:
                    profile.TAM = structured_data['market_size']
            
            print(f"\nProfile with real data:")
            print(f"  Revenue: {getattr(profile, 'revenue', 'None')}")
            print(f"  Total Funding: {getattr(profile, 'funding_amount', 'None')}")
            print(f"  TAM: {getattr(profile, 'TAM', 'None')}")
            
            # Test formatting
            from main import format_financials_section_original as format_financials_section
            formatted = format_financials_section(profile, "December 2024")
            print(f"\nFormatted output with real data:")
            print(formatted)
            
        except Exception as e:
            print(f"❌ Failed to process real data: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ No cached sample company data found")
        print("💡 To test with real data, place a sample company PDF in the extraction_cache directory")

if __name__ == "__main__":
    print("🧪 Testing Financial Analysis Components")
    print("=" * 60)
    
    # Test the chain
    test_financial_chain()
    
    # Test the agent
    test_financial_agent()
    
    # Test the formatting
    test_financial_formatting()
    
    # Test with real data
    test_with_real_data()
    
    print("\n" + "=" * 60)
    print("✅ Testing completed!")
    print("=" * 60) 