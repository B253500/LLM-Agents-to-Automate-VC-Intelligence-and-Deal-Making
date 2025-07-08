import asyncio
import os
from memo_api.services import memo_generator
from core.schemas import StartupProfile

# Create a StartupProfile object for StoreDot
profile = StartupProfile(
    founder_name="Doron Myersdorf",
    startup_id="storedot-001",
    name="StoreDot",
    sector="Battery Technology",
    website="https://www.store-dot.com",
    funding_stage="Series B"
)

pdf_path = "data/storedot.pdf"  # Path to your pitch deck
meta = {
    "currentRound": "Series B",
    "proposedValuation": "$100,000,000",
    "valuationDate": "2024-07-01",
    "extractedText": "Sample extracted text from StoreDot's pitch deck."
}
trace_id = "test-run-storedot"

async def main():
    print("🚀 Starting memo generation...")
    print(f"📄 Processing: {pdf_path}")
    print(f"🏢 Company: {profile.name}")
    print(f"📊 Sector: {profile.sector}")
    
    # Generate memo (HTML and PDF)
    result = await memo_generator.generate(profile, pdf_path, meta, trace_id)
    
    print("\n✅ Memo generation completed!")
    print(f"📄 HTML memo: {result['html']}")
    print(f"📊 PDF memo: {result['pdf']}")
    
    # Open the files in browser/PDF viewer
    if os.path.exists(result['html']):
        print(f"\n🌐 Opening HTML memo in browser...")
        os.system(f"open {result['html']}")
    
    if os.path.exists(result['pdf']) and result['pdf'].endswith('.pdf'):
        print(f"📖 Opening PDF memo...")
        os.system(f"open {result['pdf']}")

if __name__ == "__main__":
    asyncio.run(main()) 