#!/usr/bin/env python3
"""
Comprehensive test for financial analysis functionality
Tests both the chain and the formatting functions
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schemas import StartupProfile
from chains.financial_analysis_chain import run_financial_analysis_chain
from agents.financial_analysis_agent import build_financial_analysis_agent

def test_financial_chain_with_sample_data():
    """Test the financial analysis chain with sample data"""
    print("=" * 60)
    print("TESTING FINANCIAL ANALYSIS CHAIN WITH SAMPLE DATA")
    print("=" * 60)
    
    # Create a test profile with realistic data
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    
    # Add some test financial data
    profile.funding_amount = "206000000"
    profile.implied_valuation = 1500000000
    profile.latest_round_amount = 80000000
    profile.total_funding_raised = 200000000
    
    print(f"Initial profile:")
    print(f"  Company: {profile.name}")
    print(f"  Sector: {profile.sector}")
    print(f"  Funding Amount: {profile.funding_amount}")
    print(f"  Valuation: {profile.implied_valuation}")
    print(f"  Latest Round: {profile.latest_round_amount}")
    print(f"  Total Funding: {profile.total_funding_raised}")
    print()
    
    # Test the chain
    try:
        updated_profile = run_financial_analysis_chain(profile)
        print("✅ Financial chain completed successfully")
        
        # Check what financial data was added/updated
        financial_fields = [
            'revenue', 'cash_burn_12m', 'runway_months', 'implied_valuation',
            'funding_amount', 'funding_rounds_count', 'latest_round_type',
            'latest_round_date', 'latest_round_amount', 'total_funding_raised',
            'web_sources', 'web_financial_data'
        ]
        
        print("\nFinancial data after chain:")
        for field in financial_fields:
            value = getattr(updated_profile, field, None)
            if value is not None:
                print(f"  {field}: {value}")
        
        return updated_profile
        
    except Exception as e:
        print(f"❌ Financial chain failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_financial_agent():
    """Test the financial analysis agent"""
    print("\n" + "=" * 60)
    print("TESTING FINANCIAL ANALYSIS AGENT")
    print("=" * 60)
    
    # Create a test profile
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.sector = "Battery Technology"
    profile.funding_amount = "206000000"
    
    print(f"Initial profile:")
    print(f"  Company: {profile.name}")
    print(f"  Sector: {profile.sector}")
    print(f"  Funding Amount: {profile.funding_amount}")
    print()
    
    # Test the agent
    try:
        agent, task = build_financial_analysis_agent(profile)
        print("✅ Financial agent built successfully")
        
        # Run the task
        result = task.callback()
        print("✅ Financial agent task completed")
        
        # Parse the result
        try:
            agent_data = json.loads(result)
            print(f"✅ Agent output parsed successfully")
            print(f"Agent returned {len(agent_data)} fields")
            
            # Show the agent output
            for key, value in agent_data.items():
                if value is not None:
                    print(f"  {key}: {value}")
                    
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse agent output as JSON: {e}")
            print(f"Raw output: {result[:500]}...")
            
    except Exception as e:
        print(f"❌ Financial agent failed: {e}")
        import traceback
        traceback.print_exc()

def test_financial_formatting():
    """Test the financial formatting functions"""
    print("\n" + "=" * 60)
    print("TESTING FINANCIAL FORMATTING FUNCTIONS")
    print("=" * 60)
    
    # Import the formatting functions from main.py
    try:
        from main import format_clean_financials_section, format_enhanced_financials_section
        print("✅ Successfully imported formatting functions")
    except ImportError as e:
        print(f"❌ Failed to import formatting functions: {e}")
        return
    
    # Create a test profile with financial data
    profile = StartupProfile()
    profile.name = "StoreDot"
    profile.implied_valuation = 1500000000
    profile.latest_round_amount = 80000000
    profile.total_funding_raised = 200000000
    profile.web_sources = ["https://crunchbase.com/company/storedot", "https://example.com/funding"]
    
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # Test clean financial formatting
    print("\n--- Testing format_clean_financials_section ---")
    try:
        clean_output = format_clean_financials_section(profile, current_date)
        print("✅ Clean financial formatting completed")
        print("Output:")
        print(clean_output)
        
        # Check if the output contains expected elements
        expected_elements = [
            "📊 Financial Analysis",
            "Current Valuation",
            "Latest Funding Round",
            "Total Funding Raised",
            "Data Sources"
        ]
        
        for element in expected_elements:
            if element in clean_output:
                print(f"✅ Found expected element: {element}")
            else:
                print(f"❌ Missing expected element: {element}")
                
    except Exception as e:
        print(f"❌ Clean financial formatting failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test enhanced financial formatting
    print("\n--- Testing format_enhanced_financials_section ---")
    try:
        enhanced_output = format_enhanced_financials_section(profile, current_date)
        print("✅ Enhanced financial formatting completed")
        print("Output:")
        print(enhanced_output)
        
    except Exception as e:
        print(f"❌ Enhanced financial formatting failed: {e}")
        import traceback
        traceback.print_exc()

def test_financial_chain_with_no_data():
    """Test the financial analysis chain with no financial data"""
    print("\n" + "=" * 60)
    print("TESTING FINANCIAL ANALYSIS CHAIN WITH NO DATA")
    print("=" * 60)
    
    # Create a test profile with minimal data
    profile = StartupProfile()
    profile.name = "TestCompany"
    profile.sector = "Technology"
    
    print(f"Initial profile (no financial data):")
    print(f"  Company: {profile.name}")
    print(f"  Sector: {profile.sector}")
    print()
    
    # Test the chain
    try:
        updated_profile = run_financial_analysis_chain(profile)
        print("✅ Financial chain completed successfully with no data")
        
        # Check if the chain handled the no-data case gracefully
        financial_fields = [
            'revenue', 'cash_burn_12m', 'runway_months', 'implied_valuation',
            'latest_round_amount', 'total_funding_raised'
        ]
        
        print("\nFinancial data after chain (should be mostly None):")
        for field in financial_fields:
            value = getattr(updated_profile, field, None)
            print(f"  {field}: {value}")
        
        return updated_profile
        
    except Exception as e:
        print(f"❌ Financial chain failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_financial_formatting_with_no_data():
    """Test financial formatting when there's no financial data"""
    print("\n" + "=" * 60)
    print("TESTING FINANCIAL FORMATTING WITH NO DATA")
    print("=" * 60)
    
    try:
        from main import format_clean_financials_section
    except ImportError as e:
        print(f"❌ Failed to import formatting function: {e}")
        return
    
    # Create a test profile with no financial data
    profile = StartupProfile()
    profile.name = "TestCompany"
    current_date = datetime.now().strftime("%B %d, %Y")
    
    print(f"Testing with profile: {profile.name}")
    print(f"Current date: {current_date}")
    print()
    
    try:
        output = format_clean_financials_section(profile, current_date)
        print("✅ Financial formatting completed with no data")
        print("Output:")
        print(output)
        
        # Check if it shows the expected "no data" message
        if "No detailed financials were disclosed" in output:
            print("✅ Correctly shows 'no data' message")
        else:
            print("❌ Should show 'no data' message")
            
    except Exception as e:
        print(f"❌ Financial formatting failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all financial analysis tests"""
    print("🚀 STARTING COMPREHENSIVE FINANCIAL ANALYSIS TESTS")
    print("=" * 80)
    
    # Test 1: Financial chain with sample data
    test_financial_chain_with_sample_data()
    
    # Test 2: Financial agent
    test_financial_agent()
    
    # Test 3: Financial formatting
    test_financial_formatting()
    
    # Test 4: Financial chain with no data
    test_financial_chain_with_no_data()
    
    # Test 5: Financial formatting with no data
    test_financial_formatting_with_no_data()
    
    print("\n" + "=" * 80)
    print("✅ ALL FINANCIAL ANALYSIS TESTS COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    main() 