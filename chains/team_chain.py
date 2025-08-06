"""
Team Chain - Deterministic functions for team/executive data processing and formatting.
Moved from agents/founder_profiling_agent.py to separate deterministic logic from LLM orchestration.
"""

import re
import os
import json
import requests
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pathlib import Path
from dotenv import load_dotenv

from core.schemas import StartupProfile
from core.exa_utils import find_linkedin_url_with_exa

# --- LLM Post-Processing Setup ---
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

SYSTEM_PROMPT_TEAM = '''
You are a VC analyst tasked with creating a professional summary of a company's leadership team.
Your goal is to process raw web search text and return clean, structured JSON.

Your JSON output must follow this exact structure:
{
  "executives": [
    {
      "name": "Executive Name",
      "role": "Current Role",
      "linkedin": "https://www.linkedin.com/in/username (or null if not found)",
      "background": "A detailed 4-5 sentence professional background. Focus on experience, key achievements, and expertise. Do NOT include any of your own reasoning, meta-comments, or any text other than the background summary."
    }
  ]
}

Rules for the 'background' field:
- It must be a professional, narrative summary.
- It must NOT contain any "thinking process" or meta-commentary (e.g., "Based on my search...", "I found...").
- It must NOT be a direct copy-paste of raw search results.
- It must be well-written and ready for an investment memo.
'''

HUMAN_PROMPT_TEAM = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_TEAM),
    ("human", "Please process the following raw text for the executives at {company_name} and generate the structured JSON output.\n\nRaw Text:\n{raw_text}")
])

def llm_process_raw_bio(raw_bio_text: str, company_name: str, executive_name: str, executive_role: str) -> dict:
    """
    Uses an LLM to process a raw text bio into a clean, structured dictionary.
    """
    if not raw_bio_text:
        return {}
    
    # We create a more focused prompt here for a single executive
    prompt = f"Company: {company_name}\nExecutive: {executive_name} ({executive_role})\n\nRaw Text to process:\n{raw_bio_text}"
    
    try:
        llm_response_text = llm.invoke(HUMAN_PROMPT_TEAM.format(company_name=company_name, raw_text=prompt)).content.strip()
        
        json_match = re.search(r'\{.*\}', llm_response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            # Return the first executive found in the list
            if data.get("executives") and isinstance(data["executives"], list) and len(data["executives"]) > 0:
                return data["executives"][0]
    except Exception as e:
        print(f"[LLM Bio Processing] Failed for {executive_name}: {e}")
        
    return {}

# --- End LLM Post-Processing ---


def generate_team_section(profile: StartupProfile) -> str:
    """Generate team section with detailed executive information and optional ProxyCurl enrichment."""
    from core.perplexity_utils import search_perplexity
    from config import ENABLE_PROXYCURL_ENRICHMENT
    
    # First enrich with ProxyCurl if available and enabled
    if ENABLE_PROXYCURL_ENRICHMENT:
        try:
            from core.external_enrichment import enrich_executives_with_proxycurl
            # Enrich with ProxyCurl data as additional source
            profile = enrich_executives_with_proxycurl(profile)
        except Exception as e:
            print(f"[Team Section] ProxyCurl enrichment failed: {e}")
            # Continue without ProxyCurl enrichment
    
    lines = []
    execs = getattr(profile, 'executives', None) or []
    company_name = getattr(profile, 'name', '')
    
    # Improved deduplication and validation
    unique_execs = []
    seen_names = set()
    
    for exec in execs:
        if isinstance(exec, dict):
            name = exec.get('name', '').strip()
            role = exec.get('role', '').strip()
            
            if name and role:
                # Clean the name and role
                name = re.sub(r'[^\w\s\-\.]', '', name).strip()
                role = re.sub(r'[^\w\s\-\.]', '', role).strip()
                
                # Check for duplicates using fuzzy matching
                name_lower = name.lower()
                is_duplicate = False
                
                for existing in unique_execs:
                    existing_name = existing.get('name', '').lower()
                    if (name_lower == existing_name or 
                        name_lower in existing_name or 
                        existing_name in name_lower or
                        # Check for similar roles
                        (role.lower() in existing.get('role', '').lower() or 
                         existing.get('role', '').lower() in role.lower())):
                        is_duplicate = True
                        # Merge roles if it's the same person
                        if name_lower == existing_name:
                            existing_role = existing.get('role', '')
                            if role not in existing_role:
                                existing['role'] = f"{existing_role}/{role}"
                        break
                
                if not is_duplicate and name_lower not in seen_names:
                    unique_execs.append({
                        'name': name,
                        'role': role,
                        'linkedin': exec.get('linkedin', ''),
                        'bio': exec.get('bio', ''),
                        'background_summary': exec.get('background_summary', ''),
                        'proxycurl_formatted': exec.get('proxycurl_formatted', '')  # Add ProxyCurl data
                    })
                    seen_names.add(name_lower)
    
    # Sort by priority roles
    key_roles = ['founder', 'ceo', 'chief executive officer', 'cfo', 'chief financial officer', 'chairman', 'cto', 'chief technology officer']
    
    def get_role_priority(role):
        role_lower = role.lower()
        # Special handling for "Chief Executive Officer" vs "Deputy CEO"
        if 'chief executive officer' in role_lower:
            return 1  # Highest priority for CEO
        if 'deputy ceo' in role_lower:
            return 2  # Lower priority for Deputy CEO
        # Regular matching for other roles
        for i, key_role in enumerate(key_roles):
            if key_role in role_lower:
                return i
        return len(key_roles)  # Lower priority for other roles
    
    unique_execs.sort(key=lambda x: get_role_priority(x.get('role', '')))
    
    # Limit to top 3 executives
    unique_execs = unique_execs[:3]
    
    # Generate team section
    count = 0
    for exec in unique_execs:
        if count >= 3:  # Limit to 3 executives
            break
            
        name = exec.get('name', 'Unknown')
        role = exec.get('role', '').title()
        linkedin = exec.get('linkedin', '')
        bio = exec.get('bio', '')
        background_summary = exec.get('background_summary', '')
        
        # Format the executive entry - improved formatting like old_logic
        lines.append(f"**{name} – {role.upper()}**")
        
        if linkedin:
            lines.append(f"LinkedIn: {linkedin}")
        
        # Use bio if available, otherwise use background_summary
        if bio and len(bio.split()) > 5:
            # Clean up bio as well
            clean_bio = bio
            thinking_patterns = [
                r'Let me extract.*?\.',
                r'Okay, I need to.*?\.',
                r'First, from.*?\.',
                r'Based on.*?\.',
                r'According to.*?\.',
                r'Key points to include.*?\.',
                r'So putting this together.*?\.',
                r'Need to keep it concise.*?\.',
                r'Make sure to cite.*?\.',
                r'Check if all info.*?\.',
                r'Use the most relevant citations.*?\.'
            ]
            for pattern in thinking_patterns:
                clean_bio = re.sub(pattern, '', clean_bio, flags=re.DOTALL | re.IGNORECASE)
            clean_bio = clean_bio.strip()
            
            if clean_bio and len(clean_bio.split()) > 5:
                lines.append(f"Background: {clean_bio}")
        elif background_summary:
            # Clean up any remaining AI thinking patterns
            clean_summary = background_summary
            thinking_patterns = [
                r'Let me extract.*?\.',
                r'Okay, I need to.*?\.',
                r'First, from.*?\.',
                r'Based on.*?\.',
                r'According to.*?\.',
                r'Key points to include.*?\.',
                r'So putting this together.*?\.',
                r'Need to keep it concise.*?\.',
                r'Make sure to cite.*?\.',
                r'Check if all info.*?\.',
                r'Use the most relevant citations.*?\.'
            ]
            for pattern in thinking_patterns:
                clean_summary = re.sub(pattern, '', clean_summary, flags=re.DOTALL | re.IGNORECASE)
            clean_summary = clean_summary.strip()
            
            if clean_summary and len(clean_summary.split()) > 5:
                lines.append(f"Background: {clean_summary}")
        
        lines.append("")  # Add spacing between executives
        count += 1
    
    # If no executives found, provide a default message
    if not lines:
        lines.append("Executive team information requires additional research to provide detailed information.")
    
    return '\n'.join(lines)


def validate_and_clean_executives(executives: list) -> list:
    """Validate and clean executive data to remove invalid entries."""
    if not executives:
        return []
    
    cleaned = []
    for exec in executives:
        if not isinstance(exec, dict):
            continue
            
        name = exec.get('name', '').strip()
        role = exec.get('role', '').strip()
        
        # Skip entries with invalid names
        if not name or len(name) < 2 or name.lower() in ['unknown', 'n/a', 'none', '']:
            continue
            
        # Skip entries with invalid roles
        if not role or len(role) < 2 or role.lower() in ['unknown', 'n/a', 'none', '']:
            continue
        
        # Clean the name and role
        name = re.sub(r'[^\w\s\-\.]', '', name).strip()
        role = re.sub(r'[^\w\s\-\.]', '', role).strip()
        
        # Skip if cleaning resulted in empty strings
        if not name or not role:
            continue
        
        # Add to cleaned list
        cleaned.append({
            'name': name,
            'role': role,
            'linkedin': exec.get('linkedin', ''),
            'bio': exec.get('bio', ''),
            'background_summary': exec.get('background_summary', ''),
            'prior_exits': exec.get('prior_exits', [])
        })
    
    return cleaned


def ensure_executives_found(profile: StartupProfile) -> StartupProfile:
    """3-step executive extraction: 1) Deck, 2) CoreSignal (if available), 3) Web search"""
    execs = getattr(profile, 'executives', None) or []
    
    # Step 1: Validate and clean executives from deck
    execs = validate_and_clean_executives(execs)
    
    # If we have executives from the pitch deck, keep them
    if execs:
        print(f"[Team Search] ✅ Found {len(execs)} executives in pitch deck")
        profile.executives = execs
        return profile
    
    # Step 2: Try CoreSignal (but CoreSignal doesn't provide executive data, so skip)
    print(f"[Team Search] No executives found in deck for {profile.name}")
    
    # Step 3: Web search as last resort
    if profile.name:
        print(f"[Team Search] 🔍 Searching externally for {profile.name} executives...")
        execs = enrich_executives_with_perplexity(profile.name, [])
        if execs:
            # Validate the found executives
            execs = validate_and_clean_executives(execs)
            profile.executives = execs
            print(f"[Team Search] ✅ Found {len(execs)} executives via web search")
        else:
            print(f"[Team Search] ❌ No executives found via web search")
    
    # If we still have no executives, create a placeholder
    if not execs:
        print(f"[Team Search] 📝 Creating placeholder executive entry for {profile.name}")
        profile.executives = [{
            'name': 'Executive Team',
            'role': 'Management',
            'linkedin': '',
            'bio': f'The executive team at {profile.name} requires additional research to provide detailed information.'
        }]
    else:
        profile.executives = execs
    
    return profile


def get_linkedin_profile_exa(name, company_name=None):
    """Get LinkedIn profile URL using Exa and then get profile details using Perplexity."""
    from core.perplexity_utils import search_perplexity

    # Step 1: Use Exa to find the most accurate LinkedIn URL
    linkedin_url = find_linkedin_url_with_exa(name, company_name)

    if not linkedin_url:
        print(f"[Exa] No LinkedIn URL found for {name}")
        return None

    # Step 2: Use Perplexity to get the details from that specific URL
    profile_query = f"Provide a detailed professional background for the person with this LinkedIn profile: {linkedin_url}. Include their current role, key responsibilities, previous significant roles, and educational background."
    profile_details = search_perplexity(profile_query)

    if profile_details:
        return {
            'profile_url': linkedin_url,
            'summary': profile_details  # The full text from Perplexity
        }
    
    return {'profile_url': linkedin_url, 'summary': ''}


def format_linkedin_profile(data):
    """Format LinkedIn profile data for display."""
    if not data:
        return "No LinkedIn profile found."
    return f"""LinkedIn: {data.get('profile_url', 'N/A')}
Headline: {data.get('headline', 'N/A')}
Summary: {data.get('summary', 'N/A')}
Current Position: {data.get('occupation', 'N/A')}
"""

def generate_executive_background_summary(name: str, role: str, company_name: str, linkedin_data: dict = None) -> str:
    """
    Generates a high-quality executive background summary by synthesizing web search and LinkedIn data.
    """
    from core.perplexity_utils import search_perplexity
    
    print(f"[Bio Generation] Starting robust background generation for {name}.")

    # --- Step 1: Gather all available information ---
    # We will always perform a general web search to get a broad context.
    
    # General web search for a professional background
    general_query = f"Provide a detailed 3-4 sentence professional background for {name}, the {role} of {company_name}. Focus on key achievements, previous significant roles, and overall experience."
    general_search_results = search_perplexity(general_query)
    
    # Use LinkedIn data if it's available and seems useful
    linkedin_summary = ""
    if linkedin_data and linkedin_data.get('summary') and len(linkedin_data.get('summary', '').split()) > 10:
        linkedin_summary = linkedin_data.get('summary')
        print(f"[Bio Generation] Found LinkedIn summary for {name}.")

    # --- Step 2: Synthesize and Summarize with an LLM ---
    # The LLM will act as an analyst, synthesizing the best info from all sources.
    
    if not general_search_results and not linkedin_summary:
        print(f"[Bio Generation] No information found for {name} from any source. Using fallback.")
        return f"{name} serves as {role} at {company_name}. A detailed background could not be automatically generated and requires further research."
        
    synthesis_prompt = f"""
    You are a senior VC analyst. Your task is to write a concise and professional 4-5 sentence background summary for an executive based on the provided research.

    Executive: {name}
    Role: {role}
    Company: {company_name}

    Synthesize the information from the 'General Web Search' and 'LinkedIn Summary' below to create the best possible professional background. Prioritize the most relevant and impressive details.

    Rules:
    1.  The final summary MUST be a clean, well-written paragraph of 4-5 sentences.
    2.  Do NOT include any of your own meta-commentary (e.g., "Based on the search...").
    3.  Do NOT include any junk characters, citations, or incomplete fragments.
    4.  If the sources are weak or contradictory, use your judgment to produce the most likely and professional summary.

    ---
    General Web Search Results:
    {general_search_results or "No general information found."}
    ---
    LinkedIn Summary:
    {linkedin_summary or "No LinkedIn summary available."}
    ---

    Return ONLY the final, clean, professional background summary.
    """
    
    try:
        final_summary = llm.invoke(synthesis_prompt).content.strip()
        
        # --- Final Validation ---
        if final_summary and len(final_summary.split()) > 15 and "not available" not in final_summary.lower() and "cannot provide" not in final_summary.lower():
            print(f"[Bio Generation] Successfully generated synthesized bio for {name}.")
            return final_summary
        else:
            print(f"[Bio Generation] LLM synthesis failed or produced a short bio for {name}. Using fallback.")
            return f"{name} serves as {role} at {company_name}. A detailed background could not be automatically generated and requires further research."
            
    except Exception as e:
        print(f"[Bio Generation] An error occurred during LLM synthesis for {name}: {e}")
        return f"{name} serves as {role} at {company_name}. An error occurred during background generation, and further research is required."


def enrich_executives_with_perplexity(company_name, existing_execs):
    """
    Use Perplexity to find additional executives and their LinkedIn profiles if fewer than 3 are found.
    Improved version with better parsing and deduplication.
    """
    if not company_name:
        return existing_execs
    
    # If we already have 3+ executives, just return them
    if len(existing_execs) >= 3:
        return existing_execs
    
    from core.perplexity_utils import search_perplexity
    
    # Improved query for better results - focus on key executives
    query = f"List the current key executives of {company_name}. Return ONLY a clean list in this exact format:\nName (Role)\nName (Role)\nName (Role)\n\nOnly include CEO, founder, CFO, CTO, or Chairman. Limit to top 3 executives. No explanations, no extra text, just the clean list."
    result = search_perplexity(query)
    if not result:
        return existing_execs
    
    # Clean the result to remove AI thinking text
    cleaned_result = result
    
    # Remove common AI thinking patterns
    thinking_patterns = [
        r"Now, putting this together.*?",
        r"Okay, let me.*?",
        r"Based on.*?",
        r"According to.*?",
        r"Here are.*?",
        r"Let me.*?",
        r"I found.*?",
        r"The current.*?",
        r"Latest info.*?",
        r"2024-2025.*?",
        r"Step by step.*?",
        r"Tackle this query.*?",
    ]
    
    for pattern in thinking_patterns:
        cleaned_result = re.sub(pattern, "", cleaned_result, flags=re.IGNORECASE | re.DOTALL)
    
    # Enhanced parsing with better pattern matching
    execs = existing_execs.copy()
    seen_names = set()
    
    # First pass: extract from structured format
    for line in cleaned_result.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Skip lines that are clearly AI thinking or metadata
        skip_phrases = [
            'thinking', 'analysis', 'research', 'found', 'according', 'based', 
            'search result', 'dated', 'from search', 'step', 'tackle', 'okay',
            'let me', 'here are', 'latest info', '2024-2025', 'step by step',
            'from search results', 'dated 2025', 'dated 2024'
        ]
        if any(phrase in line.lower() for phrase in skip_phrases):
            continue
            
        # Skip lines that are just numbers, metadata, or unwanted patterns
        if (re.match(r'^\d+\.', line) or 
            re.match(r'^\[.*\]', line) or
            re.match(r'^From search result', line) or
            re.match(r'^\*\*.*\*\*$', line) or  # Just markdown bold
            'from search results' in line.lower() or
            'dated' in line.lower()):
            continue
            
        # Clean the line - remove unwanted formatting
        line = re.sub(r'^\d+\.\s*', '', line)  # Remove "1. " at start
        line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)  # Remove markdown bold
        line = re.sub(r'\([^)]*from[^)]*\)', '', line)  # Remove "from search results"
        line = re.sub(r'\([^)]*dated[^)]*\)', '', line)  # Remove "dated 2025-01-01"
        
        # Try multiple patterns for parsing - very strict
        patterns = [
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\(([A-Z\s]+)\)$",  # Name (Role)
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[-–]\s*([A-Z\s]+)$",  # Name - Role
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*:\s*([A-Z\s]+)$",  # Name: Role
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                role = match.group(2).strip()
                linkedin = ""  # No LinkedIn in new strict patterns
                
                # Additional cleaning
                name = re.sub(r'^\*\*|\*\*$', '', name)  # Remove remaining **
                role = re.sub(r'^\*\*|\*\*$', '', role)  # Remove remaining **
                
                # Validate the extracted data - very strict
                if (name and len(name) > 2 and 
                    role and len(role) > 2 and
                    name.lower() not in ['unknown', 'n/a', 'none', 'name', 'role'] and
                    role.lower() not in ['unknown', 'n/a', 'none', 'name', 'role'] and
                    not name.isdigit() and  # Not just numbers
                    not role.isdigit() and  # Not just numbers
                    not re.match(r'^[A-Z\s]+$', name) and  # Not just uppercase letters
                    not re.match(r'^[A-Z\s]+$', role)):    # Not just uppercase letters
                    
                    # Check for duplicates
                    name_lower = name.lower()
                    if name_lower not in seen_names:
                        execs.append({
                            'name': name,
                            'role': role,
                            'linkedin': linkedin,
                            'bio': ''
                        })
                        seen_names.add(name_lower)
                        print(f"[Team Search] ✅ Found executive: {name} ({role})")
                        
                        # Limit to top 3 executives
                        if len(execs) >= 3:
                            break
                break
    
    # If we still don't have executives after parsing, try a simpler approach
    if len(execs) == len(existing_execs):
        print(f"[Team Search] No executives found via Perplexity, trying simpler query...")
        simple_query = f"Current key executives of {company_name}. Return ONLY:\nName (CEO)\nName (CFO)\nName (CTO)\n\nNo explanations, just the clean list."
        simple_result = search_perplexity(simple_query)
        if simple_result:
            # Try to extract just names from the simple result
            lines = simple_result.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 5:
                    # Look for name patterns - more strict
                    name_match = re.search(r'([A-Z][a-z]+ [A-Z][a-z]+)', line)
                    if name_match:
                        name = name_match.group(1)
                        # Try to extract role
                        role_match = re.search(r'(CEO|CFO|CTO|Founder|Chief|President)', line, re.IGNORECASE)
                        role = role_match.group(1) if role_match else "Executive"
                        
                        # Additional validation
                        if (name.lower() not in seen_names and
                            name.lower() not in ['restaurant business', 'company name', 'unknown'] and
                            not re.match(r'^[A-Z\s]+$', name)):  # Not just uppercase letters
                            
                            execs.append({
                                'name': name,
                                'role': role,
                                'linkedin': '',
                                'bio': ''
                            })
                            seen_names.add(name.lower())
                            print(f"[Team Search] ✅ Found executive via simple query: {name} ({role})")
                            
                            # Limit to top 3 executives
                            if len(execs) >= 3:
                                break
    
    return execs

def run_team_chain(profile: StartupProfile) -> StartupProfile:
    """Run team chain to process and validate executive data."""
    existing_execs = getattr(profile, 'executives', []) or []
    print(f"[Team Chain] Found {len(existing_execs)} executives from PDF extraction")

    if not existing_execs:
        print("[Team Chain] No executives found in PDF - falling back to web search")
        profile = ensure_executives_found(profile)
        existing_execs = getattr(profile, 'executives', []) or []

    if not existing_execs:
        print("[Team Chain] No executives found after web search. Aborting.")
        return profile

    enriched_execs = []
    
    key_roles = ['founder', 'ceo', 'chief executive officer', 'cfo', 'chief financial officer', 'chairman', 'cto', 'chief technology officer']
    
    def get_role_priority(role):
        role_lower = role.lower()
        if 'chief executive officer' in role_lower: return 1
        if 'deputy ceo' in role_lower: return 2
        for i, key_role in enumerate(key_roles):
            if key_role in role_lower:
                return i
        return len(key_roles)

    sorted_execs = sorted(existing_execs, key=lambda x: get_role_priority(x.get('role', '')) if isinstance(x, dict) else len(key_roles))
    top_3_execs = sorted_execs[:3]

    for i, exec_data in enumerate(top_3_execs):
        if isinstance(exec_data, dict):
            name = exec_data.get('name', '')
            role = exec_data.get('role', '')
            
            if name and name.lower() not in ['unknown', 'n/a', 'none']:
                print(f"[Team Chain] Enriching data for executive {i+1}: {name} ({role})")
                
                enriched_exec = exec_data.copy()
                
                linkedin_data = get_linkedin_profile_exa(name, profile.name)
                
                background_summary = generate_executive_background_summary(name, role, profile.name, linkedin_data)
                
                enriched_exec['background_summary'] = background_summary
                if linkedin_data and linkedin_data.get('profile_url'):
                    enriched_exec['linkedin'] = linkedin_data.get('profile_url')
                
                enriched_exec['bio'] = background_summary
                
                enriched_execs.append(enriched_exec)
            else:
                enriched_execs.append(exec_data)
        else:
            enriched_execs.append(exec_data)

    for exec_data in existing_execs[3:]:
        enriched_execs.append(exec_data)
        
    profile.executives = enriched_execs
    
    return profile
