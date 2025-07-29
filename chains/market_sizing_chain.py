import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context
from core.perplexity_utils import search_perplexity

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

def web_search_market_context(company_name, sector):
    if not company_name and not sector:
        return ""
    query = f"Latest market size, growth rate, and trends for {company_name or 'the company'} in the {sector or ''} sector. Provide TAM, SAM, SOM if available, and cite sources."
    result = search_perplexity(query)
    return result or ""

SYSTEM = """
You are a market research analyst for venture capital.
For the given company and sector, provide a detailed, structured market analysis.

IMPORTANT: Return your analysis in the following JSON format:
{
    "TAM": <numeric value in billions or millions>,
    "SAM": <numeric value in billions or millions>,
    "SOM": <numeric value in billions or millions>,
    "TAM_original": "<original string with units from source>",
    "SAM_original": "<original string with units from source>", 
    "SOM_original": "<original string with units from source>",
    "summary": "<narrative market analysis paragraph>",
    "reasoning": "<explanation of how market sizes were determined>"
}

Guidelines:
- Use realistic market size values (TAM should be largest, SAM smaller, SOM smallest)
- If specific data is unavailable, use reasonable estimates based on the sector
- TAM should typically be in billions for major sectors
- SAM should be 10-50% of TAM
- SOM should be 1-10% of TAM
- Include original strings with units (e.g., "$160B", "$50M") in the _original fields
- Provide a narrative summary in the summary field
- Explain your reasoning in the reasoning field
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Company & sector info:\n{context}\nWeb search context:\n{web_context}\n")
])


def run_market_sizing_chain(profile: StartupProfile) -> StartupProfile:
    context = get_hybrid_context(
        profile, "market size OR TAM OR SAM OR SOM OR industry", 3, 3
    )
    web_context = web_search_market_context(profile.name, profile.sector)
    
    try:
        txt = llm.invoke(PROMPT.format(context=context, web_context=web_context)).content.strip()
        print(f"[Market Chain] LLM raw output: {txt[:200]}...")
        
        # Find JSON in the response
        first, last = txt.find("{"), txt.rfind("}")
        if first == -1 or last == -1:
            print("[Market Chain] No JSON found in response")
            return profile
            
        json_str = txt[first : last + 1]
        
        # Clean up the JSON string
        import re
        # Remove any newlines and extra whitespace that might break JSON
        json_str = re.sub(r'\s+', ' ', json_str)
        json_str = json_str.replace('\n', ' ').replace('\r', ' ')
        
        try:
            data = json.loads(json_str)
            print(f"[Market Chain] Parsed JSON: {data}")
            
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
                
        except json.JSONDecodeError as e:
            print(f"[Market Chain JSON Error] {e}")
            print(f"[Market Chain] Failed JSON string: {json_str}")
            return profile
            
    except Exception as e:
        print(f"[Market Chain Error] {e}")
        return profile
        
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile

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
