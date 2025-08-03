import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

def web_search_business_model_context(company_name):
    # Placeholder: Integrate EXA, Perplexity, or other API here
    # Return a string with web search results
    return ""

SYSTEM = """
You are a VC analyst specializing in business model analysis.
Analyze the startup's materials and provide:

1. **Overall Business Model Summary** (3-6 sentences):
   - A concise summary of the POTENTIAL business model based on available information
   - Discussion of potential revenue streams, customer segments, go-to-market strategy, and scalability
   - Any recent business model news or pivots (use web search context if available)
   - Attribute sources where possible

2. **Specific Business Model Details** (extract if mentioned):
   - Individual customer model (e.g., freemium, subscription, one-time)
   - SMB/Enterprise model (e.g., per-seat licensing, shared folders)
   - Platform aspects (e.g., broker UGC, API access)
   - IT cost reduction benefits (e.g., reduces IT headcount, replaces existing tools)

IMPORTANT: Use tentative language and clearly indicate when you are making assumptions or interpretations.
- Use phrases like "appears to be", "seems to", "may be", "could be", "based on available information"
- Do not present assumptions as facts about current business model
- If information is limited, explicitly state what additional research is needed

Return a JSON object with:
{
  "business_model_summary": "overall summary",
  "business_model_individuals": "individual customer model details",
  "business_model_smb": "SMB/enterprise model details", 
  "business_model_platform": "platform aspects",
  "it_cost_reduction": "IT cost reduction benefits"
}

If any field is not mentioned or unclear, use null.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Startup info:\n{context}\nWeb search context:\n{web_context}\n")
])

def run_business_model_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    context = full_text[:5000]
    web_context = web_search_business_model_context(profile.name)
    
    try:
        response = llm.invoke(PROMPT.format(context=context, web_context=web_context)).content.strip()
        
        # Try to parse JSON response
        try:
            parsed = json.loads(response)
            profile.business_model = parsed.get("business_model_summary", "")
            profile.business_model_individuals = parsed.get("business_model_individuals")
            profile.business_model_smb = parsed.get("business_model_smb")
            profile.business_model_platform = parsed.get("business_model_platform")
            profile.it_cost_reduction = parsed.get("it_cost_reduction")
        except json.JSONDecodeError:
            # Fallback to original behavior
            profile.business_model = response
            
    except Exception as e:
        print(f"Business model chain error: {e}")
        profile.business_model = "Error extracting business model information."
    
    return profile 