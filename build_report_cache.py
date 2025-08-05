
import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agents.vc_report_agent import VCReportAgent

def main():
    """
    This script initializes the VCReportAgent to build the vector store cache.
    Running this will process all PDF reports and save the resulting
    vector store to disk, speeding up subsequent runs.
    """
    print("Starting the report processing to build the vector store cache...")
    print("This may take a few minutes...")

    # Load environment variables from .env file
    load_dotenv()
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("Error: OPENAI_API_KEY not found in environment variables.")
        return

    # Initializing the agent will trigger the caching process
    try:
        VCReportAgent(
            openai_api_key=openai_api_key,
            report_path="data/vc_reports"
        )
        print("\n✅ Cache built successfully!")
        print("The vector store is now saved in the './chroma_db_reports/' directory.")
        print("Subsequent runs will now load from the cache.")
    except Exception as e:
        print(f"\nAn error occurred while building the cache: {e}")

if __name__ == "__main__":
    main()
