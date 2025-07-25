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

TECH STACK REQUIREMENTS:
- Provide a detailed 3-4 sentence description of the technology stack
- Cover core technologies, infrastructure, and technical approach
- Include specific technologies, frameworks, or methodologies mentioned
- Be comprehensive but avoid speculation

PRODUCT ROADMAP REQUIREMENTS:
- If available, provide a brief product development roadmap
- Include current phase, next milestones, and future development stages
- Focus on technical milestones and commercialization timeline

PATENT ANALYSIS REQUIREMENTS:
- If available, provide a brief assessment of the company's patent portfolio
- Include number of patents, key patent areas, and patent strength
- Assess patent defensibility and potential for licensing revenue
- Note if patent information is limited or unavailable

Return your analysis in the following JSON format:
{
    "tech_maturity": "Brief assessment of technical maturity (e.g., 'Early-stage prototype', 'Production-ready', 'Lab-scale')",
    "moat_strength": "Assessment of technical moat and defensibility",
    "tech_stack": "Detailed description of the technology stack and architecture (3-4 sentences covering core technologies, infrastructure, and technical approach)",
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
    [("system", SYSTEM), ("human", "Startup info:\n{context}\n")]
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
        profile, "technology stack OR product OR patents OR patent portfolio OR intellectual property OR IP", 3, 3
    )
    
    try:
        txt = llm.invoke(PROMPT.format(context=context)).content.strip()
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
        profile.product_roadmap = "Product roadmap information requires additional research"
        profile.patent_portfolio = "Patent portfolio information requires additional research"
        profile.complexity = "Technical complexity assessment requires additional research"
        profile.security = "Security considerations require additional research"
        profile.implementation = "Implementation details require additional research"
        profile.regulatory = "Regulatory compliance information requires additional research"
        profile.testing = "Testing and validation information requires additional research"
        profile.tech_stack = "Technology stack details require additional research"
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
    context = full_text[:5000]  # Truncate if needed for prompt size
    
    try:
        txt = llm.invoke(PROMPT.format(context=context)).content.strip()
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
