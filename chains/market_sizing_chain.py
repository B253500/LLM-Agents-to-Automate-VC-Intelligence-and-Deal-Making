import json
import re
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing import Optional
from core.llm_logging import log_usage_from_message
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context
from core.perplexity_utils import search_perplexity

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

def get_smart_market_context(text):
    """Extract market-relevant sections from text and create a focused 10k summary"""
    
    # High-priority market keywords (these get more context)
    high_priority_keywords = [
        'market', 'TAM', 'SAM', 'SOM', 'market size', 'market opportunity',
        'growth', 'CAGR', 'industry', 'sector', 'customer', 'target',
        'competitive', 'competitor', 'market share', 'market position'
    ]
    
    # Medium-priority keywords (business context)
    medium_priority_keywords = [
        'business model', 'pricing', 'revenue', 'partnership', 'geographic',
        'segment', 'validation', 'trend', 'driver', 'barrier'
    ]
    
    # Find high-priority sections with more context
    high_priority_sections = []
    for keyword in high_priority_keywords:
        # Get more context around high-priority keywords (1000 chars each side)
        pattern = re.compile(rf'.{{0,1000}}{keyword}.{{0,1000}}', re.IGNORECASE)
        matches = pattern.findall(text)
        high_priority_sections.extend(matches)
    
    # Find medium-priority sections with less context
    medium_priority_sections = []
    for keyword in medium_priority_keywords:
        # Get less context around medium-priority keywords (500 chars each side)
        pattern = re.compile(rf'.{{0,500}}{keyword}.{{0,500}}', re.IGNORECASE)
        matches = pattern.findall(text)
        medium_priority_sections.extend(matches)
    
    # Combine all sections, prioritizing high-priority ones
    all_sections = high_priority_sections + medium_priority_sections
    
    # Remove duplicates while preserving order
    seen = set()
    unique_sections = []
    for section in all_sections:
        if section not in seen:
            seen.add(section)
            unique_sections.append(section)
    
    # Combine sections
    combined_context = '\n\n'.join(unique_sections)
    
    # If we don't have enough context, add strategic parts of the text
    if len(combined_context) < 5000:
        # Add the end of the text (where market data often is)
        combined_context += '\n\n' + text[-8000:]  # Add last 8k chars
    
    # Limit to 10k chars total for efficiency
    return combined_context[:10000]

def format_market_size(val):
    """
    Format market size values (TAM, SAM, SOM) preserving original units from source.
    If the value is already a string with units, keep it as-is.
    If it's a number, format it nicely with appropriate units (B, M, K).
    """
    # If it's already a string (with units), return as-is
    if isinstance(val, str):
        return val
    
    try:
        val = float(val)
    except (TypeError, ValueError):
        return str(val)
    
    # For numeric values, format nicely with appropriate units
    abs_val = abs(val)
    if abs_val >= 1_000_000_000:
        if val % 1_000_000_000 == 0:
            return f"${val/1_000_000_000:,.0f}B"
        else:
            return f"${val/1_000_000_000:,.1f}B"
    elif abs_val >= 1_000_000:
        if val % 1_000_000 == 0:
            return f"${val/1_000_000:,.0f}M"
        else:
            return f"${val/1_000_000:,.1f}M"
    elif abs_val >= 1_000:
        if val % 1_000 == 0:
            return f"${val/1_000:,.0f}K"
        else:
            return f"${val/1_000:,.1f}K"
    else:
        if val % 1 == 0:
            return f"${val:,.0f}"
        else:
            return f"${val:,.1f}"


def format_growth_rate(val):
    """
    Formats growth rate values to always include a percentage sign.
    Removes trailing .0 if it's a whole number.
    """
    if val is None:
        return "unknown"
    
    val_str = str(val).strip()
    
    # If it already has a %, just return it
    if val_str.endswith('%'):
        return val_str
        
    try:
        num = float(val_str)
        # Check if it's a whole number
        if num == int(num):
            return f"{int(num)}%"
        else:
            # Format to one decimal place if not whole
            return f"{num:.1f}%"
    except (ValueError, TypeError):
        # If it's not a number, just append %
        return f"{val_str}%"


def ai_extract_market_data(text):
    """AI-powered extraction of any market-related data from text"""
    try:
        from config import Config
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        
        prompt = f"""
You are a market research analyst extracting market-related data from a company pitch deck.

Extract ALL market-related information from this text and return it as a JSON object with the following structure:

{{
    "market_size": {{
        "TAM": "value and unit (e.g., $46B)",
        "SAM": "value and unit (e.g., $10B)", 
        "SOM": "value and unit (e.g., $1B)",
        "market_size": "any other market size metrics"
    }},
    "market_metrics": {{
        "total_customers": "number of customers/users",
        "active_customers": "number of active customers",
        "target_customers": "number of target customers",
        "market_penetration": "penetration percentage",
        "revenue_per_customer": "revenue per customer",
        "customer_growth_rate": "customer growth rate"
    }},
    "geographic_data": {{
        "global_market": "global market size or scope",
        "core_geographies": "core geographic markets",
        "international_presence": "international market presence",
        "regional_breakdown": "regional market breakdown"
    }},
    "market_definition": {{
        "target_segment": "target market segment definition",
        "customer_type": "type of customers targeted",
        "market_criteria": "criteria for market inclusion"
    }},
    "growth_metrics": {{
        "CAGR": "compound annual growth rate",
        "growth_rate": "market growth rate",
        "growth_drivers": "key growth drivers"
    }},
    "competitive_data": {{
        "market_share": "market share information",
        "competitors": "competitor information",
        "competitive_advantage": "competitive advantages"
    }},
    "source_attribution": {{
        "data_source": "source of market data",
        "research_firm": "research firm or analyst",
        "date": "date of market data"
    }}
}}

IMPORTANT:
- Extract ANY market-related data, not just predefined fields
- If a field is not found, use null
- For numbers, include units (e.g., "$46B", "200,000+", "46M")
- For text fields, extract the exact wording from the text
- Be comprehensive - extract everything that could be market-related

Market-Relevant Text to analyze:
{get_smart_market_context(text)}
"""
        
        response = llm.invoke(prompt).content.strip()
        
        # Parse the JSON response
        import json
        
        # Clean up the response to extract JSON
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            market_data = json.loads(json_match.group())
            print(f"[AI Market Extraction] Extracted {len(market_data)} market data categories")
            return market_data
        else:
            print(f"[AI Market Extraction] Could not parse JSON from response")
            return {}
            
    except Exception as e:
        print(f"[AI Market Extraction] Error: {e}")
        return {}


def extract_market_size_from_text(text):
    """Extract market size data using regex patterns with validation"""
    results = {}
    
    try:
        # Enhanced regex patterns for market size extraction
        patterns = {
            "TAM": [
                r'(\$[\d,\.]+[KMB]?)\s*TAM',
                r'TAM[^\d$]*(\$[\d,\.]+[KMB]?)',
                r'(\$[\d,\.]+[KMB]?)\s*total\s*addressable\s*market',
                r'total\s*addressable\s*market[^\d$]*(\$[\d,\.]+[KMB]?)',
                r'(\$[\d,\.]+[KMB]?)\s*market\s*size',
                r'market\s*size[^\d$]*(\$[\d,\.]+[KMB]?)'
            ],
            "SAM": [
                r'(\$[\d,\.]+[KMB]?)\s*SAM',
                r'SAM[^\d$]*(\$[\d,\.]+[KMB]?)',
                r'(\$[\d,\.]+[KMB]?)\s*serviceable\s*addressable\s*market',
                r'serviceable\s*addressable\s*market[^\d$]*(\$[\d,\.]+[KMB]?)'
            ],
            "SOM": [
                r'(\$[\d,\.]+[KMB]?)\s*SOM',
                r'SOM[^\d$]*(\$[\d,\.]+[KMB]?)',
                r'(\$[\d,\.]+[KMB]?)\s*serviceable\s*obtainable\s*market',
                r'serviceable\s*obtainable\s*market[^\d$]*(\$[\d,\.]+[KMB]?)'
            ],
            "market_size": [
                r'(\$[\d,\.]+[KMB]?)\s*market',
                r'market[^\d$]*(\$[\d,\.]+[KMB]?)',
                r'(\$[\d,\.]+[KMB]?)\s*industry',
                r'industry[^\d$]*(\$[\d,\.]+[KMB]?)'
            ],
            "CAGR": [
                r'(\d+\.?\d*)\s*%\s*CAGR',
                r'CAGR[^\d]*(\d+\.?\d*)%',
                r'(\d+\.?\d*)\s*CAGR'
            ],
            "growth_rate": [
                r'(\d+\.?\d*)\s*%\s*growth',
                r'growth[^\d]*(\d+\.?\d*)%',
                r'\+(\d+\.?\d*)\s*%'
            ]
        }
        
        for market_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    val = match.group(1)
                    
                    # Parse the value appropriately
                    if market_type in ['CAGR', 'growth_rate']:
                        try:
                            parsed_value = float(val.replace(',', ''))
                            results[market_type] = parsed_value
                            print(f"[Market Extraction] Found {market_type}={parsed_value}")
                            break
                        except:
                            # If parsing fails, store as string
                            results[market_type] = val.strip()
                            print(f"[Market Extraction] Found {market_type}={val.strip()} (as string)")
                            break
                    else:
                        # For dollar amounts, store as string to preserve units
                        results[market_type] = val.strip()
                        print(f"[Market Extraction] Found {market_type}={val.strip()}")
                        break
                        
    except Exception as e:
        print(f"[Market Extraction] Error extracting market data: {e}")
    
    return results


def web_search_market_context(company_name, sector):
    if not company_name and not sector:
        return ""
    query = f"Latest market size, growth rate, and trends for {company_name or 'the company'} in the {sector or ''} sector. Provide TAM, SAM, SOM if available, and cite sources."
    result = search_perplexity(query)
    return result or ""

SYSTEM = """
You are a top-tier VC market research analyst. Your task is to provide a detailed and professional market analysis based on the provided pitch deck context and web search results.

Your response MUST be in this exact JSON format:
{
    "market_summary": "A 4-6 sentence professional narrative summarizing the market. Cover market size, growth drivers, key trends, and competitive dynamics. Be specific and quantitative where possible. If data is sparse, note it professionally.",
    "market_size_analysis": {
        "TAM": {
            "value_usd_billions": "Total Addressable Market in billions of US dollars (e.g., 150.5). Use numbers only. If unknown, use null.",
            "description": "The original TAM figure from the source (e.g., '$150.5B', 'Approx. 2B users'). If unknown, use 'unknown'."
        },
        "SAM": {
            "value_usd_billions": "Serviceable Available Market in billions of US dollars (e.g., 45.0). Use numbers only. If unknown, use null.",
            "description": "The original SAM figure from the source (e.g., '$45B'). If unknown, use 'unknown'."
        },
        "SOM": {
            "value_usd_billions": "Serviceable Obtainable Market in billions of US dollars (e.g., 4.5). Use numbers only. If unknown, use null.",
            "description": "The original SOM figure from the source (e.g., '$4.5B'). If unknown, use 'unknown'."
        }
    },
    "growth_metrics": {
        "CAGR_percent": "Compound Annual Growth Rate as a percentage (e.g., '15.2%'). If unknown, use 'unknown'.",
        "growth_rate_percent": "Other relevant market growth rates (e.g., 'YoY growth of 20%'). If unknown, use 'unknown'."
    },
    "key_drivers": [
        "A key factor driving market growth.",
        "Another significant market driver."
    ],
    "source_commentary": "A brief commentary on the source and confidence level of the data (e.g., 'Data is from a reliable 2024 market report.' or 'Market size figures are estimated based on industry averages as the pitch deck lacks specifics.')."
}

CRITICAL INSTRUCTIONS:
1.  **Prioritize Pitch Deck**: Use figures from the 'Pitch Deck Context' as the highest priority source.
2.  **Web Search for Gaps**: Use the 'Web Search Context' to fill in gaps where the pitch deck is missing information and to provide the latest market data.
3.  **Synthesize, Don't Copy**: Do NOT just copy-paste from the context. Synthesize the information into a professional analysis.
4.  **Quantitative Analysis**: For `value_usd_billions`, provide ONLY a numeric value (e.g., 150.5). For `description`, provide the original string (e.g., "$150.5B").
5.  **Realistic Estimates**: If you must estimate, ensure TAM > SAM > SOM. State that you are estimating in the `source_commentary`. A common heuristic is SAM as 10-30% of TAM, and SOM as 1-10% of SAM.
6.  **No Hallucination**: If a value cannot be found or reasonably estimated from the provided context, use `null` for numeric fields and `unknown` for string fields.
7.  **Professional Tone**: The `market_summary` must be well-written and suitable for a formal investment memo.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Company & sector info:\n{context}\nWeb search context:\n{web_context}\n")
])


def run_market_sizing_chain(profile: StartupProfile, evaluator: Optional[object] = None) -> StartupProfile:
    """
    Runs the market sizing chain with a focus on high-quality, structured data extraction.
    1. Extracts market context from the pitch deck.
    2. Performs a web search to gather the latest market data.
    3. Uses a powerful LLM prompt to synthesize both sources into a structured JSON.
    4. Populates the StartupProfile with the clean, validated data.
    """
    print("[Market Chain] Starting market sizing analysis...")

    # Step 1: Get smart context from the pitch deck
    deck_context = ""
    if hasattr(profile, 'deck_text') and profile.deck_text:
        deck_context = get_smart_market_context(profile.deck_text)
        print(f"[Market Chain] Extracted {len(deck_context)} chars of market context from the deck.")

    # Step 2: Always perform a web search for the latest market data
    print("[Market Chain] Performing web search for market context...")
    web_context = web_search_market_context(profile.name, profile.sector)
    if web_context:
        print(f"[Market Chain] Web search found {len(web_context)} chars of additional context.")
    else:
        print("[Market Chain] Web search did not return any context.")

    # Step 3: Invoke the LLM with the new, robust prompt
    try:
        prompt = PROMPT.format(context=deck_context, web_context=web_context)
        response = llm.invoke(prompt)
        log_usage_from_message(evaluator, "MARKET SIZING AGENT", response, model="gpt-4o")
        raw_json = response.content.strip()

        # Step 4: Parse the JSON and populate the profile
        json_match = re.search(r'\{.*\}', raw_json, re.DOTALL)
        if not json_match:
            print("[Market Chain] Error: No JSON object found in the LLM response.")
            return profile

        data = json.loads(json_match.group())
        print("[Market Chain] Successfully parsed JSON from LLM.")

        # Populate profile with high-quality, structured data
        if data.get("market_summary"):
            profile.market_summary = data["market_summary"]

        if "market_size_analysis" in data and data["market_size_analysis"]:
            size_analysis = data["market_size_analysis"]
            if "TAM" in size_analysis and size_analysis["TAM"]:
                profile.TAM = size_analysis["TAM"].get("value_usd_billions")
                profile.TAM_original = size_analysis["TAM"].get("description")
            if "SAM" in size_analysis and size_analysis["SAM"]:
                profile.SAM = size_analysis["SAM"].get("value_usd_billions")
                profile.SAM_original = size_analysis["SAM"].get("description")
            if "SOM" in size_analysis and size_analysis["SOM"]:
                profile.SOM = size_analysis["SOM"].get("value_usd_billions")
                profile.SOM_original = size_analysis["SOM"].get("description")

        if "growth_metrics" in data and data["growth_metrics"]:
            growth = data["growth_metrics"]
            profile.cagr = growth.get("CAGR_percent")
            profile.market_growth_rate = growth.get("growth_rate_percent")

        if data.get("key_drivers"):
            profile.market_drivers = data["key_drivers"]

        if data.get("source_commentary"):
            profile.market_reasoning = data["source_commentary"]

        print("[Market Chain] Successfully updated StartupProfile with new market data.")

    except json.JSONDecodeError as e:
        print(f"[Market Chain] JSON parsing error: {e}")
        print(f"LLM Raw Output:\n{raw_json}")
    except Exception as e:
        print(f"[Market Chain] An unexpected error occurred: {e}")

    return profile

def generate_market_size_section(profile: StartupProfile, evaluator: Optional[object] = None) -> str:
    """Generate the market size section with improved structure and formatting."""
    # Import formatting function from chain
    from chains.market_sizing_chain import format_market_size
    
    # Get market size values, preferring original strings if available
    TAM = getattr(profile, 'TAM_original', None) or getattr(profile, 'TAM', 0)
    TAM_source = getattr(profile, 'TAM_source', None)
    SAM = getattr(profile, 'SAM_original', None) or getattr(profile, 'SAM', 0)
    SAM_source = getattr(profile, 'SAM_source', None)
    SOM = getattr(profile, 'SOM_original', None) or getattr(profile, 'SOM', 0)
    SOM_source = getattr(profile, 'SOM_source', None)
    CAGR = getattr(profile, 'cagr', None)
    CAGR_source = getattr(profile, 'cagr_source', None)
    growth_rate = getattr(profile, 'market_growth_rate', None)
    growth_rate_source = getattr(profile, 'market_growth_rate_source', None)
    sector = getattr(profile, 'sector', None)
    
    # NEW: Extract additional market data fields
    total_merchants = getattr(profile, 'total_merchants', None)
    global_merchants = getattr(profile, 'global_merchants', None)
    core_geography_merchants = getattr(profile, 'core_geography_merchants', None)
    revenue_per_merchant = getattr(profile, 'revenue_per_merchant', None)
    market_definition = getattr(profile, 'market_definition', None)
    geographic_focus = getattr(profile, 'geographic_focus', None)
    market_source = getattr(profile, 'market_source', None)
    
    # NEW: AI-extracted market data fields
    ai_market_metrics = {}
    ai_geographic_data = {}
    ai_growth_metrics = {}
    ai_competitive_data = {}
    ai_source_attribution = {}
    
    # Collect all AI-extracted fields
    for field_name in dir(profile):
        if not field_name.startswith('_') and not callable(getattr(profile, field_name)):
            value = getattr(profile, field_name)
            if value and field_name.startswith('market_metrics_'):
                ai_market_metrics[field_name.replace('market_metrics_', '')] = value
            elif value and field_name.startswith('geographic_data_'):
                ai_geographic_data[field_name.replace('geographic_data_', '')] = value
            elif value and field_name.startswith('growth_metrics_'):
                ai_growth_metrics[field_name.replace('growth_metrics_', '')] = value
            elif value and field_name.startswith('competitive_data_'):
                ai_competitive_data[field_name.replace('competitive_data_', '')] = value
            elif value and field_name.startswith('source_attribution_'):
                ai_source_attribution[field_name.replace('source_attribution_', '')] = value
    
    # Extract BEV data from deck text if available
    bev_data = {}
    if hasattr(profile, 'extracted_data_context') and profile.extracted_data_context:
        bev_data = extract_bev_data_from_text(profile.extracted_data_context)
    
    # Data validation: Ensure SAM is not larger than TAM
    if SAM and TAM and isinstance(SAM, (int, float)) and isinstance(TAM, (int, float)):
        if SAM > TAM:
            print(f"[Market Size Validation] SAM ({SAM}) is larger than TAM ({TAM}). Correcting SAM to TAM * 0.3")
            SAM = TAM * 0.3
            SAM_source = "calculated_from_tam"
    
    # Data validation: Ensure SOM is not larger than SAM
    if SOM and SAM and isinstance(SOM, (int, float)) and isinstance(SAM, (int, float)):
        if SOM > SAM:
            print(f"[Market Size Validation] SOM ({SOM}) is larger than SAM ({SAM}). Correcting SOM to SAM * 0.1")
            SOM = SAM * 0.1
            SOM_source = "calculated_from_sam"
    
    # NEW: Calculate market penetration if we have merchant data
    market_penetration = None
    if total_merchants and global_merchants:
        try:
            penetration_rate = (total_merchants / global_merchants) * 100
            market_penetration = f"{penetration_rate:.2f}%"
            print(f"[Market Analysis] Calculated penetration: {market_penetration}")
        except:
            pass
    
    def clean_perplexity_response(response: str, sector: str) -> str:
        """
        Cleans and refines a raw Perplexity response using a multi-step, AI-driven process.
        """
        if not response:
            return ""

        # --- Step 1: Use an LLM for intelligent, context-aware cleaning ---
        # This is more robust than simple regex because it understands the content.
        print(f"[Market Analysis Cleaning] Attempting LLM-based cleaning for '{sector}' sector analysis.")
        
        # A specific prompt designed to clean and professionalize the text
        llm_cleaning_prompt = f"""
        You are a senior VC analyst. Your task is to take the raw, messy text below from a market research search and transform it into a clean, professional, and coherent paragraph for an investment memo.

        Rules:
        1.  Remove ALL conversational filler, meta-commentary, and "thinking process" text (e.g., "Based on the search...", "Here is a summary...", "Let me analyze...").
        2.  Strip out all artifacts, junk characters, citations (e.g., [1], B253500), and incomplete sentences.
        3.  Rewrite the text into a single, well-structured, and insightful paragraph.
        4.  Ensure the final text flows logically and is suitable for a professional audience.
        5.  Do NOT include any of your own analysis; only use the information present in the raw text.

        Raw Text for the '{sector}' sector:
        ---
        {response}
        ---

        Return ONLY the clean, professional paragraph.
        """
        
        try:
            llm_cleaned_text = llm.invoke(llm_cleaning_prompt).content.strip()
            
            # --- Validation of LLM Output ---
            # Check if the output is substantial and doesn't contain common failure phrases.
            if llm_cleaned_text and len(llm_cleaned_text.split()) > 20 and "cannot provide" not in llm_cleaned_text.lower() and "don't have enough" not in llm_cleaned_text.lower():
                print("[Market Analysis Cleaning] LLM-based cleaning successful.")
                return llm_cleaned_text
            else:
                print("[Market Analysis Cleaning] LLM-based cleaning produced a short or invalid response. Falling back to regex.")
        except Exception as e:
            print(f"[Market Analysis Cleaning] LLM-based cleaning failed: {e}. Falling back to regex.")

        # --- Step 2: Fallback to aggressive regex cleaning if LLM fails ---
        # This is a safety net for cases where the LLM might fail or produce poor results.
        print("[Market Analysis Cleaning] Executing aggressive regex fallback.")
        
        # A more comprehensive list of patterns to remove
        junk_patterns = [
            r'<think>.*?</think>',
            r'Okay, let me break this down.*',
            r'Here is a summary of.*',
            r'Based on the search results.*',
            r'I will now generate a summary.*',
            r'Let me start by.*',
            r'Here\'s a professional summary.*',
            r'\[\d+\]',  # Citations like [1]
            r'B\d{5,}', # Artifacts like B253500
            r'\([^)]*source[^)]*\)', # (source: ...)
            r'•', # Bullet points
            r'^\s*,\s*|^,', # Leading commas
            r'\n\s*\n', # Extra newlines
        ]

        cleaned = response
        for pattern in junk_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)

        # --- Step 3: Reconstruct the paragraph from clean sentences ---
        # This helps to ensure a coherent final output.
        sentences = [s.strip() for s in cleaned.split('.') if len(s.strip()) > 20]
        final_text = ". ".join(sentences)
        if sentences:
            final_text += "."

        # --- Step 4: Final validation check ---
        # Ensure the fallback result is still of reasonable quality.
        if len(final_text.split()) > 15:
            print("[Market Analysis Cleaning] Regex fallback cleaning successful.")
            return final_text.strip()
        else:
            print("[Market Analysis Cleaning] All cleaning methods failed to produce a quality result.")
            return "" # Return empty if all else fails
    
    # --- Perplexity search for market research URLs ---
    market_research_urls = []
    if sector:
        print(f"[Market Agent] Searching for market research URLs for sector: {sector}")
        try:
            # Use Perplexity to find relevant market research reports with explicit URL requests
            search_queries = [
                f"Find 2 specific market research report URLs for {sector} market size 2024 2025. Return only the URLs in markdown format: [Report Name](URL)",
                f"Find 2 industry analysis report URLs for {sector} TAM SAM market research. Return only the URLs in markdown format: [Report Name](URL)"
            ]
            
            # Check if Perplexity API is available
            from core.perplexity_utils import search_perplexity
            test_result = search_perplexity("test", num_results=1)
            if test_result is None:
                print("[Market Agent] Perplexity API not available, skipping web searches")
                # Add fallback URLs for generic market research sources
                market_research_urls = [
                    "https://www.grandviewresearch.com/",
                    "https://www.marketsandmarkets.com/",
                    "https://www.alliedmarketresearch.com/",
                    "https://www.researchandmarkets.com/",
                    "https://www.ibisworld.com/",
                    "https://www.statista.com/"
                ]
            
            for query in search_queries:
                try:
                    # Use Perplexity search to get market research URLs
                    search_results = search_perplexity(query, num_results=3)
                    
                    if search_results:
                        print(f"[Market Agent] Found search results, extracting URLs...")
                        # Extract URLs BEFORE cleaning the response
                        
                        # Look for markdown links first: [text](url) - BEFORE cleaning
                        markdown_links = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', search_results)
                        print(f"[Market Agent] Found {len(markdown_links)} markdown links")
                        for text, url in markdown_links:
                            print(f"[Market Agent] Adding URL: {url}")
                            market_research_urls.append(url)
                            if len(market_research_urls) >= 2:
                                break
                        
                        # If not enough markdown links, look for plain URLs - BEFORE cleaning
                        if len(market_research_urls) < 2:
                            print(f"[Market Agent] Looking for plain URLs...")
                            # More comprehensive URL regex
                            urls = re.findall(r'https?://[^\s\)\]<>"]+', search_results)
                            print(f"[Market Agent] Found {len(urls)} plain URLs")
                            # Filter for market research domains
                            market_domains = ['statista', 'grandviewresearch', 'marketsandmarkets', 'mckinsey', 'bain', 'bcg', 'deloitte', 'pwc', 'kpmg', 'ey', 'forrester', 'gartner', 'idc', 'frost', 'technavio', 'ibisworld', 'marketresearch', 'researchandmarkets', 'alliedmarketresearch', 'persistencemarketresearch', 'factmr', 'coherentmarketinsights', 'transparencymarketresearch', 'emergenresearch', 'precedenceresearch', 'verifiedmarketresearch', 'marketdataforecast', 'marketresearchfuture', '360marketupdates', 'marketwatch', 'bloomberg', 'reuters', 'cnbc', 'wsj', 'ft', 'forbes', 'techcrunch', 'venturebeat']
                            
                            for url in urls:
                                if any(domain in url.lower() for domain in market_domains):
                                    if url not in market_research_urls:  # Avoid duplicates
                                        print(f"[Market Agent] Adding filtered URL: {url}")
                                        market_research_urls.append(url)
                                        if len(market_research_urls) >= 2:
                                            break
                    
                    if len(market_research_urls) >= 2:
                        break
                        
                except Exception as e:
                    print(f"[Market Research] Error searching for {query}: {e}")
                    continue
                    
        except Exception as e:
            print(f"[Market Research] Error during Perplexity search: {e}")
    
    print(f"[Market Agent] Final market research URLs found: {len(market_research_urls)}")
    for i, url in enumerate(market_research_urls, 1):
        print(f"[Market Agent] URL {i}: {url}")
    
    # --- Perplexity for market analysis content with source extraction ---
    sector_analysis = ""
    sector_sources = []
    if sector:
        try:
            search_query = f"Latest market analysis and trends for the {sector} sector in 2024-2025. Focus on market size, growth drivers, and key trends. Include specific URLs to market research reports in markdown format: [Source Name](URL)."
            search_results = search_perplexity(search_query, num_results=2)
            
            if search_results:
                # Extract URLs BEFORE cleaning the response
                
                # Look for markdown links first: [text](url) - BEFORE cleaning
                markdown_links = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', search_results)
                for text, url in markdown_links:
                    # Ensure we have a complete URL
                    if url.startswith('http') and len(url) > 10:
                        sector_sources.append(url)
                    if len(sector_sources) >= 2:
                        break
                
                # If not enough markdown links, look for plain URLs - BEFORE cleaning
                if len(sector_sources) < 2:
                    urls = re.findall(r'https?://[^\s\)\]<>"]+', search_results)
                    for url in urls:
                        # Ensure we have a complete URL with domain and path
                        if len(url) > 15 and '.' in url.split('/')[2]:
                            sector_sources.append(url)
                        if len(sector_sources) >= 2:
                            break
                
                # Clean the response for LLM processing
                cleaned_results = clean_perplexity_response(search_results, sector)
                
                # The cleaned_results should now be a professional paragraph
                sector_analysis = cleaned_results
                
        except Exception as e:
            print(f"[Market Analysis] Error during sector analysis: {e}")
    
    web_sources = getattr(profile, 'market_size_sources', []) or []
    web_links = [url for url in web_sources if url.startswith('http') and len(url) > 15][:2]  # Limit to 2 sources (reduced from 3)
    
    # Generate market discussion
    prompt = f"""
You are a VC analyst writing the Market Size & Analysis section for an investment memo.
Write a concise, professional market analysis (4-6 sentences) that covers:
- Current market size and growth trajectory
- Key market drivers and trends
- Competitive landscape considerations
- Opportunities and challenges for the company

Use the following data and be specific about numbers and sources. Present the market data as provided without assuming units.

IMPORTANT: Validate that SAM is not larger than TAM. If SAM > TAM, use SAM = TAM * 0.3 as a reasonable estimate.

Data:
TAM: {TAM}
SAM: {SAM}
SOM: {SOM}
CAGR: {CAGR}%
Growth Rate: {growth_rate}
Sector: {sector}

Additional Market Data:
Total Merchants: {total_merchants}
Global Merchants: {global_merchants}
Core Geography Merchants: {core_geography_merchants}
Revenue per Merchant: {revenue_per_merchant}
Market Penetration: {market_penetration}
Market Definition: {market_definition}
Geographic Focus: {geographic_focus}
Market Source: {market_source}

AI-Detected Market Metrics: {ai_market_metrics}
AI-Detected Geographic Data: {ai_geographic_data}
AI-Detected Growth Metrics: {ai_growth_metrics}
AI-Detected Competitive Data: {ai_competitive_data}
AI-Detected Source Attribution: {ai_source_attribution}
"""
    resp_disc = llm.invoke(prompt)
    log_usage_from_message(evaluator, "MARKET SIZING AGENT", resp_disc, model="gpt-4o")
    market_discussion = resp_disc.content.strip()
    
    def format_source(source):
        if not source:
            return ""
        
        source_map = {
            "deck_text": "Pitch Deck",
            "deck_ocr/table": "Pitch Deck (Visuals)",
            "web_search": "Market Research"
        }
        
        # If source is a URL, use it directly
        if isinstance(source, str) and source.startswith('http'):
            domain = source.split('/')[2] if len(source.split('/')) > 2 else source
            return f" [Source: {domain}]({source})"
        
        display_source = source_map.get(source, source)
        return f" [Source: {display_source}]" if display_source else ""

    # Build structured output
    lines = []
    
    # 1. Market Discussion
    lines.append(market_discussion)
    lines.append("")
    
    # 2. Market Size Metrics (Structured Table)
    lines.append("**📊 Market Size Metrics**")
    lines.append("")
    
    # Create a structured metrics table
    metrics_data = []
    if TAM:
        metrics_data.append(("Total Addressable Market (TAM)", TAM, TAM_source))
    if SAM:
        metrics_data.append(("Serviceable Available Market (SAM)", SAM, SAM_source))
    if SOM:
        metrics_data.append(("Serviceable Obtainable Market (SOM)", SOM, SOM_source))
    
    # Dynamically add any additional market size fields from deck extraction
    # Check for any fields that might contain market data
    for field_name in dir(profile):
        if not field_name.startswith('_') and not callable(getattr(profile, field_name)):
            value = getattr(profile, field_name)
            source = getattr(profile, f"{field_name}_source", None)
            
            # Skip if already handled or if value is None/empty
            if (field_name in ['TAM', 'SAM', 'SOM', 'cagr', 'market_growth_rate'] or 
                not value or value == 0 or 
                field_name.endswith('_source') or 
                field_name.endswith('_original')):
                continue
                
            # Check if this looks like market data (contains numbers and common market terms)
            # Exclude non-market fields
            exclude_fields = [
                'linkedin_followers', 'followers', 'employees_count', 'patent_count',
                'funding_amount', 'revenue', 'implied_valuation', 'cash_burn_12m',
                'runway_months', 'arr', 'mrr', 'cac', 'ltv', 'payback_period',
                'revenue_growth_rate', 'debt', 'cash_on_hand', 'cycle_life_count',
                'energy_density_wh_kg', 'startup_id', 'founded_year', 'founded'
            ]
            
            if (isinstance(value, (int, float)) and value > 1000 and 
                field_name not in exclude_fields and
                any(keyword in field_name.lower() for keyword in ['market', 'tam', 'sam', 'som', 'addressable', 'bev', 'demand', 'size'])):
                
                # Try to create a readable label
                label = field_name.replace('_', ' ').title()
                if 'addressable' in field_name.lower():
                    label = "Addressable Market"
                elif 'bev' in field_name.lower() or 'battery' in field_name.lower():
                    label = "Market Size"
                elif 'demand' in field_name.lower():
                    label = "Market Demand"
                
                metrics_data.append((label, value, source))
    
    if metrics_data:
        for metric, value, source in metrics_data:
            # Format the value using the improved formatting function
            formatted_value = format_market_size(value)
            source_str = format_source(source)
            lines.append(f"• **{metric}**: {formatted_value}{source_str}")
        lines.append("")
    
    # 3. Growth Metrics
    growth_metrics = []
    if CAGR:
        growth_metrics.append(f"**CAGR**: {format_growth_rate(CAGR)}{format_source(CAGR_source)}")
    if growth_rate:
        growth_metrics.append(f"**Growth Rate**: {format_growth_rate(growth_rate)}{format_source(growth_rate_source)}")
    
    if growth_metrics:
        lines.append("**📈 Growth Metrics**")
        lines.append(" • ".join(growth_metrics))
        lines.append("")
    
    # NEW: Enhanced Market Data Section
    enhanced_market_data = []
    
    # Market Penetration Analysis
    if market_penetration:
        enhanced_market_data.append(f"**Market Penetration**: {market_penetration}")
    
    # Merchant Data
    if total_merchants:
        enhanced_market_data.append(f"**Active Merchants**: {format_market_size(total_merchants)}")
    
    if global_merchants:
        enhanced_market_data.append(f"**Global Addressable Merchants**: {format_market_size(global_merchants)}")
    
    if core_geography_merchants:
        enhanced_market_data.append(f"**Core Geography Merchants**: {format_market_size(core_geography_merchants)}")
    
    # Revenue per Merchant
    if revenue_per_merchant:
        enhanced_market_data.append(f"**Revenue per Merchant**: {format_market_size(revenue_per_merchant)}")
    
    # Market Definition
    if market_definition:
        enhanced_market_data.append(f"**Market Definition**: {market_definition}")
    
    # Geographic Focus
    if geographic_focus:
        enhanced_market_data.append(f"**Geographic Focus**: {geographic_focus}")
    
    # Market Source Attribution
    if market_source:
        enhanced_market_data.append(f"**Market Data Source**: {market_source}")
    
    if enhanced_market_data:
        lines.append("**🎯 Enhanced Market Analysis**")
        lines.append("")
        for data_point in enhanced_market_data:
            lines.append(f"• {data_point}")
        lines.append("")
    
    # NEW: AI-Detected Market Data Section
    ai_sections = []
    
    # AI Market Metrics
    if ai_market_metrics:
        ai_sections.append("**📊 AI-Detected Market Metrics**")
        for key, value in ai_market_metrics.items():
            ai_sections.append(f"• **{key.replace('_', ' ').title()}**: {value}")
        ai_sections.append("")
    
    # AI Geographic Data
    if ai_geographic_data:
        ai_sections.append("**🌍 AI-Detected Geographic Data**")
        for key, value in ai_geographic_data.items():
            ai_sections.append(f"• **{key.replace('_', ' ').title()}**: {value}")
        ai_sections.append("")
    
    # AI Growth Metrics
    if ai_growth_metrics:
        ai_sections.append("**📈 AI-Detected Growth Metrics**")
        for key, value in ai_growth_metrics.items():
            ai_sections.append(f"• **{key.replace('_', ' ').title()}**: {value}")
        ai_sections.append("")
    
    # AI Competitive Data
    if ai_competitive_data:
        ai_sections.append("**🏆 AI-Detected Competitive Data**")
        for key, value in ai_competitive_data.items():
            ai_sections.append(f"• **{key.replace('_', ' ').title()}**: {value}")
        ai_sections.append("")
    
    # AI Source Attribution
    if ai_source_attribution:
        ai_sections.append("**📚 AI-Detected Source Attribution**")
        for key, value in ai_source_attribution.items():
            ai_sections.append(f"• **{key.replace('_', ' ').title()}**: {value}")
        ai_sections.append("")
    
    if ai_sections:
        lines.append("**🤖 AI-Enhanced Market Intelligence**")
        lines.append("")
        lines.extend(ai_sections)
    
    # 4. Sector Analysis with source links
    if sector_analysis:
        lines.append("**📰 Sector Analysis**")
        lines.append("")
        lines.append(sector_analysis)
        
        # Add BEV data if available
        if bev_data and (bev_data.get('overall_adoption') or bev_data.get('us_adoption') or bev_data.get('market_size')):
            lines.append("")
            lines.append("**🚗 BEV Market Data (from Deck)**")
            if bev_data.get('overall_adoption'):
                lines.append(f"• **Overall BEV Adoption**: {bev_data['overall_adoption']} by {bev_data.get('target_year', '2030')}")
            if bev_data.get('us_adoption'):
                lines.append(f"• **Regional Adoption**: US ({bev_data['us_adoption']}), EU ({bev_data['eu_adoption']}), China ({bev_data['china_adoption']})")
            if bev_data.get('market_size'):
                lines.append(f"• **Market Size**: {bev_data['market_size']}")
            lines.append("• **Source**: Company Pitch Deck")
        
        if sector_sources:
            lines.append("")
            lines.append("**Sources:**")
            for url in sector_sources:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain = parsed.netloc
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    
                    # Create readable source names
                    if 'precedenceresearch' in domain.lower():
                        source_name = "Precedence Research"
                    elif 'oganalysis' in domain.lower():
                        source_name = "OG Analysis"
                    elif 'grandviewresearch' in domain.lower():
                        source_name = "Grand View Research"
                    elif 'marketsandmarkets' in domain.lower():
                        source_name = "MarketsandMarkets"
                    elif 'statista' in domain.lower():
                        source_name = "Statista"
                    elif 'ibisworld' in domain.lower():
                        source_name = "IBISWorld"
                    else:
                        source_name = domain.replace('.com', '').replace('.co', '').title()
                    
                    lines.append(f"• [{source_name}]({url})")
                except:
                    # Fallback to domain extraction
                    domain = url.split('/')[2] if len(url.split('/')) > 2 else url
                    lines.append(f"• [{domain}]({url})")
        lines.append("")
    
    # 4b. BEV Data (if no sector analysis but BEV data available)
    if not sector_analysis and bev_data and (bev_data.get('overall_adoption') or bev_data.get('us_adoption') or bev_data.get('market_size')):
        lines.append("**🚗 BEV Market Data (from Deck)**")
        lines.append("")
        if bev_data.get('overall_adoption'):
            lines.append(f"• **Overall BEV Adoption**: {bev_data['overall_adoption']} by {bev_data.get('target_year', '2030')}")
        if bev_data.get('us_adoption'):
            lines.append(f"• **Regional Adoption**: US ({bev_data['us_adoption']}), EU ({bev_data['eu_adoption']}), China ({bev_data['china_adoption']})")
        if bev_data.get('market_size'):
            lines.append(f"• **Market Size**: {bev_data['market_size']}")
        lines.append("• **Source**: Company Pitch Deck")
        lines.append("")
    
    # 5. Market Research Sources (Perplexity search results)
    if market_research_urls:
        lines.append("**🔍 Market Research Sources**")
        lines.append("")
        for url in market_research_urls:
            try:
                # Clean the URL - only remove trailing periods that are not part of the URL structure
                clean_url = url
                # Only remove trailing period if it's not part of a domain extension
                if clean_url.endswith('.') and not clean_url.endswith('.com') and not clean_url.endswith('.org') and not clean_url.endswith('.net') and not clean_url.endswith('.co') and not clean_url.endswith('.io'):
                    clean_url = clean_url[:-1]
                if len(clean_url) > 200:
                    clean_url = clean_url[:200]
                    print(f"[Market Agent] Truncated long URL: {url[:50]}...")
                
                # Ensure we have a complete URL
                if clean_url.startswith('http') and len(clean_url) > 10:
                    # Fix URLs with missing hyphens - generic approach
                    if 'market.us' in clean_url and 'global' in clean_url and 'market' in clean_url:
                        # Generic fix for market.us URLs - add hyphens between words
                        clean_url = re.sub(r'([a-z])([A-Z])', r'\1-\2', clean_url)
                        clean_url = clean_url.replace('--', '-')  # Fix double hyphens
                    
                    elif 'alliedmarketresearch' in clean_url and 'market' in clean_url:
                        # Generic fix for alliedmarketresearch URLs - add hyphens between words
                        clean_url = re.sub(r'([a-z])([A-Z])', r'\1-\2', clean_url)
                        clean_url = clean_url.replace('--', '-')  # Fix double hyphens
                    
                    # Format as markdown link for proper DOCX hyperlink processing
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(clean_url)
                        domain = parsed.netloc
                        if domain.startswith('www.'):
                            domain = domain[4:]
                        
                        # Create readable source names
                        if 'precedenceresearch' in domain.lower():
                            source_name = "Precedence Research"
                        elif 'oganalysis' in domain.lower():
                            source_name = "OG Analysis"
                        elif 'grandviewresearch' in domain.lower():
                            source_name = "Grand View Research"
                        elif 'marketsandmarkets' in domain.lower():
                            source_name = "MarketsandMarkets"
                        elif 'statista' in domain.lower():
                            source_name = "Statista"
                        elif 'ibisworld' in domain.lower():
                            source_name = "IBISWorld"
                        else:
                            source_name = domain.replace('.com', '').replace('.co', '').title()
                        
                        lines.append(f"• [{clean_url}]({clean_url})")
                    except:
                        # Fallback to domain extraction
                        domain = clean_url.split('/')[2] if len(clean_url.split('/')) > 2 else clean_url
                        lines.append(f"• [{clean_url}]({clean_url})")
                else:
                    print(f"[Market Agent] Invalid URL found: {url}")
            except Exception as e:
                print(f"[Market Agent] Error processing URL {url}: {e}")
        lines.append("")
    
    # 6. Additional Web Sources (if any from profile)
    if web_links:
        lines.append("**🔗 Additional Sources**")
        for url in web_links:
            try:
                # Clean the URL - only remove trailing periods that are not part of the URL structure
                clean_url = url
                # Only remove trailing period if it's not part of a domain extension
                if clean_url.endswith('.') and not clean_url.endswith('.com') and not clean_url.endswith('.org') and not clean_url.endswith('.net') and not clean_url.endswith('.co') and not clean_url.endswith('.io'):
                    clean_url = clean_url[:-1]
                if len(clean_url) > 200:
                    clean_url = clean_url[:200]
                    print(f"[Market Agent] Truncated long URL: {url[:50]}...")
                
                # Ensure we have a complete URL
                if clean_url.startswith('http') and len(clean_url) > 10:
                    # Fix URLs with missing hyphens - generic approach
                    if 'market.us' in clean_url and 'global' in clean_url and 'market' in clean_url:
                        # Generic fix for market.us URLs - add hyphens between words
                        clean_url = re.sub(r'([a-z])([A-Z])', r'\1-\2', clean_url)
                        clean_url = clean_url.replace('--', '-')  # Fix double hyphens
                    
                    elif 'alliedmarketresearch' in clean_url and 'market' in clean_url:
                        # Generic fix for alliedmarketresearch URLs - add hyphens between words
                        clean_url = re.sub(r'([a-z])([A-Z])', r'\1-\2', clean_url)
                        clean_url = clean_url.replace('--', '-')  # Fix double hyphens
                    
                    # Format as markdown link for proper DOCX hyperlink processing
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(clean_url)
                        domain = parsed.netloc
                        if domain.startswith('www.'):
                            domain = domain[4:]
                        
                        # Create readable source names
                        if 'precedenceresearch' in domain.lower():
                            source_name = "Precedence Research"
                        elif 'oganalysis' in domain.lower():
                            source_name = "OG Analysis"
                        elif 'grandviewresearch' in domain.lower():
                            source_name = "Grand View Research"
                        elif 'marketsandmarkets' in domain.lower():
                            source_name = "MarketsandMarkets"
                        elif 'statista' in domain.lower():
                            source_name = "Statista"
                        elif 'ibisworld' in domain.lower():
                            source_name = "IBISWorld"
                        else:
                            source_name = domain.replace('.com', '').replace('.co', '').title()
                        
                        lines.append(f"• [{clean_url}]({clean_url})")
                    except:
                        # Fallback to domain extraction
                        domain = clean_url.split('/')[2] if len(clean_url.split('/')) > 2 else clean_url
                        lines.append(f"• [{clean_url}]({clean_url})")
                else:
                    print(f"[Market Agent] Invalid URL found: {url}")
            except Exception as e:
                print(f"[Market Agent] Error processing additional URL {url}: {e}")
        lines.append("")
    
    return '\n'.join(lines)


def run_market_sizing_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    context = full_text[:5000]
    web_context = web_search_market_context(profile.name, profile.sector)
    txt = llm.invoke(PROMPT.format(context=context, web_context=web_context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        
        # Validate and set TAM
        if data.get("TAM") is not None and data.get("TAM", 0) > 0:
            tam_value = float(data.get("TAM"))
            # Validate TAM is reasonable (should be in billions for major sectors)
            if tam_value < 1:  # If less than 1 billion, likely an error
                print(f"[Market Sizing] Warning: TAM value {tam_value} seems too small, skipping")
            else:
                profile.TAM = tam_value
        
        # Validate and set SAM
        if data.get("SAM") is not None and data.get("SAM", 0) > 0:
            sam_value = float(data.get("SAM"))
            # Validate SAM is reasonable (should be smaller than TAM)
            if profile.TAM and sam_value >= profile.TAM:
                print(f"[Market Sizing] Warning: SAM value {sam_value} is >= TAM {profile.TAM}, skipping")
            elif sam_value < 0.1:  # If less than 100M, likely an error
                print(f"[Market Sizing] Warning: SAM value {sam_value} seems too small, skipping")
            else:
                profile.SAM = sam_value
        
        # Validate and set SOM
        if data.get("SOM") is not None and data.get("SOM", 0) > 0:
            som_value = float(data.get("SOM"))
            # Validate SOM is reasonable (should be smaller than SAM)
            if profile.SAM and som_value >= profile.SAM:
                print(f"[Market Sizing] Warning: SOM value {som_value} is >= SAM {profile.SAM}, skipping")
            elif som_value < 0.01:  # If less than 10M, likely an error
                print(f"[Market Sizing] Warning: SOM value {som_value} seems too small, skipping")
            else:
                profile.SOM = som_value
        
        if data.get("summary"):
            profile.market_summary = data.get("summary")
        # Store original strings and reasoning if present
        if data.get("TAM_original"):
            profile.TAM_original = data["TAM_original"]
        if data.get("SAM_original"):
            profile.SAM_original = data["SAM_original"]
        if data.get("SOM_original"):
            profile.SOM_original = data["SOM_original"]
        if data.get("reasoning"):
            profile.market_reasoning = data["reasoning"]
    except Exception as e:
        print(f"[Market Sizing Parsing Error] {e}")
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile




def extract_bev_data_from_text(text):
    """Extract BEV (Battery Electric Vehicle) data from deck text."""
    if not text:
        return {}
    
    import re
    
    bev_data = {}
    
    # Extract regional BEV adoption rates
    regional_matches = re.findall(r'US \(([^)]+)\), EU \(([^)]+)\) and China \(([^)]+)\)', text)
    if regional_matches:
        bev_data['us_adoption'] = regional_matches[0][0]
        bev_data['eu_adoption'] = regional_matches[0][1]
        bev_data['china_adoption'] = regional_matches[0][2]
    
    # Extract overall adoption percentage
    adoption_matches = re.findall(r'>(\d+\.?\d*)%', text)
    if adoption_matches:
        bev_data['overall_adoption'] = adoption_matches[0] + '%'
    
    # Extract market size data
    market_matches = re.findall(r'(\d+\.?\d*M|\d+\.?\d*B).*cars', text)
    if market_matches:
        bev_data['market_size'] = market_matches[0]
    
    # Extract year references (prioritize recent years)
    year_matches = re.findall(r'(\d{4})', text)
    if year_matches:
        # Filter for reasonable years (2000-2030)
        valid_years = [int(y) for y in year_matches if 2000 <= int(y) <= 2030]
        if valid_years:
            bev_data['target_year'] = str(max(valid_years))  # Use the most recent year
        else:
            bev_data['target_year'] = '2023'  # Default to 2023 if no valid years found
    
    return bev_data

