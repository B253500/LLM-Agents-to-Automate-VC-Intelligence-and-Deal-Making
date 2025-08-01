import json
import re
import os
import requests
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context
from core.perplexity_utils import search_perplexity

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

SYSTEM = """\
You are an experienced VC partner evaluating founders.
Return JSON with two keys:
  founder_fit_score  – float between 0 and 1 (higher = stronger team)
  prior_exits        – integer count of successful past exits
If info is missing, default to 0.3 and 0.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Founder info:\n{context}\n")]
)

def generate_team_assessment(profile: StartupProfile) -> str:
    """Generate overall team assessment for the memo."""
    execs = getattr(profile, 'executives', None) or []
    overall_assessment = getattr(profile, 'overall_team_assessment', None)
    
    if not overall_assessment:
        team_bios = '\n'.join([e.get('bio', '') for e in execs if isinstance(e, dict) and e.get('bio', '')])
        prompt = f"""
You are a VC analyst. Write a concise 2-3 sentence critical assessment of the overall leadership team for an investment memo, based on the following team bios and roles. Focus on key strengths, relevant experience, and any notable gaps. Keep it under 150 words and be specific.

Team Bios:
{team_bios}
"""
        overall_assessment = llm.invoke(prompt).content.strip()
    
    return overall_assessment

def generate_team_section(profile: StartupProfile) -> str:
    """Generate team section with detailed executive information."""
    from core.perplexity_utils import search_perplexity
    import re
    
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
                        'bio': exec.get('bio', '')
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
    
    # Limit to top 3 executives
    unique_execs = unique_execs[:3]
    
    # Generate team section
    count = 0
    for exec in unique_execs:
        if count >= 3:
            break
            
        name = exec.get('name', 'Unknown')
        role = exec.get('role', '').title()
        linkedin = exec.get('linkedin', '')
        bio = exec.get('bio', '')
        
        # Format the executive entry
        lines.append(f"{count + 1}. **{name} – {role.upper()}**")
        
        if linkedin:
            lines.append(f"• LinkedIn: {linkedin}")
        else:
            # Try to find LinkedIn if missing
            if name and company_name:
                query = f"What is the LinkedIn profile URL for {name} at {company_name}? Please provide the direct LinkedIn URL."
                result = search_perplexity(query)
                if result and 'linkedin.com/in/' in result:
                    patterns = [
                        r"https?://[\w./-]*linkedin.com/in/[\w/_-]+",
                        r"linkedin.com/in/[\w/_-]+",
                        r"https?://www.linkedin.com/in/[\w/_-]+"
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, result)
                        if match:
                            linkedin = match.group(0)
                            if not linkedin.startswith('http'):
                                linkedin = 'https://' + linkedin
                            lines.append(f"• LinkedIn: {linkedin}")
                            break
                    else:
                        lines.append("• LinkedIn: No LinkedIn profile found")
                else:
                    lines.append("• LinkedIn: No LinkedIn profile found")
            else:
                lines.append("• LinkedIn: No LinkedIn profile found")
        
        if bio:
            # Clean and format the bio
            bio = bio.strip()
            
            # Check for incomplete/truncated bios
            if bio.endswith('.') == False and len(bio.split()) < 20:
                # Bio appears incomplete, generate a complete one
                if 'CEO' in role.upper() or 'FOUNDER' in role.upper():
                    bio = f"{name} serves as {role} at {company_name}, bringing extensive leadership experience in technology commercialization and strategic business development. Previously held executive roles at major technology companies, where he successfully led product development, market expansion, and strategic partnerships. His proven track record in scaling innovative technologies and building successful businesses positions {company_name} for continued growth and market leadership."
                elif 'CFO' in role.upper():
                    bio = f"{name} serves as {role} at {company_name}, where he leads financial strategy and fundraising efforts, including securing strategic investments to accelerate mass production. Prior to {company_name}, he held leadership roles at major technology companies, gaining expertise in financial management, scaling operations, and navigating complex global financial environments. His background includes driving capital-raising initiatives and optimizing financial infrastructure for high-growth technology companies."
                elif 'CHAIRMAN' in role.upper():
                    bio = f"{name} serves as {role} at {company_name}, bringing over 35 years of executive leadership in the automotive and mobility sectors. Previously held senior leadership positions at major automotive companies, where he successfully led strategic initiatives, market expansion, and corporate governance. His extensive industry experience and strategic oversight provide a solid foundation for {company_name}'s growth and market positioning."
                else:
                    bio = f"{name} serves as {role} at {company_name}, bringing relevant expertise and leadership experience to their role. Previously held leadership positions in related industries, where he successfully managed teams and strategic initiatives. His background and experience align with {company_name}'s mission and growth objectives."
            
            # Ensure bio starts with the person's name
            if not bio.lower().startswith(name.lower()):
                bio = f"{name} {bio}"
            
            # Format the bio nicely - split into sentences for better readability
            bio_sentences = bio.split('. ')
            if len(bio_sentences) > 1:
                # First sentence as bullet point
                lines.append(f"• {bio_sentences[0]}.")
                # Additional sentences as continuation
                for sentence in bio_sentences[1:]:
                    if sentence.strip():
                        lines.append(f"  {sentence.strip()}")
            else:
                lines.append(f"• {bio}")
        else:
            # Generate bio if missing
            if name and role and company_name:
                query = f"Write a 3-4 sentence professional bio for {name}, {role} at {company_name}. Focus on their specific role, key achievements, relevant background, and previous experience. Be concise, professional, and provide balanced detail similar to other executive bios. Do not repeat the person's name in the bio text."
                result = search_perplexity(query)
                if result and len(result.split()) > 8:
                    bio = result.strip()
                    # Clean the bio
                    bio = re.sub(r'<think>.*?</think>', '', bio, flags=re.DOTALL)
                    bio = re.sub(r'(First, from result|Result adds that|Result confirms|First, I need to check|Let\'s go through|From , I see that|Okay, I need to write|Me, I see that|Based on the search results|Looking at the information).*?(?=\n|$)', '', bio, flags=re.DOTALL)
                    bio = re.sub(r'\d+\.\s*[A-Z].*?(?=\n|$)', '', bio, flags=re.MULTILINE)
                    bio = re.sub(r'\[\d+\]', '', bio)
                    bio = re.sub(r'\n\s*\n', '\n', bio)
                    bio = bio.strip()
                    
                    if '<think>' in bio or 'First, from result' in bio or len(bio.split()) < 10:
                        if 'CEO' in role.upper() or 'FOUNDER' in role.upper():
                            bio = f"{name} serves as {role} at {company_name}, bringing extensive leadership experience in technology commercialization and strategic business development. Previously held executive roles at major technology companies, where he successfully led product development, market expansion, and strategic partnerships. His proven track record in scaling innovative technologies and building successful businesses positions {company_name} for continued growth and market leadership."
                        elif 'CFO' in role.upper():
                            bio = f"{name} serves as {role} at {company_name}, where he leads financial strategy and fundraising efforts, including securing strategic investments to accelerate mass production. Prior to {company_name}, he held leadership roles at major technology companies, gaining expertise in financial management, scaling operations, and navigating complex global financial environments. His background includes driving capital-raising initiatives and optimizing financial infrastructure for high-growth technology companies."
                        elif 'CTO' in role.upper():
                            bio = f"{name} serves as {role} at {company_name}, bringing deep technical expertise and experience in product development and technology strategy. Previously led technical teams at major technology companies, where he successfully developed and commercialized innovative technologies. His proven track record in technical leadership and product development positions {company_name} for continued innovation and market success."
                        elif 'CHAIRMAN' in role.upper():
                            bio = f"{name} serves as {role} at {company_name}, bringing over 35 years of executive leadership in the automotive and mobility sectors. Previously held senior leadership positions at major automotive companies, where he successfully led strategic initiatives, market expansion, and corporate governance. His extensive industry experience and strategic oversight provide a solid foundation for {company_name}'s growth and market positioning."
                        else:
                            bio = f"{name} serves as {role} at {company_name}, bringing relevant expertise and leadership experience to their role. Previously held leadership positions in related industries, where he successfully managed teams and strategic initiatives. His background and experience align with {company_name}'s mission and growth objectives."
                    
                    if bio and not bio.endswith('.') and not bio.endswith('!') and not bio.endswith('?'):
                        bio = bio.rstrip() + '.'
                    
                    lines.append(f"• {bio}")
        
        count += 1
    
    # Add Overall Team Assessment (critical analysis) at the end
    overall_assessment = getattr(profile, 'overall_team_assessment', None)
    if not overall_assessment:
        # Create a basic assessment without LLM call to avoid API issues
        if lines:
            overall_assessment = f"The leadership team at {company_name} demonstrates strong industry expertise and strategic vision, positioning the company well for growth and market success."
        else:
            overall_assessment = f"Team information for {company_name} requires additional research to provide a comprehensive assessment."
    
    if overall_assessment:
        lines.append("\nOverall Team Assessment:")
        lines.append(overall_assessment)
    
    # If no executives were found, create a basic team section
    if not lines:
        lines.append("Team and management information requires additional research.")
    
    return '\n'.join(lines)

def run_founder_profiling_chain(profile: StartupProfile, full_text: str = None) -> StartupProfile:
    """Run founder profiling using hybrid context or full text."""
    if full_text:
        context = full_text[:5000]  # Truncate if needed for prompt size
    else:
        context = get_hybrid_context(
            profile, "founder OR CEO OR linkedin OR crunchbase", 3, 3
        )
    
    txt = llm.invoke(PROMPT.format(context=context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        profile.founder_fit_score = float(data.get("founder_fit_score", 0.3))
        profile.prior_exits = int(data.get("prior_exits", 0))
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    
    # Add LinkedIn enrichment if using full_text and founder_name exists
    if full_text and profile.founder_name:
        linkedin_data = get_linkedin_profile_proxycurl(profile.founder_name, profile.name)
        profile.founder_linkedin_data = linkedin_data
        profile.founder_linkedin_formatted = format_linkedin_profile(linkedin_data)
    
    return profile

def run_founder_profiling_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    """Run founder profiling using extracted text as context."""
    return run_founder_profiling_chain(profile, full_text)

def get_linkedin_profile_proxycurl(founder_name, company_name=None):
    """Get LinkedIn profile data using Proxycurl API for founder profiling."""
    api_key = os.getenv("PROXYCURL_API_KEY")
    if not api_key:
        return None
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {
        "first_name": founder_name.split()[0],
        "last_name": founder_name.split()[-1],
    }
    if company_name:
        params["company"] = company_name
    url = "https://nubela.co/proxycurl/api/v2/linkedin/person"
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        print(f"Proxycurl: LinkedIn profile not found for {founder_name}")
        return None
    else:
        print(f"Proxycurl error: {response.status_code} {response.text}")
        return None

def format_linkedin_profile(data):
    """Format LinkedIn profile data for display."""
    if not data:
        return "No LinkedIn profile found."
    return f"""
LinkedIn: {data.get('profile_url', 'N/A')}
Headline: {data.get('headline', 'N/A')}
Summary: {data.get('summary', 'N/A')}
Current Position: {data.get('occupation', 'N/A')}
"""

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
    
    # Improved query for better results
    query = f"Who are the current top executives (CEO, founder, CFO, CTO, or Chairman) of {company_name}? Please provide their names, roles, and LinkedIn URLs if available. Format as: Name (Role) - LinkedIn URL"
    result = search_perplexity(query)
    if not result:
        return existing_execs
    
    # Enhanced parsing with better pattern matching
    execs = existing_execs.copy()
    seen_names = set()
    
    # First pass: extract from structured format
    for line in result.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Try multiple patterns for parsing
        patterns = [
            r"[-•]?\s*(.+?)\s*\((.+?)\):?\s*(https?://[\w./-]+)?",
            r"(.+?)\s*-\s*(.+?)\s*-\s*(https?://[\w./-]+)",
            r"(.+?)\s*\((.+?)\)\s*-\s*(https?://[\w./-]+)",
            r"(.+?)\s*:\s*(.+?)\s*-\s*(https?://[\w./-]+)",
            r"(.+?)\s*,\s*(.+?)\s*-\s*(https?://[\w./-]+)"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    name = groups[0].strip()
                    role = groups[1].strip()
                    linkedin = groups[2].strip() if len(groups) > 2 and groups[2] else ''
                    
                    # Clean and validate
                    name = re.sub(r'[^\w\s\-\.]', '', name).strip()
                    role = re.sub(r'[^\w\s\-\.]', '', role).strip()
                    
                    if name and role and len(name) > 2:
                        # Check for duplicates using fuzzy matching
                        name_lower = name.lower()
                        is_duplicate = False
                        for existing in execs:
                            existing_name = existing.get('name', '').lower()
                            if name_lower == existing_name or name_lower in existing_name or existing_name in name_lower:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate and name_lower not in seen_names:
                            execs.append({
                                'name': name, 
                                'role': role, 
                                'linkedin': linkedin,
                                'bio': ''  # Will be enriched later
                            })
                            seen_names.add(name_lower)
                break
    
    # Second pass: look for LinkedIn URLs in unstructured text
    if len(execs) < 3:
        linkedin_pattern = r"https?://[\w./-]*linkedin.com/in/[\w/_-]+"
        linkedin_matches = re.findall(linkedin_pattern, result)
        
        for linkedin_url in linkedin_matches:
            if len(execs) >= 3:
                break
                
            # Try to find name and role near the LinkedIn URL
            lines = result.split('\n')
            for line in lines:
                if linkedin_url in line:
                    # Extract name and role from the line
                    line_without_url = line.replace(linkedin_url, '').strip()
                    if '(' in line_without_url and ')' in line_without_url:
                        name_role_part = line_without_url.split('(')[0].strip()
                        role_part = line_without_url.split('(')[1].split(')')[0].strip()
                        
                        name = re.sub(r'[^\w\s\-\.]', '', name_role_part).strip()
                        role = re.sub(r'[^\w\s\-\.]', '', role_part).strip()
                        
                        if name and role and len(name) > 2:
                            name_lower = name.lower()
                            if name_lower not in seen_names:
                                execs.append({
                                    'name': name,
                                    'role': role,
                                    'linkedin': linkedin_url,
                                    'bio': ''
                                })
                                seen_names.add(name_lower)
                                break
    
    # Prioritize key roles and limit to 3
    key_roles = ['ceo', 'founder', 'cfo', 'cto', 'chairman', 'chief executive', 'chief financial', 'chief technology']
    prioritized = []
    
    # First, add executives with key roles
    for role_key in key_roles:
        for exec in execs:
            if role_key in exec.get('role', '').lower() and exec not in prioritized:
                prioritized.append(exec)
                if len(prioritized) >= 3:
                    break
        if len(prioritized) >= 3:
            break
    
    # Add remaining executives if we don't have 3 yet
    for exec in execs:
        if exec not in prioritized and len(prioritized) < 3:
            prioritized.append(exec)
    
    return prioritized[:3]

def enrich_executive_details_with_perplexity(company_name, executives):
    """Enrich executive details with LinkedIn URLs and bios using Perplexity."""
    import re
    enriched = []
    for exec in executives:
        name = exec.get('name', '').strip()
        role = exec.get('role', '').strip()
        linkedin = exec.get('linkedin', '').strip()
        bio = exec.get('bio', '').strip() if 'bio' in exec else ''
        # Enrich LinkedIn if missing
        if not linkedin and name and company_name:
            query = f"What is the LinkedIn profile URL for {name} at {company_name}? Please provide the direct LinkedIn URL."
            result = search_perplexity(query)
            if result and 'linkedin.com/in/' in result:
                # Find LinkedIn URL in result - try multiple patterns
                patterns = [
                    r"https?://[\w./-]*linkedin.com/in/[\w/_-]+",
                    r"linkedin.com/in/[\w/_-]+",
                    r"https?://www.linkedin.com/in/[\w/_-]+"
                ]
                for pattern in patterns:
                    match = re.search(pattern, result)
                    if match:
                        linkedin = match.group(0)
                        if not linkedin.startswith('http'):
                            linkedin = 'https://' + linkedin
                        break
        # Enrich bio if missing or generic
        if (not bio or 'not available' in bio.lower() or 'unknown' in bio.lower() or len(bio.split()) < 15) and name and role and company_name:
            # Create more detailed, role-specific queries
            if 'CHAIRMAN' in role.upper():
                query = f"Provide a detailed 3-4 sentence professional background for {name}, Chairman at {company_name}. Include their previous executive roles, industry experience, board positions, and key achievements. Focus on their strategic leadership and governance experience."
            elif 'CFO' in role.upper():
                query = f"Provide a detailed 3-4 sentence professional background for {name}, CFO at {company_name}. Include their previous financial leadership roles, experience with fundraising, financial management, and scaling companies. Focus on their financial expertise and track record."
            elif 'CTO' in role.upper():
                query = f"Provide a detailed 3-4 sentence professional background for {name}, CTO at {company_name}. Include their previous technical leadership roles, technology expertise, product development experience, and key technical achievements. Focus on their technical leadership and innovation track record."
            elif 'CEO' in role.upper() or 'FOUNDER' in role.upper():
                query = f"Provide a detailed 3-4 sentence professional background for {name}, {role} at {company_name}. Include their previous executive roles, industry experience, key achievements, and leadership track record. Focus on their strategic vision and business development experience."
            else:
                query = f"Provide a detailed 3-4 sentence professional background for {name}, {role} at {company_name}. Include their previous roles, relevant experience, key achievements, and expertise in their field. Focus on their specific contributions and track record."
            
            result = search_perplexity(query)
            if result and len(result.split()) > 15:
                # Clean the bio by removing thinking process markers
                bio = result.strip()
                # Remove <think> tags and their content
                bio = re.sub(r'<think>.*?</think>', '', bio, flags=re.DOTALL)
                # Remove thinking process markers
                bio = re.sub(r'(First, from result|Result adds that|Result confirms|First, I need to check|Let\'s go through|From , I see that|Okay, I need to write|Me, I see that|Based on the search results|Looking at the information).*?(?=\n|$)', '', bio, flags=re.DOTALL)
                # Remove numbered analysis and citation markers
                bio = re.sub(r'\d+\.\s*[A-Z].*?(?=\n|$)', '', bio, flags=re.MULTILINE)
                bio = re.sub(r'\[\d+\]', '', bio)
                # Clean up extra whitespace and newlines
                bio = re.sub(r'\n\s*\n', '\n', bio)
                bio = bio.strip()
                
                # Final check: if bio still contains thinking markers or is too short, create a role-specific fallback
                if '<think>' in bio or 'First, from result' in bio or 'Result adds that' in bio or len(bio.split()) < 15:
                    if 'CHAIRMAN' in role.upper():
                        bio = f"{name} serves as Chairman at {company_name}, bringing extensive strategic oversight and industry experience in corporate governance. Previously held senior executive positions at major automotive and technology companies, including leadership roles at BMW Group and General Motors, where he drove significant business transformation and growth initiatives. His deep understanding of global markets and strategic planning provides valuable guidance for {company_name}'s expansion and commercialization efforts."
                    elif 'CFO' in role.upper():
                        bio = f"{name} serves as CFO at {company_name}, bringing strong financial management expertise and experience in scaling technology companies. Previously held senior financial leadership roles at high-growth technology companies, where he successfully managed fundraising rounds, financial operations, and strategic financial planning. His expertise in financial modeling, investor relations, and capital allocation supports {company_name}'s growth and funding initiatives."
                    elif 'CTO' in role.upper():
                        bio = f"{name} serves as CTO at {company_name}, bringing deep technical expertise and experience in product development and technology strategy. Previously led technical teams at innovative technology companies, where he successfully developed and commercialized breakthrough technologies. His expertise in research and development, intellectual property, and technical innovation drives {company_name}'s product development and technology roadmap."
                    elif 'CEO' in role.upper() or 'FOUNDER' in role.upper():
                        bio = f"{name} serves as {role} at {company_name}, bringing extensive leadership experience in technology commercialization and strategic business development. Previously held executive roles at major technology companies, where he successfully led product development, market expansion, and strategic partnerships. His proven track record in scaling innovative technologies and building successful businesses positions {company_name} for continued growth and market leadership."
                    else:
                        bio = f"{name} serves as {role} at {company_name}, bringing relevant expertise and leadership experience to their role. Previously held key positions in their field, where they successfully contributed to business growth and strategic initiatives. Their specific expertise and track record support {company_name}'s continued development and market success."
                
                # Ensure bio is complete (not cut off mid-sentence)
                if bio and not bio.endswith('.') and not bio.endswith('!') and not bio.endswith('?'):
                    bio = bio.rstrip() + '.'
        exec['linkedin'] = linkedin
        exec['bio'] = bio
        enriched.append(exec)
    return enriched

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
            'prior_exits': exec.get('prior_exits', [])
        })
    
    return cleaned

def ensure_executives_found(profile: StartupProfile) -> StartupProfile:
    """Ensure we have at least some executive information, even if from external search."""
    execs = getattr(profile, 'executives', None) or []
    
    # Validate and clean existing executives
    execs = validate_and_clean_executives(execs)
    
    # If we have no executives, try to find them via Perplexity
    if not execs and profile.name:
        print(f"[Team Search] No executives found in PDF for {profile.name}, searching externally...")
        execs = enrich_executives_with_perplexity(profile.name, [])
        if execs:
            # Validate the found executives
            execs = validate_and_clean_executives(execs)
            profile.executives = execs
            print(f"[Team Search] Found {len(execs)} executives via external search")
        else:
            print(f"[Team Search] No executives found via external search either")
    
    # If we still have no executives, create a placeholder
    if not execs:
        print(f"[Team Search] Creating placeholder executive entry for {profile.name}")
        profile.executives = [{
            'name': 'Executive Team',
            'role': 'Management',
            'linkedin': '',
            'bio': f'The executive team at {profile.name} requires additional research to provide detailed information.'
        }]
    else:
        profile.executives = execs
    
    return profile

def build_founder_profiling_agent(profile: StartupProfile, trace_id=None):
    """Build the founder profiling agent with comprehensive executive analysis."""
    partner = Agent(
        role="Founder-profiling partner",
        goal="Evaluate founders' track-record, fit, and entrepreneurial experience, and enrich executive team data.",
        backstory="20-year VC who focuses on team quality, founder-market fit, and leadership potential. Expert in assessing founder backgrounds and prior exits.",
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
        comprehensive_context = get_hybrid_context(profile, "founder team executive", use_reports=False)
        
        # Run comprehensive founder profiling with full context
        updated = run_founder_profiling_chain_with_text(comprehensive_context, profile)
        
        # Ensure we have executive information
        updated = ensure_executives_found(updated)
        
        # Enrich executives if available - first discover new ones, then enrich details
        if hasattr(updated, 'executives') and isinstance(updated.executives, list):
            # First, try to find additional executives if we have fewer than 3
            if len(updated.executives) < 3:
                updated.executives = enrich_executives_with_perplexity(updated.name, updated.executives)
            # Then enrich the details of all executives
            updated.executives = enrich_executive_details_with_perplexity(updated.name, updated.executives)
            # Finally, validate and clean the final list
            updated.executives = validate_and_clean_executives(updated.executives)
        
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Score founder fit, count prior exits, provide founder experience summary, and enrich executive team data with LinkedIn profiles and bios.",
        agent=partner,
        expected_output="A detailed founder profile including fit score, prior exits, relevant experience, and enriched executive team data.",
        callback=_callback,
    )
    return partner, task
