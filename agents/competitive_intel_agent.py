from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from crewai_tools import EXASearchTool
from core.schemas import StartupProfile
from chains.competitive_intel_chain import run_competitive_intel_chain
from core.perplexity_utils import search_perplexity
from dotenv import load_dotenv
import os
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

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)

def generate_competitive_landscape(profile: StartupProfile) -> str:
    """Enhanced competitive landscape with detailed competitor analysis"""
    competitors = getattr(profile, 'top_competitors', [])
    if not competitors:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)
        # Try to generate competitors from context with detailed descriptions
        prompt = f"""
        Based on this company's profile, identify exactly 3 main competitors in their space. For each competitor, provide:
        - Company name
        - Website URL
        - 2-3 sentence description of their product/technology
        - Key differentiator or competitive advantage
        
        Company: {getattr(profile, 'name', '')}
        Sector: {getattr(profile, 'sector', '')}
        Product: {getattr(profile, 'product_description', '')}
        Market: {getattr(profile, 'market_summary', '')}
        
        Format each competitor as:
        • **Company Name** (website.com)
          Product description: [2-3 sentences about their technology/product]
          Key differentiator: [What makes them unique]
        
        Focus on real companies with actual websites. For battery technology companies, consider companies like:
        - QuantumScape (quantumscape.com) - Solid-state battery technology
        - Solid Power (solidpowerbattery.com) - Solid-state battery development
        - SES AI Corporation (ses.ai) - AI-powered battery management
        - CATL (catl.com) - Lithium-ion battery manufacturing
        - Panasonic (panasonic.com) - Automotive battery solutions
        
        Provide specific, factual information about each competitor's technology and market position.
        """
        competitors_text = llm.invoke(prompt).content.strip()
        if competitors_text:
            # Keep B253500 tokens - don't remove them
            return f"Key Competitors Analysis:\n{competitors_text}\n\nNote: This analysis should be verified with additional research."

    # Find websites for competitors that don't have them
    from core.external_enrichment import find_company_website
    for comp in competitors:
        # Handle both dict and Competitor objects
        if hasattr(comp, 'name'):  # Competitor object
            name = comp.name
            website = comp.url or comp.website if hasattr(comp, 'url') or hasattr(comp, 'website') else None
            if not website:
                try:
                    website = find_company_website(
                        company_name=name,
                        sector=getattr(profile, 'sector', None),
                        deck_text=None
                    )
                    if website:
                        comp.url = website
                        print(f"[Competitor Website] Found website for {name}: {website}")
                except Exception as e:
                    print(f"[Competitor Website] Error finding website for {name}: {e}")
        else:  # dict object
            if not comp.get('website') and not comp.get('url'):
                try:
                    website = find_company_website(
                        company_name=comp.get('name', ''),
                        sector=getattr(profile, 'sector', None),
                        deck_text=None
                    )
                    if website:
                        comp['website'] = website
                        print(f"[Competitor Website] Found website for {comp.get('name')}: {website}")
                except Exception as e:
                    print(f"[Competitor Website] Error finding website for {comp.get('name')}: {e}")

    lines = ["Key Competitors Analysis:"]
    
    # Limit to top 3 competitors
    top_competitors = competitors[:3]
    
    for comp in top_competitors:
        # Handle both dict and Competitor objects
        if hasattr(comp, 'name'):  # Competitor object
            name = comp.name
            website = comp.url or comp.website if hasattr(comp, 'url') or hasattr(comp, 'website') else ''
            product = comp.product_offering or comp.product or comp.description if hasattr(comp, 'product_offering') or hasattr(comp, 'product') or hasattr(comp, 'description') else ''
            differentiator = comp.differentiator if hasattr(comp, 'differentiator') else ''
        else:  # dict object
            name = comp.get('name', 'Unknown')
            website = comp.get('website', '') or comp.get('url', '')
            product = comp.get('product_offering', '') or comp.get('product', '') or comp.get('description', '')
            differentiator = comp.get('differentiator', '')
        
        # Header with name and website (make name bold)
        if website:
            lines.append(f"\n• **{name}** ({website})")
        else:
            lines.append(f"\n• **{name}**")
            
        if product:
            lines.append(f"  Product: {product}")
        if differentiator and differentiator != product:
            lines.append(f"  Differentiator: {differentiator}")
            
        # Add competitive positioning
        if getattr(profile, 'competitive_positioning', None):
            lines.append(f"  Positioning vs {name}: {profile.competitive_positioning}")
            
    # Add competitive summary if available
    if getattr(profile, 'competitive_summary', None):
        lines.append(f"\nCompetitive Summary:\n{profile.competitive_summary}")
        
    lines.append("\nNote: This analysis should be verified with additional research.")
        
    return '\n'.join(lines)

def build_competitive_intel_agent(profile: StartupProfile, trace_id=None):
    scout = Agent(
        role="AI Startup Intelligence Specialist",
        goal="Identify and analyze relevant AI startups within specific AI subsegment markets.",
        backstory="Expert in mapping competitive landscapes for specific AI verticals. Specialized in identifying real, named emerging startups and scale-ups rather than tech giants. Known for finding verifiable information about startups' funding, technology, and market focus.",
        tools=[exa_search_tool],
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        # Use comprehensive extracted data context
        from core.hybrid_context import get_hybrid_context
        
        # Get comprehensive context including all extracted data
        comprehensive_context = get_hybrid_context(profile, "competitive analysis competitors", use_reports=False)
        
        # Run competitive analysis with comprehensive context
        updated = run_competitive_intel_chain(profile, comprehensive_context)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Find the main AI startup competitors for the startup's sector. Identify exactly 3 specific AI startup competitors by name, and provide company details and traction.",
        agent=scout,
        expected_output="A comprehensive competitor analysis including company names, details, and traction.",
        callback=_callback,
    )
    return scout, task
