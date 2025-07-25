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
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

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

Return your analysis in the following JSON format:
{
    "tech_maturity": "Brief assessment of technical maturity (e.g., 'Early-stage prototype', 'Production-ready', 'Lab-scale')",
    "moat_strength": "Assessment of technical moat and defensibility",
    "tech_stack": "Detailed description of the technology stack and architecture (3-4 sentences covering core technologies, infrastructure, and technical approach)",
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
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Try to fix common JSON issues
        json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        json_str = re.sub(r':\s*([^",\{\}\[\]]+?)([,}\]])', r': "\1"\2', json_str)
        try:
            return json.loads(json_str)
        except:
            return None


def run_technical_dd_chain(profile: StartupProfile) -> StartupProfile:
    context = get_hybrid_context(
        profile, "technology stack OR product OR patents OR infrastructure", 3, 3
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
