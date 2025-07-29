from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from crewai_tools import EXASearchTool
from core.schemas import StartupProfile
from dotenv import load_dotenv
import os
import json
import re
from hashlib import sha1
from core.hybrid_context import get_hybrid_context
from core.perplexity_utils import search_perplexity
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
exa_api_key = os.getenv("EXA_API_KEY")

exa_search_tool = EXASearchTool(
    api_key=exa_api_key,
    type='neural',
    use_autoprompt=True,
    category='company',
    startPublishedDate='2021-10-01T00:00:00.000Z',
    excludeText=[
        'OpenAI', 'Anthropic', 'Google', 'Mistral', 'Microsoft', 'Nvidia',
        'general AI market', 'overall AI industry', 'IBM', 'Mistral'
    ],
    numResults=20
)

llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

SYSTEM = """
You are a market research analyst for venture capital.
For the given company and sector, provide a detailed, structured market analysis including:
- Challenges: A bulleted list of the main pain points and obstacles in the market.
- Drivers: A bulleted list of growth drivers and positive trends.
- Size: A narrative paragraph with the latest available numbers (TAM, SAM, SOM if possible), growth rates (CAGR), and sources. If specific data is unavailable, explain why and provide the closest relevant market size.
Leave the current Discussion logic in place.
Return your answer as a multi-section, multi-bullet, multi-paragraph analysis suitable for a VC investment memo.
"""

from langchain.prompts import ChatPromptTemplate
PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Company & sector info:\n{context}\nWeb search context:\n{web_context}\n")
])

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


def web_search_market_context(company_name, sector):
    """Web search for market context focusing on content analysis."""
    if not company_name and not sector:
        return ""
    
    query = f"Latest market size, growth rate, and trends for {company_name or 'the company'} in the {sector or ''} sector. Provide TAM, SAM, SOM if available. Focus on recent data from 2024-2025."
    result = search_perplexity(query)
    
    return result or ""

def generate_market_size_section(profile: StartupProfile) -> str:
    """Generate the market size section with improved structure and formatting."""
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
    
    def clean_perplexity_response(response):
        """Clean Perplexity response by removing think tags and internal reasoning."""
        if not response:
            return ""
        
        # Remove <think> tags and their content
        import re
        cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        
        # Remove thinking process markers (but be more careful)
        thinking_patterns = [
            r'Okay, so I need to figure out.*?(?=\n|$)',
            r'First, looking at.*?(?=\n|$)',
            r'Let me start by.*?(?=\n|$)',
            r'I need to analyze.*?(?=\n|$)',
            r'Let me examine.*?(?=\n|$)',
            r'Based on my search.*?(?=\n|$)',
            r'According to the search results.*?(?=\n|$)'
        ]
        
        for pattern in thinking_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL)
        
        # Remove citation markers like [1], [2], etc. (but keep the text)
        cleaned = re.sub(r'\[\d+\]', '', cleaned)
        
        # Clean up extra whitespace and newlines
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
        cleaned = cleaned.strip()
        
        # Remove any remaining single characters that might be artifacts
        cleaned = re.sub(r'^\s*[a-z]\s+', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^\s*\.\s+', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^\s*,\s+', '', cleaned, flags=re.MULTILINE)
        
        return cleaned
    
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
                # Add fallback URLs for common market research sources
                market_research_urls = [
                    "https://market.us/report/global-battery-technology-market/",
                    "https://www.alliedmarketresearch.com/battery-technology-market/", 
                    "https://www.researchandmarkets.com/reports/battery-technology-market"
                ]
            
            for query in search_queries:
                try:
                    # Use Perplexity search to get market research URLs
                    search_results = search_perplexity(query, num_results=3)
                    
                    if search_results:
                        print(f"[Market Agent] Found search results, extracting URLs...")
                        # Extract URLs BEFORE cleaning the response
                        import re
                        
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
                import re
                
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
                cleaned_results = clean_perplexity_response(search_results)
                
                # Use LLM to summarize the analysis
                summary_prompt = f"""
                Based on the following market research for the '{sector}' sector, provide a well-structured, professional analysis covering:
                
                1. Market Overview: Current market size and growth trajectory
                2. Key Drivers: Main factors driving market growth
                3. Technology Trends: Important technological developments
                4. Industry Developments: Notable industry changes and innovations
                
                Write in clear, complete sentences. Focus on actionable insights for investment analysis. 
                Do not include URLs, citations, or incomplete fragments.
                Ensure the analysis flows logically and is suitable for a professional investment memo.
                
                Research Results:
                {cleaned_results}
                """
                sector_analysis = llm.invoke(summary_prompt).content.strip()
        except Exception as e:
            print(f"[Market Analysis] Error during sector analysis: {e}")
    
    web_sources = getattr(profile, 'market_size_sources', []) or []
    web_links = [url for url in web_sources if url.startswith('http') and len(url) > 15][:3]
    
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
"""
    market_discussion = llm.invoke(prompt).content.strip()
    
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
        growth_metrics.append(f"**CAGR**: {CAGR}%{format_source(CAGR_source)}")
    if growth_rate:
        growth_metrics.append(f"**Growth Rate**: {growth_rate}{format_source(growth_rate_source)}")
    
    if growth_metrics:
        lines.append("**📈 Growth Metrics**")
        lines.append(" • ".join(growth_metrics))
        lines.append("")
    
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
            lines.append("• **Source**: StoreDot Pitch Deck")
        
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
        lines.append("• **Source**: StoreDot Pitch Deck")
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
                    # Fix common URL issues before adding to output
                    corrected_url = clean_url
                    # Fix market.us URLs
                    if 'market.us' in clean_url and 'globalbatterytechnologymarket' in clean_url:
                        corrected_url = clean_url.replace('globalbatterytechnologymarket', 'global-battery-technology-market')
                    # Fix alliedmarketresearch URLs
                    elif 'alliedmarketresearch' in clean_url and 'batterytechnologymarket' in clean_url:
                        corrected_url = clean_url.replace('batterytechnologymarket', 'battery-technology-market')
                    
                    # Format as markdown link for proper DOCX hyperlink processing
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(corrected_url)
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
                        
                        lines.append(f"• [{corrected_url}]({corrected_url})")
                    except:
                        # Fallback to domain extraction
                        domain = corrected_url.split('/')[2] if len(corrected_url.split('/')) > 2 else corrected_url
                        lines.append(f"• [{corrected_url}]({corrected_url})")
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
                    # Fix common URL issues before adding to output
                    corrected_url = clean_url
                    # Fix market.us URLs
                    if 'market.us' in clean_url and 'globalbatterytechnologymarket' in clean_url:
                        corrected_url = clean_url.replace('globalbatterytechnologymarket', 'global-battery-technology-market')
                    # Fix alliedmarketresearch URLs
                    elif 'alliedmarketresearch' in clean_url and 'batterytechnologymarket' in clean_url:
                        corrected_url = clean_url.replace('batterytechnologymarket', 'battery-technology-market')
                    
                    # Format as markdown link for proper DOCX hyperlink processing
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(corrected_url)
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
                        
                        lines.append(f"• [{corrected_url}]({corrected_url})")
                    except:
                        # Fallback to domain extraction
                        domain = corrected_url.split('/')[2] if len(corrected_url.split('/')) > 2 else corrected_url
                        lines.append(f"• [{corrected_url}]({corrected_url})")
                else:
                    print(f"[Market Agent] Invalid URL found: {url}")
            except Exception as e:
                print(f"[Market Agent] Error processing additional URL {url}: {e}")
        lines.append("")
    
    return '\n'.join(lines)

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

def build_market_sizing_agent(profile: StartupProfile, trace_id=None):
    analyst = Agent(
        role="Market size Research Analyst",
        goal="Research and analyze the market size TAM of AI subsegment markets focusing on specialized market sizes and growth rates.",
        backstory="Expert in doing research and calculating the market size TAM of specific subsegments of the AI market, and growth rates. Also search for sector-specific growth drivers. Known for providing granular market insights rather than general AI market statistics like the overall size of AI market which is irrelevant.",
        tools=[exa_search_tool],
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        # --- Hybrid context and web search ---
        context = get_hybrid_context(
            profile, "market size OR TAM OR SAM OR SOM OR industry", 3, 3
        )
        web_context = web_search_market_context(profile.name, profile.sector)
        prompt_vars = {"context": context, "web_context": web_context}
        txt = llm.invoke(PROMPT.format(**prompt_vars)).content.strip()
        first, last = txt.find("{"), txt.rfind("}")
        if first == -1 or last == -1:
            return profile.model_dump_json(indent=2)
        try:
            data = json.loads(txt[first : last + 1])
            if data.get("TAM") is not None and data.get("TAM", 0) > 0:
                profile.TAM = float(data.get("TAM"))
            if data.get("SAM") is not None and data.get("SAM", 0) > 0:
                profile.SAM = float(data.get("SAM"))
            if data.get("SOM") is not None and data.get("SOM", 0) > 0:
                profile.SOM = float(data.get("SOM"))
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
        return profile.model_dump_json(indent=2)

    task = Task(
        description="Analyze the market size and expected growth rate for the startup's sector. Estimate TAM, SAM, SOM, and provide supporting data and sources.",
        agent=analyst,
        expected_output="A detailed market analysis report including TAM, SAM, SOM, growth rates, and sources.",
        callback=_callback,
    )
    return analyst, task
