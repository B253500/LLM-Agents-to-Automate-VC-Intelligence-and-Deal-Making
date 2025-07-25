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

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

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
    If it's a number, format it nicely.
    """
    # If it's already a string (with units), return as-is
    if isinstance(val, str):
        return val
    
    try:
        val = float(val)
    except (TypeError, ValueError):
        return str(val)
    
    # For numeric values, format nicely
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
    sector = getattr(profile, 'sector', '')
    
    # --- Perplexity search for market research URLs ---
    market_research_urls = []
    if sector:
        try:
            # Use Perplexity to find relevant market research reports
            search_queries = [
                f"{sector} market size report 2024 2025",
                f"{sector} industry analysis TAM SAM",
                f"{sector} market research growth trends"
            ]
            
            for query in search_queries:
                try:
                    # Use Perplexity search to get market research URLs
                    search_results = search_perplexity(query, num_results=3)
                    
                    if search_results:
                        # Extract URLs from the search results
                        import re
                        urls = re.findall(r'https?://[^\s\)]+', search_results)
                        # Filter for market research domains
                        market_domains = ['statista', 'grandviewresearch', 'marketsandmarkets', 'mckinsey', 'bain', 'bcg', 'deloitte', 'pwc', 'kpmg', 'ey', 'forrester', 'gartner', 'idc', 'frost', 'technavio', 'ibisworld', 'marketresearch', 'researchandmarkets', 'alliedmarketresearch', 'persistencemarketresearch', 'factmr', 'coherentmarketinsights', 'transparencymarketresearch', 'emergenresearch', 'precedenceresearch', 'verifiedmarketresearch', 'marketdataforecast', 'marketresearchfuture', '360marketupdates', 'marketwatch', 'bloomberg', 'reuters', 'cnbc', 'wsj', 'ft', 'forbes', 'techcrunch', 'venturebeat']
                        
                        for url in urls:
                            if any(domain in url.lower() for domain in market_domains):
                                market_research_urls.append(url)
                                if len(market_research_urls) >= 3:
                                    break
                    
                    if len(market_research_urls) >= 3:
                        break
                        
                except Exception as e:
                    print(f"[Market Research] Error searching for {query}: {e}")
                    continue
                    
        except Exception as e:
            print(f"[Market Research] Error during Perplexity search: {e}")
    
    # --- Perplexity for market analysis content (without URL extraction) ---
    sector_analysis = ""
    if sector:
        try:
            search_query = f"Latest market analysis and trends for the {sector} sector in 2024-2025. Focus on market size, growth drivers, and key trends."
            search_results = search_perplexity(search_query, num_results=2)
            
            if search_results:
                # Use LLM to summarize the analysis without trying to extract URLs
                summary_prompt = f"""
                Based on the following market research for the '{sector}' sector, provide a concise summary (2-3 sentences) covering:
                1. Key market trends and drivers
                2. Growth projections and opportunities
                3. Important industry developments
                
                Focus on actionable insights for investment analysis. Do not include URLs or citations.
                
                Research Results:
                {search_results}
                """
                sector_analysis = llm.invoke(summary_prompt).content.strip()
        except Exception as e:
            print(f"[Market Analysis] Error during sector analysis: {e}")
    
    web_sources = getattr(profile, 'market_size_sources', []) or []
    web_links = [url for url in web_sources if url.startswith('http')][:3]
    
    # Generate market discussion
    prompt = f"""
You are a VC analyst writing the Market Size & Analysis section for an investment memo.
Write a concise, professional market analysis (4-6 sentences) that covers:
- Current market size and growth trajectory
- Key market drivers and trends
- Competitive landscape considerations
- Opportunities and challenges for the company

Use the following data and be specific about numbers and sources. Present the market data as provided without assuming units.

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
    
    if metrics_data:
        for metric, value, source in metrics_data:
            source_str = format_source(source)
            lines.append(f"• **{metric}**: {value}{source_str}")
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
    
    # 4. Sector Analysis (without URLs)
    if sector_analysis:
        lines.append("**📰 Sector Analysis**")
        lines.append("")
        lines.append(sector_analysis)
        lines.append("")
    
    # 5. Market Research Sources (Perplexity search results)
    if market_research_urls:
        lines.append("**🔍 Market Research Sources**")
        lines.append("")
        for url in market_research_urls:
            domain = url.split('/')[2] if len(url.split('/')) > 2 else url
            lines.append(f"• [{domain}]({url})")
        lines.append("")
    
    # 6. Additional Web Sources (if any from profile)
    if web_links:
        lines.append("**🔗 Additional Sources**")
        for url in web_links:
            domain = url.split('/')[2] if len(url.split('/')) > 2 else url
            lines.append(f"• [{domain}]({url})")
        lines.append("")
    
    return '\n'.join(lines)

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
