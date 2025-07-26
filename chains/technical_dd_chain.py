import json
import re
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

SYSTEM = """
You are a senior CTO performing technical due diligence for venture capital investment.
For the given company, provide a detailed, critical analysis of the technology.

IMPORTANT: Use tentative language and clearly indicate when you are making assumptions or interpretations. 
- Use phrases like "appears to be", "seems to", "may be", "could be", "based on available information"
- Do not present assumptions as facts
- If information is limited, explicitly state what additional research is needed

CRITICAL REQUIREMENTS:
1. CAREFULLY EXTRACT ALL PATENT INFORMATION from the provided context
2. CAREFULLY EXTRACT ALL PRODUCT ROADMAP INFORMATION from the provided context
3. CAREFULLY EXTRACT ALL PRODUCT TECHNICAL SPECIFICATIONS from the provided context
4. Look for specific patent numbers, filing dates, patent areas, and patent status
5. Look for development phases, milestones, timelines, and commercialization plans
6. Look for technical specifications, performance metrics, materials, dimensions, capabilities
7. If the context contains patent, roadmap, or technical specification information, USE IT - do not say "requires additional research"

TECH STACK REQUIREMENTS:
- Provide a detailed 3-4 sentence description of the technology stack
- Cover core technologies, infrastructure, and technical approach
- Include specific technologies, frameworks, or methodologies mentioned
- Be comprehensive but avoid speculation

PRODUCT TECHNICAL SPECIFICATIONS REQUIREMENTS:
- Extract and summarize all product technical specifications from the context
- Include performance metrics, materials, dimensions, capabilities, and key features
- Look for specific numbers, measurements, performance data, and technical parameters
- Cover energy density, cycle life, charging speed, temperature range, safety features
- Include any technical comparisons or benchmarks mentioned
- If technical specifications are present in the context, provide specific details

PRODUCT ROADMAP REQUIREMENTS:
- Extract and summarize any product development roadmap information from the context
- Include current phase, next milestones, and future development stages
- Focus on technical milestones and commercialization timeline
- If roadmap information is present in the context, provide specific details

PATENT ANALYSIS REQUIREMENTS:
- Extract and summarize any patent portfolio information from the context
- Include number of patents, key patent areas, and patent strength
- Look for specific patent numbers, filing dates, and patent descriptions
- Assess patent defensibility and potential for licensing revenue
- If patent information is present in the context, provide specific details

Return your analysis in the following JSON format:
{
    "tech_maturity": "Brief assessment of technical maturity (e.g., 'Early-stage prototype', 'Production-ready', 'Lab-scale')",
    "moat_strength": "Assessment of technical moat and defensibility",
    "tech_stack": "Detailed description of the technology stack and architecture (3-4 sentences covering core technologies, infrastructure, and technical approach)",
    "product_specifications": "Detailed product technical specifications including performance metrics, materials, dimensions, capabilities, and key features (3-4 sentences with specific numbers and data)",
    "product_roadmap": "Brief product development roadmap with current phase and future milestones (2-3 sentences)",
    "patent_portfolio": "Assessment of patent portfolio including number of patents, key areas, and strength (2-3 sentences)",
    "complexity": "Assessment of technical complexity",
    "security": "Security considerations and risks",
    "implementation": "Implementation challenges and requirements",
    "regulatory": "Regulatory and compliance considerations",
    "testing": "Testing and validation requirements"
}

Be specific, critical, and highlight both strengths and weaknesses. If information is missing, note it explicitly.
Focus on actionable insights for VC investment decision-making.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Startup info:\n{context}")]
)


def clean_llm_output(text):
    """Clean LLM output to extract valid JSON."""
    # Remove thinking output
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Keep B253500 tokens - don't remove them
    
    # Find JSON content
    first, last = text.find("{"), text.rfind("}")
    if first == -1 or last == -1:
        return None
    
    json_str = text[first:last + 1]
    
    # Clean up common JSON formatting issues
    json_str = json_str.strip()
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[Technical DD] JSON parsing error: {e}")
        print(f"[Technical DD] Raw JSON: {json_str[:200]}...")
        
        # Try to fix common JSON issues
        # Fix unquoted keys
        json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        # Fix unquoted string values
        json_str = re.sub(r':\s*([^",\{\}\[\]]+?)([,}\]])', r': "\1"\2', json_str)
        # Remove bullet points from string values
        json_str = re.sub(r'•\s*', '', json_str)
        # Remove extra whitespace and newlines
        json_str = re.sub(r'\s+', ' ', json_str)
        # Fix trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e2:
            print(f"[Technical DD] Second JSON parsing error: {e2}")
            print(f"[Technical DD] Cleaned JSON: {json_str[:200]}...")
            return None


def run_technical_dd_chain(profile: StartupProfile) -> StartupProfile:
    context = get_hybrid_context(
        profile, "patents OR patent portfolio OR intellectual property OR IP OR product roadmap OR development timeline OR technical milestones OR technology stack OR product development OR technical specifications OR performance metrics OR energy density OR cycle life OR charging speed OR temperature range OR safety features OR materials OR dimensions OR capabilities", 5, 3
    )
    
    # Debug: Print a snippet of the context to see what's being passed
    print(f"[Technical DD] Context snippet: {context[:500]}...")
    
    try:
        # Clean the context to avoid formatting issues
        clean_context = context.replace('"', "'").replace('\n', ' ').strip()
        txt = llm.invoke(PROMPT.format(context=clean_context)).content.strip()
        data = clean_llm_output(txt)
        
        if data:
            # Set profile attributes from the cleaned data
            if data.get("tech_maturity"):
                profile.tech_maturity = str(data["tech_maturity"])
            if data.get("moat_strength"):
                profile.moat_strength = str(data["moat_strength"])
            if data.get("tech_stack"):
                profile.tech_stack = str(data["tech_stack"])
            if data.get("product_roadmap"):
                profile.product_roadmap = str(data["product_roadmap"])
            if data.get("patent_portfolio"):
                profile.patent_portfolio = str(data["patent_portfolio"])
            if data.get("complexity"):
                profile.complexity = str(data["complexity"])
            if data.get("security"):
                profile.security = str(data["security"])
            if data.get("implementation"):
                profile.implementation = str(data["implementation"])
            if data.get("regulatory"):
                profile.regulatory = str(data["regulatory"])
            if data.get("testing"):
                profile.testing = str(data["testing"])
        else:
            # Fallback: set default values if parsing fails
            profile.tech_maturity = "Technical maturity assessment requires additional research"
            profile.moat_strength = "Moat strength analysis requires additional research"
            
    except Exception as e:
        print(f"[Technical DD] Error: {e}")
        # Set fallback values
        profile.tech_maturity = "Technical assessment unavailable"
        profile.moat_strength = "Moat analysis unavailable"
        profile.tech_stack = "Technology stack details require additional research"
        profile.product_specifications = "Product technical specifications require additional research"
        profile.product_roadmap = "Product roadmap information requires additional research"
        profile.patent_portfolio = "Patent portfolio information requires additional research"
        profile.complexity = "Technical complexity assessment requires additional research"
        profile.security = "Security considerations require additional research"
        profile.implementation = "Implementation details require additional research"
        profile.regulatory = "Regulatory compliance information requires additional research"
        profile.testing = "Testing and validation information requires additional research"
    
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    
    return profile


def run_technical_dd_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    """Run technical due diligence using extracted text as context."""
    # Use more text to capture patent and roadmap information
    context = full_text[:8000]  # Increased from 5000 to capture more content
    
    # Debug: Print a snippet of the context to see what's being passed
    print(f"[Technical DD] Full text context snippet: {context[:500]}...")
    
    try:
        # Clean the context to avoid formatting issues
        clean_context = context.replace('"', "'").replace('\n', ' ').strip()
        txt = llm.invoke(PROMPT.format(context=clean_context)).content.strip()
        data = clean_llm_output(txt)
        
        if data:
            # Set profile attributes from the cleaned data
            if data.get("tech_maturity"):
                profile.tech_maturity = str(data["tech_maturity"])
            if data.get("moat_strength"):
                profile.moat_strength = str(data["moat_strength"])
            if data.get("tech_stack"):
                profile.tech_stack = str(data["tech_stack"])
            if data.get("product_roadmap"):
                profile.product_roadmap = str(data["product_roadmap"])
            if data.get("patent_portfolio"):
                profile.patent_portfolio = str(data["patent_portfolio"])
            if data.get("complexity"):
                profile.complexity = str(data["complexity"])
            if data.get("security"):
                profile.security = str(data["security"])
            if data.get("implementation"):
                profile.implementation = str(data["implementation"])
            if data.get("regulatory"):
                profile.regulatory = str(data["regulatory"])
            if data.get("testing"):
                profile.testing = str(data["testing"])
        else:
            # Fallback: set default values if parsing fails
            profile.tech_maturity = "Technical maturity assessment requires additional research"
            profile.moat_strength = "Moat strength analysis requires additional research"
            
    except Exception as e:
        print(f"[Technical DD] Error: {e}")
        # Set fallback values
        profile.tech_maturity = "Technical assessment unavailable"
        profile.moat_strength = "Moat analysis unavailable"
    
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    
    return profile
