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

def get_smart_team_context(text):
    """Extract team-relevant sections from text for better executive detection"""
    import re
    
    # High-priority team keywords (these get more context)
    high_priority_keywords = [
        'founder', 'ceo', 'cfo', 'cto', 'chief', 'executive', 'president',
        'founder', 'co-founder', 'cofounder', 'founders', 'management',
        'team', 'leadership', 'board', 'director', 'chairman', 'chairwoman'
    ]
    
    # Medium-priority keywords (name patterns)
    medium_priority_keywords = [
        'mr.', 'ms.', 'dr.', 'professor', 'phd', 'mba', 'linkedin',
        'experience', 'background', 'previously', 'former', 'current'
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
    if len(combined_context) < 3000:
        # Add the beginning and end of the text (where team info often is)
        combined_context += '\n\n' + text[:4000] + '\n\n' + text[-4000:]
    
    # Limit to 8k chars total for efficiency
    return combined_context[:8000]

SYSTEM = """
You are a top-tier VC investment analyst. Extract the following fields as JSON:
- name
- founder_name
- sector
- website
- funding_stage
- executives: a list of key executives found in the text. Look for team sections, leadership sections, or any area that lists company executives. For each executive, include name, role, LinkedIn if available, and a list of prior exits with company name and link if available. Common roles to look for: CEO, Chief Executive Officer, Founder, Co-Founder, CFO, Chief Financial Officer, CTO, Chief Technology Officer, Chairman, COO, Chief Operating Officer, Head of Product, Chief Risk Officer.

IMPORTANT: For executives, DO NOT duplicate the same person. If someone appears multiple times with different roles, combine them into one entry with all roles. For example, if "Drew Houston" appears as both "CEO" and "Founder", create one entry: {{"name": "Drew Houston", "role": "CEO/Founder"}}

EXAMPLES OF EXECUTIVE FORMATS TO RECOGNIZE:
- "Tom Blomfield\nChief Executive Officer" → {{"name": "Tom Blomfield", "role": "Chief Executive Officer"}}
- "Paul Rippon\nDeputy CEO & Co-Founder" → {{"name": "Paul Rippon", "role": "Deputy CEO & Co-Founder"}}
- "Gary Dolman\nCFO & Co-Founder" → {{"name": "Gary Dolman", "role": "CFO & Co-Founder"}}

CRITICAL: If NO executive information is found in the text (no names, no roles mentioned), return an EMPTY executives array: "executives": []. Do NOT make up or infer executive information.

EXECUTIVE EXTRACTION RULES:
1. Only extract executives that are CLEARLY mentioned with both name and role
2. Look for patterns like: "Name - Role", "Name (Role)", "Name, Role", "Role: Name", "Name\nRole", "Role\nName"
3. Also look for executives listed in team sections with names and roles on separate lines
4. Common executive roles to extract: CEO, Chief Executive Officer, Founder, Co-Founder, CFO, Chief Financial Officer, CTO, Chief Technology Officer, Chairman, COO, Chief Operating Officer, Head of Product, Chief Risk Officer
5. Do NOT extract partial information or inferred roles
6. Do NOT include generic text like "from search results" or "dated 2025-01-01"
7. Clean names: remove numbers, extra text, and formatting artifacts
8. If you see a team section with multiple executives, extract all clearly identified ones

For the 'name' field: 
1. Look for the official company name that appears most frequently in the text
2. Common patterns: "Company Name Inc", "Company Name Corp", "Company Name Technologies", "Company Name"
3. For well-known companies, use their official name (e.g., "Shopify", "Tesla", "Uber")
4. Do not return slogans, products, or generic terms like "Company" or "All"
5. If the company name is clearly stated, use it exactly as written
6. If not explicitly stated, return "unknown"

For the 'founder_name' field:
1. Look for founder names in the text
2. If no founder is mentioned, return "unknown"
3. Do NOT make up founder names

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
HUMAN = "Pitch-deck text (team-relevant sections):\n```markdown\n{deck}\n```"
PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", HUMAN)])


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def pdf_to_text(path: Path) -> str:
    """Concatenate text from every page of a PDF."""
    with pdfplumber.open(path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(pages)


def extract_company_name_with_ai(text: str, evaluator=None) -> str:
    """Use AI to detect the company name from text"""
    try:
        ai_prompt = f"""
        Analyze the following text and identify the official company name.
        
        Rules:
        1. Look for the company that this pitch deck is about
        2. Return ONLY the company name, not slogans or products
        3. For well-known companies, use their official name (e.g., "Shopify", "Tesla", "Uber")
        4. If multiple companies are mentioned, identify the main company this deck is for
        5. Look for company names in headers, titles, and prominent positions
        6. If unclear, return "unknown"
        
        IMPORTANT: This is a pitch deck, so the company name should be prominently featured.
        Look for the company that is presenting or being analyzed.
        
        Text to analyze:
        {text[:3000]}
        
        Return ONLY the company name:
        """
        
        response = llm.invoke(ai_prompt)
        company_name = response.content.strip().strip('"').strip("'")
        
        # Track token usage
        if evaluator and hasattr(response, 'usage'):
            input_tokens = getattr(response.usage, 'prompt_tokens', 0)
            output_tokens = getattr(response.usage, 'completion_tokens', 0)
            evaluator.log_agent_tokens("COMPANY NAME DETECTION", input_tokens, output_tokens, "gpt-4o")
        
        # Clean up the response
        if company_name.lower() in ['unknown', 'none', 'n/a', '']:
            return "unknown"
        
        return company_name
    except Exception as e:
        print(f"[AI Company Detection] Error: {e}")
        return "unknown"


def extract_website_with_ai(text: str, company_name: str = None, evaluator=None) -> str:
    """Use AI to detect the company website from text"""
    try:
        # Well-known company website mappings
        known_companies = {
            'snapchat': 'snapchat.com',
            'shopify': 'shopify.com',
            'tesla': 'tesla.com',
            'airbnb': 'airbnb.com',
            'uber': 'uber.com',
            'dropbox': 'dropbox.com',
            'linkedin': 'linkedin.com',
            'twitter': 'twitter.com',
            'facebook': 'facebook.com',
            'instagram': 'instagram.com',
            'tiktok': 'tiktok.com',
            'netflix': 'netflix.com',
            'spotify': 'spotify.com',
            'zoom': 'zoom.us',
            'slack': 'slack.com',
            'discord': 'discord.com',
            'github': 'github.com',
            'stripe': 'stripe.com',
            'square': 'square.com',
            'coinbase': 'coinbase.com',
            'robinhood': 'robinhood.com',
            'peloton': 'onepeloton.com',
            'doordash': 'doordash.com',
            'lyft': 'lyft.com',
            'pinterest': 'pinterest.com',
            'reddit': 'reddit.com',
            'twitch': 'twitch.tv',
            'youtube': 'youtube.com',
            'amazon': 'amazon.com',
            'google': 'google.com',
            'microsoft': 'microsoft.com',
            'apple': 'apple.com',
            'meta': 'meta.com',
            'alphabet': 'alphabet.com'
        }
        
        # Check if it's a well-known company first
        if company_name:
            company_lower = company_name.lower().replace(' ', '').replace('-', '').replace('_', '')
            for known_name, known_website in known_companies.items():
                if known_name in company_lower or company_lower in known_name:
                    print(f"[AI Website Detection] Using known website for {company_name}: {known_website}")
                    return f"https://{known_website}"
        
        ai_prompt = f"""
        Analyze the following text and identify the official company website.
        
        Rules:
        1. Look for the main company website URL
        2. Common patterns: www.companyname.com, companyname.com, https://companyname.com
        3. For well-known companies, use their official website (e.g., shopify.com, tesla.com)
        4. If multiple URLs are mentioned, identify the main company website
        5. Avoid admin URLs, merchant URLs, or social media URLs
        6. If unclear, return "unknown"
        
        Company name: {company_name or "unknown"}
        Text to analyze:
        {text[:3000]}
        
        Return ONLY the website URL (without http/https if not in text):
        """
        
        response = llm.invoke(ai_prompt)
        website = response.content.strip().strip('"').strip("'")
        
        # Track token usage
        if evaluator and hasattr(response, 'usage'):
            input_tokens = getattr(response.usage, 'prompt_tokens', 0)
            output_tokens = getattr(response.usage, 'completion_tokens', 0)
            evaluator.log_agent_tokens("WEBSITE DETECTION", input_tokens, output_tokens, "gpt-4o")
        
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


def extract_sector_with_ai(text: str, evaluator=None) -> str:
    """Use AI to detect the business sector from text"""
    try:
        ai_prompt = f"""
        Analyze the following text and identify the business sector/industry.
        
        Rules:
        1. Look for the main business sector this company operates in
        2. Be specific about the sector (e.g., "ecommerce", "fintech", "healthtech", "battery technology")
        3. Avoid generic terms like "technology" or "software" unless that's the specific focus
        4. Look for sector mentions in the pitch deck content
        5. If unclear, return "unknown"
        
        Common sectors to look for:
        - ecommerce, fintech, healthtech, edtech, proptech, insurtech
        - battery technology, electric vehicles, renewable energy
        - ai/ml, cybersecurity, biotech, medtech, agtech, cleantech
        - retail, manufacturing, services, consulting
        
        Text to analyze:
        {text[:3000]}
        
        Return ONLY the sector name:
        """
        
        response = llm.invoke(ai_prompt)
        sector = response.content.strip().strip('"').strip("'")
        
        # Track token usage
        if evaluator and hasattr(response, 'usage'):
            input_tokens = getattr(response.usage, 'prompt_tokens', 0)
            output_tokens = getattr(response.usage, 'completion_tokens', 0)
            evaluator.log_agent_tokens("SECTOR DETECTION", input_tokens, output_tokens, "gpt-4o")
        
        # Clean up the response
        if sector.lower() in ['unknown', 'none', 'n/a', '']:
            return "unknown"
        
        return sector
    except Exception as e:
        print(f"[AI Sector Detection] Error: {e}")
        return "unknown"


def extract_financial_metrics_with_ai(text: str, evaluator=None) -> dict:
    """Use AI to extract financial and business metrics from pitch deck text"""
    try:
        ai_prompt = f"""
        Analyze the following pitch deck text and extract key financial and business metrics.
        
        Look for and extract EXACT values from the text:
        1. Total merchants/users (e.g., "200,000+ merchants")
        2. Gross Merchandise Volume (GMV) (e.g., "$4.9B", "$3.8B")
        3. Revenue figures (e.g., "$195.0M", "$135.1M")
        4. Monthly Recurring Revenue (MRR) (e.g., "$9.8M", "$1.1M")
        5. Employee count (e.g., "10,000+ employees")
        6. Target market size (e.g., "$46B TAM", "$10B TAM")
        7. Growth rates (e.g., "85% CAGR", "+86%", "+93%")
        8. Business model details (e.g., "subscription fees", "transaction fees")
        9. Funding amounts (e.g., "$187.3M Series I")
        10. Valuation figures (e.g., "$1.2B valuation")
        11. Gross Profit figures (e.g., "$75.8M", "$62.1M")
        
        CRITICAL: Extract the MOST RECENT and LARGEST values when multiple years are shown.
        For example:
        - If revenue shows "$195.0M" (2015) and "$135.1M" (2014), use "$195.0M"
        - If GMV shows "$4.9B" (9 MO 2015) and "$3.8B" (2014), use "$4.9B"
        - If MRR shows "$9.8M" (Q1 2015) and "$1.1M" (Q1 2012), use "$9.8M"
        
        Return ONLY a JSON object with these fields:
        {{
            "total_merchants": "number or description",
            "total_gmv": "amount or description", 
            "revenue": "amount or description",
            "mrr": "amount or description",
            "employees": "number or description",
            "target_market": "size or description",
            "growth_rate": "percentage or description",
            "business_model": "description of revenue streams",
            "latest_funding": "amount and round if mentioned",
            "valuation": "amount if mentioned",
            "gross_profit": "amount or description"
        }}
        
        If a metric is not found, use "unknown". Be specific with numbers when available.
        
        Text to analyze:
        {text[:4000]}
        """
        
        response = llm.invoke(ai_prompt)
        result = response.content.strip()
        
        # Track token usage
        if evaluator and hasattr(response, 'usage'):
            input_tokens = getattr(response.usage, 'prompt_tokens', 0)
            output_tokens = getattr(response.usage, 'completion_tokens', 0)
            evaluator.log_agent_tokens("FINANCIAL METRICS EXTRACTION", input_tokens, output_tokens, "gpt-4o")
        
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
    """Deduplicate executives by name, merging roles for the same person."""
    if not executives:
        return []
    
    unique_execs = []
    seen_names = set()
    
    for exec in executives:
        if not isinstance(exec, dict):
            continue
            
        name = exec.get('name', '').strip()
        role = exec.get('role', '').strip()
        
        if not name or not role:
            continue
        
        # Clean the name
        name = re.sub(r'[^\w\s\-\.]', '', name).strip()
        name_lower = name.lower()
        
        # Check for duplicates using fuzzy matching
        is_duplicate = False
        for existing in unique_execs:
            existing_name = existing.get('name', '').lower()
            if (name_lower == existing_name or 
                name_lower in existing_name or 
                existing_name in name_lower):
                is_duplicate = True
                # Merge roles if it's the same person
                existing_role = existing.get('role', '')
                if role not in existing_role:
                    existing['role'] = f"{existing_role}/{role}"
                # Merge other fields
                if not existing.get('linkedin') and exec.get('linkedin'):
                    existing['linkedin'] = exec.get('linkedin')
                if not existing.get('bio') and exec.get('bio'):
                    existing['bio'] = exec.get('bio')
                break
        
        if not is_duplicate and name_lower not in seen_names:
            unique_execs.append({
                'name': name,
                'role': role,
                'linkedin': exec.get('linkedin', ''),
                'bio': exec.get('bio', ''),
                'prior_exits': exec.get('prior_exits', [])
            })
            seen_names.add(name_lower)
    
    # Sort by priority roles
    key_roles = ['founder', 'ceo', 'chief executive officer', 'cfo', 'chief financial officer', 'chairman', 'cto', 'chief technology officer']
    
    def get_role_priority(role):
        role_lower = role.lower()
        for i, key_role in enumerate(key_roles):
            if key_role in role_lower:
                return i
        return len(key_roles)  # Lower priority for other roles
    
    unique_execs.sort(key=lambda x: get_role_priority(x.get('role', '')))
    
    return unique_execs


def extract_common_term(text: str, pdf_path: str, evaluator=None) -> str:
    """Enhanced company name extraction with AI as primary method"""
    
    # PRIMARY: AI detection first
    ai_name = extract_company_name_with_ai(text, evaluator)
    if ai_name and ai_name.lower() != "unknown":
        print(f"[Company Detection] AI detected: {ai_name}")
        return ai_name
    
    # SECONDARY: Enhanced regex-based extraction with better filtering
    company_patterns = [
        r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Company|Co|Technologies|Tech|Systems|Solutions))\b",  # With company suffixes
        r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*\s+(?:International|Global|Worldwide|Enterprises|Group|Partners))\b",  # With business suffixes
        r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+){2,})\b",  # Multi-word names (2+ words)
        r"\b([A-Z][a-z]{3,}(?:\s[A-Z][a-z]+)*)\b",  # Longer single words (4+ chars)
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
            if len(name) > 3:  # Avoid very short names
                freq[name] = freq.get(name, 0) + 1
        
        # Enhanced filter out common/generic terms
        generic_terms = {
            "all", "company", "unknown", "the", "and", "for", "with", "from", "this", "that", 
            "have", "will", "been", "they", "their", "them", "were", "said", "each", "which",
            "there", "were", "been", "other", "about", "many", "then", "them", "these", "so",
            "some", "her", "would", "make", "like", "into", "him", "time", "two", "more", "go",
            "no", "way", "could", "my", "than", "first", "been", "call", "who", "its", "now",
            "find", "long", "down", "day", "did", "get", "come", "made", "may", "part",
            # PDF-specific terms
            "page", "dashboard", "report", "overview", "summary", "analysis", "chart", "graph",
            "table", "figure", "section", "chapter", "slide", "presentation", "deck",
            # Common UI terms
            "menu", "button", "link", "search", "filter", "sort", "view", "edit", "delete",
            "save", "cancel", "ok", "yes", "no", "back", "next", "previous", "home",
            # Common business terms
            "business", "market", "product", "service", "customer", "revenue", "profit",
            "growth", "sales", "marketing", "finance", "investment", "strategy", "plan",
            "goal", "target", "objective", "mission", "vision", "value", "benefit"
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
def run_pitch_deck_chain_with_text(deck_text: str, profile: StartupProfile = None, pdf_path: str = None, evaluator=None) -> StartupProfile:
    """Run pitch deck analysis using extracted text directly"""
    if profile is None:
        profile = StartupProfile()
    
    truncated_text = deck_text[:5000]

    # Safe string checking function
    def is_valid_string(value, invalid_values=["unknown", "all", "company", "n/a", ""]):
        if not value:
            return False
        if isinstance(value, list):
            return False
        if not isinstance(value, str):
            return False
        return value.lower() not in invalid_values

    # PRIMARY: Try AI company name detection first (only if not already detected)
    if not profile.name or not is_valid_string(profile.name):
        print("[Company Detection] Starting AI detection...")
        ai_company_name = extract_company_name_with_ai(truncated_text, evaluator)
        
        if ai_company_name and ai_company_name.lower() != "unknown":
            print(f"[Company Detection] AI successfully detected: {ai_company_name}")
            profile.name = ai_company_name
        else:
            print("[Company Detection] AI detection failed")
    
    # ALWAYS run JSON extraction to get executives and other data
    print("[JSON Extraction] Running JSON extraction for executives and other data...")
    # Use smart team context for better executive detection
    team_context = get_smart_team_context(truncated_text)
    prompt = PROMPT.format(deck=team_context)
    response = llm.invoke(prompt)
    txt = response.content.strip()
    
    # Track token usage for main pitch deck extraction
    if evaluator and hasattr(response, 'usage'):
        input_tokens = getattr(response.usage, 'prompt_tokens', 0)
        output_tokens = getattr(response.usage, 'completion_tokens', 0)
        evaluator.log_agent_tokens("PITCH DECK MAIN EXTRACTION", input_tokens, output_tokens, "gpt-4o")

    # Extract JSON from LLM output
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1 or last < first:
        print("[Warning] No JSON object found, falling back to extraction")
        if not profile.name or not is_valid_string(profile.name):
            fallback_name = extract_common_term(truncated_text, pdf_path or "unknown.pdf", evaluator)
            profile.name = fallback_name
    else:
        try:
            json_str = txt[first : last + 1]
            raw = json.loads(json_str)

            # Only update company name if we don't already have a good one
            if not profile.name or not is_valid_string(profile.name):
                if not raw.get("name") or not is_valid_string(raw.get("name")):
                    fallback_name = extract_common_term(truncated_text, pdf_path or "unknown.pdf", evaluator)
                    raw["name"] = fallback_name
                profile.name = raw.get("name", profile.name)

            if not raw.get("founder_name") or not is_valid_string(raw.get("founder_name")):
                raw["founder_name"] = "unknown"

            # Update profile with extracted data
            for key, value in raw.items():
                if hasattr(profile, key) and value:
                    setattr(profile, key, value)
            
            # Extract additional metrics using AI
            additional_metrics = extract_financial_metrics_with_ai(truncated_text, evaluator)
            for key, value in additional_metrics.items():
                if hasattr(profile, key) and value and is_valid_string(value):
                    # Consolidate with existing data - prefer more specific/recent values
                    existing_value = getattr(profile, key, None)
                    if existing_value and is_valid_string(existing_value):
                        # Keep the more specific value
                        if len(str(value)) > len(str(existing_value)) or "million" in str(value).lower() or "billion" in str(value).lower():
                            setattr(profile, key, value)
                            print(f"[AI Metrics] Updated {key} from '{existing_value}' to '{value}'")
                        else:
                            print(f"[AI Metrics] Keeping existing {key}: '{existing_value}' (more specific than '{value}')")
                    else:
                        setattr(profile, key, value)
                        print(f"[AI Metrics] Set {key} = {value}")
                elif key == "total_merchants" and hasattr(profile, "merchants_count") and value and is_valid_string(value):
                    profile.merchants_count = value
                    print(f"[AI Metrics] Set merchants_count = {value}")
                elif key == "total_gmv" and hasattr(profile, "gmv") and value and is_valid_string(value):
                    profile.gmv = value
                    print(f"[AI Metrics] Set gmv = {value}")
                elif key == "target_market" and hasattr(profile, "TAM") and value and is_valid_string(value):
                    profile.TAM = value
                    print(f"[AI Metrics] Set TAM = {value}")
                elif key == "growth_rate" and hasattr(profile, "growth_rate") and value and is_valid_string(value):
                    profile.growth_rate = value
                    print(f"[AI Metrics] Set growth_rate = {value}")
                elif key == "latest_funding" and hasattr(profile, "latest_round_amount") and value and is_valid_string(value):
                    profile.latest_round_amount = value
                    print(f"[AI Metrics] Set latest_round_amount = {value}")
                elif key == "valuation" and hasattr(profile, "valuation") and value and is_valid_string(value):
                    profile.valuation = value
                    print(f"[AI Metrics] Set valuation = {value}")
                elif key == "gross_profit" and hasattr(profile, "gross_profit") and value and is_valid_string(value):
                    profile.gross_profit = value
                    print(f"[AI Metrics] Set gross_profit = {value}")
            
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
            if not profile.name or not is_valid_string(profile.name):
                fallback_name = extract_common_term(truncated_text, pdf_path or "unknown.pdf", evaluator)
                profile.name = fallback_name

    # Fallback if still missing
    if not profile.name or not is_valid_string(profile.name):
        fallback_name = extract_common_term(truncated_text, pdf_path or "unknown.pdf", evaluator)
        profile.name = fallback_name

    # AI Sector Detection
    if not profile.sector or not is_valid_string(profile.sector):
        ai_sector = extract_sector_with_ai(truncated_text, evaluator)
        if ai_sector and is_valid_string(ai_sector):
            profile.sector = ai_sector
            print(f"[Sector Detection] AI detected: {profile.sector}")
    
    # AI Website Detection
    if not profile.website or not is_valid_string(profile.website):
        ai_website = extract_website_with_ai(truncated_text, profile.name, evaluator)
        if ai_website and is_valid_string(ai_website):
            profile.website = ai_website
            profile._ai_detected_website = ai_website  # Track AI detection
            print(f"[Website Detection] AI detected: {profile.website}")

    # Assign deterministic ID
    profile.startup_id = sha1(profile.name.encode()).hexdigest()[:10]
    
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
