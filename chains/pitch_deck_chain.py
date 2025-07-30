from hashlib import sha1
from pathlib import Path
import json
import re

import pdfplumber
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile
from core.vector_store import add_doc

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parents[1] / ".env")  # loads OPENAI_API_KEY
llm = ChatOpenAI(model="gpt-4", temperature=0.2)

SYSTEM = """
You are a top-tier VC investment analyst. Extract the following fields as JSON:
- name
- founder_name
- sector
- website
- funding_stage
- executives: a list of ONLY the following roles if present: CEO/Founder, CFO (Chief Financial Officer), Chairman, CTO (Chief Technology Officer). For each, include name, role, LinkedIn if available, and a list of prior exits with company name and link if available.

IMPORTANT: For executives, DO NOT duplicate the same person. If someone appears multiple times with different roles, combine them into one entry with all roles. For example, if "Drew Houston" appears as both "CEO" and "Founder", create one entry: {{"name": "Drew Houston", "role": "CEO/Founder"}}

For the 'name' field: 
1. Look for the official company name that appears most frequently in the text
2. Common patterns: "Company Name Inc", "Company Name Corp", "Company Name Technologies", "Company Name"
3. For well-known companies, use their official name (e.g., "Shopify", "Tesla", "Uber")
4. Do not return slogans, products, or generic terms like "Company" or "All"
5. If the company name is clearly stated, use it exactly as written
6. If not explicitly stated, return "unknown"

For the 'sector' field: Be specific about the business sector (e.g., "ecommerce", "fintech", "battery technology", "healthtech")

ADDITIONAL METRICS TO EXTRACT:
- total_merchants: Number of active merchants/users (e.g., "200,000+")
- total_gmv: Total gross merchandise volume (e.g., "$1.9B+")
- revenue_growth: Revenue growth figures if mentioned
- mrr_growth: Monthly recurring revenue growth if mentioned
- target_market: Target market size or description
- business_model: Key revenue streams (subscription, transaction fees, etc.)
- key_metrics: Any other important business metrics mentioned

If not explicitly stated, return "unknown". Do NOT hallucinate or infer.
Return ONLY valid JSON.
"""
HUMAN = "Pitch-deck text (first 5000 characters):\n```markdown\n{deck}\n```"
PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", HUMAN)])


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def pdf_to_text(path: Path) -> str:
    """Concatenate text from every page of a PDF."""
    with pdfplumber.open(path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(pages)


def extract_company_name_with_ai(text: str) -> str:
    """Use AI to detect the company name from text"""
    try:
        ai_prompt = f"""
        Analyze the following text and identify the official company name.
        
        Rules:
        1. Look for the company that this pitch deck is about
        2. Return ONLY the company name, not slogans or products
        3. For well-known companies, use their official name (e.g., "Shopify", "Tesla", "Uber")
        4. If multiple companies are mentioned, identify the main company this deck is for
        5. If unclear, return "unknown"
        
        Text to analyze:
        {text[:3000]}
        
        Return ONLY the company name:
        """
        
        response = llm.invoke(ai_prompt)
        company_name = response.content.strip().strip('"').strip("'")
        
        # Clean up the response
        if company_name.lower() in ['unknown', 'none', 'n/a', '']:
            return "unknown"
        
        return company_name
    except Exception as e:
        print(f"[AI Company Detection] Error: {e}")
        return "unknown"


def extract_website_with_ai(text: str, company_name: str = None) -> str:
    """Use AI to detect the company website from text"""
    try:
        ai_prompt = f"""
        Analyze the following text and identify the official company website.
        
        Rules:
        1. Look for the main company website URL
        2. Common patterns: www.companyname.com, companyname.com, https://companyname.com
        3. For well-known companies, use their official website (e.g., shopify.com, tesla.com)
        4. If multiple URLs are mentioned, identify the main company website
        5. If unclear, return "unknown"
        
        Company name: {company_name or "unknown"}
        Text to analyze:
        {text[:3000]}
        
        Return ONLY the website URL (without http/https if not in text):
        """
        
        response = llm.invoke(ai_prompt)
        website = response.content.strip().strip('"').strip("'")
        
        # Clean up the response
        if website.lower() in ['unknown', 'none', 'n/a', '']:
            return "unknown"
        
        # Add protocol if missing
        if website and website != "unknown" and not website.startswith(('http://', 'https://')):
            website = f"https://{website}"
        
        return website
    except Exception as e:
        print(f"[AI Website Detection] Error: {e}")
        return "unknown"


def extract_financial_metrics_with_ai(text: str) -> dict:
    """Use AI to extract financial and business metrics from pitch deck text"""
    try:
        ai_prompt = f"""
        Analyze the following pitch deck text and extract key financial and business metrics.
        
        Look for and extract:
        1. Total merchants/users (e.g., "200,000+ merchants")
        2. Gross Merchandise Volume (GMV) (e.g., "$1.9B+ GMV")
        3. Revenue figures (e.g., "$195M revenue")
        4. Monthly Recurring Revenue (MRR) (e.g., "$9.8M MRR")
        5. Employee count (e.g., "10,000+ employees")
        6. Target market size (e.g., "$46B TAM")
        7. Growth rates (e.g., "85% CAGR")
        8. Business model details (e.g., "subscription fees", "transaction fees")
        
        Return ONLY a JSON object with these fields:
        {{
            "total_merchants": "number or description",
            "total_gmv": "amount or description", 
            "revenue": "amount or description",
            "mrr": "amount or description",
            "employees": "number or description",
            "target_market": "size or description",
            "growth_rate": "percentage or description",
            "business_model": "description of revenue streams"
        }}
        
        If a metric is not found, use "unknown". Be specific with numbers when available.
        
        Text to analyze:
        {text[:4000]}
        """
        
        response = llm.invoke(ai_prompt)
        result = response.content.strip()
        
        # Extract JSON from response
        import json
        try:
            # Find JSON in the response
            start = result.find('{')
            end = result.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = result[start:end]
                metrics = json.loads(json_str)
                return metrics
            else:
                print(f"[AI Metrics] No JSON found in response: {result}")
                return {}
        except json.JSONDecodeError as e:
            print(f"[AI Metrics] JSON parsing error: {e}")
            return {}
            
    except Exception as e:
        print(f"[AI Metrics] Error: {e}")
        return {}


def deduplicate_executives(executives: list) -> list:
    """Deduplicate executives by name, keeping the most complete entry for each person"""
    if not executives:
        return []
    
    # Group executives by normalized name
    name_groups = {}
    
    for exec_data in executives:
        if not isinstance(exec_data, dict):
            continue
            
        name = exec_data.get("name", "").strip()
        if not name:
            continue
            
        # Normalize name for comparison (remove extra spaces, lowercase)
        normalized_name = " ".join(name.lower().split())
        
        if normalized_name not in name_groups:
            name_groups[normalized_name] = []
        name_groups[normalized_name].append(exec_data)
    
    # For each group, keep the most complete entry
    deduplicated = []
    for normalized_name, group in name_groups.items():
        if len(group) == 1:
            deduplicated.append(group[0])
        else:
            # Choose the most complete entry (most fields filled)
            best_entry = max(group, key=lambda x: sum(1 for v in x.values() if v))
            deduplicated.append(best_entry)
            print(f"[Team Deduplication] Merged {len(group)} entries for '{best_entry.get('name', 'Unknown')}'")
    
    return deduplicated


def extract_common_term(text: str, pdf_path: str) -> str:
    """Enhanced company name extraction with AI fallback"""
    
    # First try AI detection
    ai_name = extract_company_name_with_ai(text)
    if ai_name and ai_name.lower() != "unknown":
        print(f"[Company Detection] AI detected: {ai_name}")
        return ai_name
    
    # Fallback to regex-based extraction
    company_patterns = [
        r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b",  # Standard capitalized words
        r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Company|Co|Technologies|Tech|Systems|Solutions))\b",  # With company suffixes
        r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*\s+(?:International|Global|Worldwide|Enterprises|Group|Partners))\b",  # With business suffixes
    ]
    
    all_matches = []
    for pattern in company_patterns:
        matches = re.findall(pattern, text)
        all_matches.extend(matches)
    
    if all_matches:
        # Count frequency and filter out common words
        freq = {}
        for name in all_matches:
            name = name.strip()
            if len(name) > 2:  # Avoid very short names
                freq[name] = freq.get(name, 0) + 1
        
        # Filter out common/generic terms
        generic_terms = {
            "all", "company", "unknown", "the", "and", "for", "with", "from", "this", "that", 
            "have", "will", "been", "they", "their", "them", "were", "said", "each", "which",
            "there", "were", "been", "other", "about", "many", "then", "them", "these", "so",
            "some", "her", "would", "make", "like", "into", "him", "time", "two", "more", "go",
            "no", "way", "could", "my", "than", "first", "been", "call", "who", "its", "now",
            "find", "long", "down", "day", "did", "get", "come", "made", "may", "part"
        }
        
        # Remove generic terms and sort by frequency
        filtered_freq = {k: v for k, v in freq.items() if k.lower() not in generic_terms}
        
        if filtered_freq:
            sorted_names = sorted(filtered_freq.items(), key=lambda x: x[1], reverse=True)
            likely_term = sorted_names[0][0]
            
            # Additional validation: prefer longer names (likely company names)
            if len(likely_term.split()) >= 1:
                print(f"[Company Detection] Regex detected: {likely_term}")
                return likely_term
        
        # If no good matches found, try the original approach
        if freq:
            sorted_names = sorted(freq.items(), key=lambda x: x[1], reverse=True)
            likely_term = sorted_names[0][0]
            if likely_term.lower() not in ["all", "company", "unknown"]:
                print(f"[Company Detection] Fallback regex detected: {likely_term}")
                return likely_term
    
    # Final fallback to PDF filename
    fallback_name = Path(pdf_path).stem.replace("_", " ").replace("-", " ").title()
    print(f"[Company Detection] Using PDF filename: {fallback_name}")
    return fallback_name


# ---------------------------------------------------------------------
# Main chain function
# ---------------------------------------------------------------------
def run_pitch_deck_chain_with_text(deck_text: str, profile: StartupProfile = None, pdf_path: str = None) -> StartupProfile:
    """Run pitch deck analysis using extracted text directly"""
    if profile is None:
        profile = StartupProfile()
    
    truncated_text = deck_text[:5000]

    prompt = PROMPT.format(deck=truncated_text)
    response = llm.invoke(prompt)
    txt = response.content.strip()

    # Extract JSON from LLM output
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1 or last < first:
        print("[Warning] No JSON object found, falling back to extraction")
        fallback_name = extract_common_term(truncated_text, pdf_path or "unknown.pdf")
        profile.name = fallback_name
    else:
        try:
            json_str = txt[first : last + 1]
            raw = json.loads(json_str)

            if not raw.get("name") or raw.get("name").lower() in ["unknown", "all", "company"]:
                fallback_name = extract_common_term(truncated_text, pdf_path or "unknown.pdf")
                raw["name"] = fallback_name

            if (
                not raw.get("founder_name")
                or raw.get("founder_name").lower() == "unknown"
            ):
                raw["founder_name"] = "unknown"

            # Update profile with extracted data
            for key, value in raw.items():
                if hasattr(profile, key) and value:
                    setattr(profile, key, value)
            
            # Extract additional metrics using AI
            additional_metrics = extract_financial_metrics_with_ai(truncated_text)
            for key, value in additional_metrics.items():
                if hasattr(profile, key) and value:
                    setattr(profile, key, value)
                    print(f"[AI Metrics] Set {key} = {value}")
            
            # Explicitly handle executives if present
            if "executives" in raw and raw["executives"]:
                # Deduplicate executives by name
                deduplicated_executives = deduplicate_executives(raw["executives"])
                profile.executives = deduplicated_executives
                print(f"[Team Extraction] Found {len(deduplicated_executives)} unique executives")
                
                # Collect all prior exits from executives
                prior_exit_details = []
                for exec in deduplicated_executives:
                    if isinstance(exec, dict) and exec.get("prior_exits"):
                        for ex in exec["prior_exits"]:
                            prior_exit_details.append(ex)
                if prior_exit_details:
                    profile.prior_exit_details = prior_exit_details
        except Exception as e:
            print(f"[Error] Failed to parse LLM output: {e}")
            fallback_name = extract_common_term(truncated_text, pdf_path or "unknown.pdf")
            profile.name = fallback_name

    # Fallback if still missing
    if not profile.name or profile.name.lower() in ["unknown", "all", "company"]:
        fallback_name = extract_common_term(truncated_text, pdf_path or "unknown.pdf")
        profile.name = fallback_name

    # AI Website Detection
    if not profile.website or profile.website.lower() in ["unknown", "n/a", ""]:
        ai_website = extract_website_with_ai(truncated_text, profile.name)
        if ai_website and ai_website.lower() != "unknown":
            profile.website = ai_website
            print(f"[Website Detection] AI detected: {profile.website}")

    # Assign deterministic ID
    profile.startup_id = sha1(profile.name.encode()).hexdigest()[:10]

    # Store the full deck in Chroma
    add_doc(profile.startup_id, deck_text)

    return profile

def extract_common_term_from_text(text: str, pdf_path: str) -> str:
    # Use regex to find frequent capitalized brand mentions
    matches = re.findall(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b", text)
    if matches:
        freq = {name: matches.count(name) for name in set(matches)}
        sorted_names = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        likely_term = sorted_names[0][0]
        if likely_term.lower() in ["all", "company", "unknown"]:
            return ""
        return likely_term
    return ""

def run_pitch_deck_chain(pdf_path: str) -> StartupProfile:
    """Legacy function that extracts text from PDF and calls the text-based version"""
    deck_text = pdf_to_text(Path(pdf_path))
    return run_pitch_deck_chain_with_text(deck_text, pdf_path=pdf_path)
