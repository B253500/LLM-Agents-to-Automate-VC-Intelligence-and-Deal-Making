import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile
from core.perplexity_utils import search_perplexity
import re

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

def get_smart_esg_context(text: str) -> str:
    """Extract ESG-relevant sections from text to create a focused summary."""
    esg_keywords = [
        'esg', 'environmental', 'social', 'governance', 'sustainability', 
        'impact', 'ethical', 'diversity', 'inclusion', 'csr', 
        'corporate social responsibility', 'carbon footprint', 'renewable',
        'employee welfare', 'community', 'supply chain', 'data privacy',
        'board structure', 'compliance', 'regulation'
    ]
    
    esg_sections = []
    for keyword in esg_keywords:
        pattern = re.compile(rf'.{{0,1000}}{keyword}.{{0,1000}}', re.IGNORECASE)
        matches = pattern.findall(text)
        esg_sections.extend(matches)
        
    seen = set()
    unique_sections = [s for s in esg_sections if not (s in seen or seen.add(s))]
    
    combined_context = '\n\n'.join(unique_sections)
    return combined_context[:10000]

SYSTEM = """
You are a top-tier ESG (Environmental, Social, Governance) analyst for a venture capital firm. Your task is to provide a comprehensive and professional ESG analysis for an investment memo based SOLELY on the provided company materials.

Your response must be structured and detailed. Follow these instructions precisely:

1.  **Analyze each ESG pillar separately and provide a detailed paragraph for each.**
    *   **Environmental**: Assess the company's environmental impact. Consider its carbon footprint, use of renewable resources, waste management, and any environmental initiatives mentioned in the text.
    *   **Social**: Evaluate the company's social impact. Discuss its policies on diversity and inclusion, employee welfare, customer data privacy, and community engagement mentioned in the text.
    *   **Governance**: Examine the company's corporate governance. Look at its board structure, executive compensation, transparency, and compliance with regulations mentioned in the text.

2.  **Provide a final "Overall ESG Summary" paragraph.** This should be a concise (4-6 sentence) synthesis of your findings from the three pillars, offering a balanced view of the company's ESG profile and highlighting the most material risks and opportunities for a VC investor, based only on the provided text.

3.  **Use a professional and analytical tone.** The analysis should be objective and evidence-based.

4.  **Synthesize, Don't Just List**: Do not simply list facts from the context. Synthesize the information to form a coherent and insightful analysis for each section.

5.  **Handle Missing Information**: If the provided information is insufficient for any section, state this professionally (e.g., "The provided materials lack specific details on the company's environmental policies, which requires further due diligence."). Do not hallucinate or use external knowledge.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("human", "Company Name: {company_name}\nSector: {sector}\n\nPitch Deck Context:\n---\n{context}\n---")
])

def run_esg_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    """Runs the comprehensive ESG analysis chain based only on deck context."""
    
    print("[ESG Chain] Starting ESG analysis from deck context...")
    
    # Step 1: Get smart context from the pitch deck
    deck_context = get_smart_esg_context(full_text)
    if deck_context:
        print(f"[ESG Chain] Extracted {len(deck_context)} chars of ESG context from the deck.")

    # Step 2: Invoke the LLM with the comprehensive prompt (no web search)
    try:
        prompt = PROMPT.format(
            company_name=profile.name,
            sector=profile.sector,
            context=deck_context or "No ESG information was found in the pitch deck."
        )
        
        response = llm.invoke(prompt).content.strip()
        
        # --- Final Cleanup ---
        cleaned_response = re.sub(r'Here is the ESG analysis.*?\n', '', response, flags=re.IGNORECASE).strip()
        
        profile.esg_summary = cleaned_response
        print("[ESG Chain] Successfully generated ESG analysis.")

    except Exception as e:
        print(f"[ESG Chain] An unexpected error occurred: {e}")
        profile.esg_summary = "An error occurred during the ESG analysis, requiring further manual review."

    return profile
