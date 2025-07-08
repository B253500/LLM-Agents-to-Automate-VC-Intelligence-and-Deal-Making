#!/usr/bin/env python3
"""
VC Memo Generator - Command Line Interface
Usage: python run_memo.py <pdf_path> [company_name] [sector]
Example: python run_memo.py data/storedot.pdf "StoreDot" "Battery Technology"
"""

import sys
import asyncio
import os
from datetime import datetime
from pathlib import Path

# Import the memo generator service
from memo_api.services.memo_generator import generate
from core.schemas import StartupProfile

async def main():
    if len(sys.argv) < 2:
        print("Usage: python run_memo.py <pdf_path> [company_name] [sector]")
        print("Example: python run_memo.py data/storedot.pdf \"StoreDot\" \"Battery Technology\"")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Check if PDF exists
    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # Get company name and sector from command line or use defaults
    company_name = sys.argv[2] if len(sys.argv) > 2 else "Unknown Company"
    sector = sys.argv[3] if len(sys.argv) > 3 else "Technology"
    
    print(f"🚀 Starting memo generation...")
    print(f"📄 Processing: {pdf_path}")
    print(f"🏢 Company: {company_name}")
    print(f"📊 Sector: {sector}")
    
    # Create a basic startup profile
    profile = StartupProfile(
        name=company_name,
        sector=sector,
        website="",
        funding_stage="",
        founder_name="",
        tech_maturity="",
        moat_strength="",
        founder_fit_score=None,
        prior_exits=0,
        TAM=0.0,
        SAM=0.0,
        SOM=0.0,
        cash_burn_12m=0.0,
        runway_months=0.0,
        implied_valuation=0.0,
        risk_score=None,
        risk_flags=[],
        top_competitors=[]
    )
    
    # Create metadata
    meta = {
        "timestamp": datetime.now().isoformat(),
        "pdf_path": pdf_path,
        "company_name": company_name,
        "sector": sector
    }
    
    # Generate trace ID
    trace_id = f"memo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"🚀 Starting memo generation for {company_name}")
    
    try:
        # Generate memo
        result = await generate(profile, pdf_path, meta, trace_id)
        
        if result.get("html") and result.get("pdf"):
            print("✅ Memo generation completed!")
            print(f"📄 HTML memo: {result['html']}")
            print(f"📊 PDF memo: {result['pdf']}")
            
            # Try to open the files
            try:
                import subprocess
                import platform
                
                system = platform.system()
                if system == "Darwin":  # macOS
                    subprocess.run(["open", result["html"]])
                    subprocess.run(["open", result["pdf"]])
                elif system == "Windows":
                    subprocess.run(["start", result["html"]], shell=True)
                    subprocess.run(["start", result["pdf"]], shell=True)
                elif system == "Linux":
                    subprocess.run(["xdg-open", result["html"]])
                    subprocess.run(["xdg-open", result["pdf"]])
                    
                print("🌐 Opening HTML memo in browser...")
                print("📖 Opening PDF memo...")
            except Exception as e:
                print(f"⚠️  Could not open files automatically: {e}")
                print(f"   HTML: {result['html']}")
                print(f"   PDF: {result['pdf']}")
        else:
            print("❌ Error: Memo generation failed")
            print(f"Result: {result}")
            
    except Exception as e:
        print(f"❌ Error during memo generation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 