"""
Exa Search Utilities - for high-quality, targeted web searches.
"""

import os
from exa_py import Exa
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

def find_linkedin_url_with_exa(name: str, company_name: str, evaluator=None) -> str:
    """
    Uses Exa's search API to find the most likely LinkedIn profile URL for an executive.
    Exa is optimized for finding specific, high-quality sources like official profiles.
    """
    exa_api_key = os.getenv("EXA_API_KEY")
    if not exa_api_key:
        print("[Exa Search] EXA_API_KEY not found in .env file. Skipping search.")
        return ""

    exa = Exa(api_key=exa_api_key)
    
    # A more sophisticated query that guides Exa to the right kind of page
    query = f"The official LinkedIn profile page for {name}, who is the {company_name}."
    
    try:
        print(f"[Exa Search] Searching for LinkedIn profile for: {name} at {company_name}")
        search_response = exa.search(
            query,
            num_results=3,  # Check the top 3 results
            include_domains=["linkedin.com"],  # Restrict search to LinkedIn
            type="keyword"  # Use keyword search for more precise matching
        )

        # Log token usage if evaluator is provided
        if evaluator and hasattr(search_response, 'api_cost'):
            # Exa's API cost can be used as a proxy for token usage
            evaluator.log_agent_tokens("EXA_LINKEDIN_SEARCH", 0, int(search_response.api_cost * 1000), "exa")

        if search_response.results:
            # Find the most likely URL (often the first result is the best)
            for result in search_response.results:
                # A simple validation to ensure it's a profile URL
                if "/in/" in result.url:
                    print(f"[Exa Search] Found URL: {result.url}")
                    return result.url
        
        print(f"[Exa Search] No suitable LinkedIn profile found in the top results for {name}.")
        return ""

    except Exception as e:
        print(f"[Exa Search] An error occurred: {e}")
        return ""
