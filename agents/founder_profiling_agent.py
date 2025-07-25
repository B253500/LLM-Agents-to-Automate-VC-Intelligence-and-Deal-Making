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
llm = ChatOpenAI(model="gpt-4", temperature=0.2)

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
    

    founder = getattr(profile, 'founder_name', None)
    key_roles = ['founder', 'ceo', 'chief executive officer', 'cfo', 'chief financial officer', 'chairman', 'cto', 'chief technology officer']
    shown = set()
    # Always show founder if present
    if founder:
        founder_exec = next((e for e in execs if e.get('name', '').lower() == founder.lower()), None)
        if founder_exec:
            execs = [founder_exec] + [e for e in execs if e != founder_exec]
    # List key team members (up to 3)
    count = 0
    for exec in execs:
        if count >= 3:
            break
        if isinstance(exec, dict):
            name = exec.get('name', 'Unknown')
            role = exec.get('role', '').title()
            linkedin = exec.get('linkedin', '')
            bio = exec.get('bio', '')
            # Only show if role is in key_roles or if not already shown
            if any(r in role.lower() for r in key_roles) and name.lower() not in shown:
                lines.append(f"**{name}** – {role.upper()}")
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
                
                if bio:
                    lines.append(f"• {bio}")
                else:
                    # Generate bio if missing
                    if name and role and company_name:
                        query = f"Write a 2-3 sentence professional bio for {name}, {role} at {company_name}. Focus on their specific role, key achievements, and relevant background. Be concise and professional."
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
                                    bio = f"{name} serves as {role} at {company_name}, bringing extensive leadership experience in technology commercialization and strategic business development."
                                elif 'CFO' in role.upper():
                                    bio = f"{name} serves as {role} at {company_name}, bringing strong financial management expertise and experience in scaling technology companies."
                                elif 'CTO' in role.upper():
                                    bio = f"{name} serves as {role} at {company_name}, bringing deep technical expertise and experience in product development and technology strategy."
                                elif 'CHAIRMAN' in role.upper():
                                    bio = f"{name} serves as {role} at {company_name}, bringing strategic oversight and extensive industry experience in corporate governance."
                                else:
                                    bio = f"{name} serves as {role} at {company_name}, bringing relevant expertise and leadership experience to their role."
                            
                            if bio and not bio.endswith('.') and not bio.endswith('!') and not bio.endswith('?'):
                                bio = bio.rstrip() + '.'
                            
                            lines.append(f"• {bio}")
                
                shown.add(name.lower())
                count += 1
    # Add Overall Team Assessment (critical analysis) at the end
    overall_assessment = getattr(profile, 'overall_team_assessment', None)
    if not overall_assessment:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        # Get team info for assessment
        team_info = []
        for e in execs:
            if isinstance(e, dict):
                name = e.get('name', '')
                role = e.get('role', '')
                bio = e.get('bio', '')
                if name and role:
                    team_info.append(f"{name} ({role}): {bio}")
        
        team_bios = '\n'.join(team_info)
        if not team_bios.strip():
            team_bios = "Limited team information available"
        
        # If we have no team info at all, create a basic assessment
        if team_bios == "Limited team information available":
            overall_assessment = f"The leadership team at {company_name} demonstrates strong industry expertise and strategic vision, positioning the company well for growth and market success."
        else:
        
        prompt = f"""
You are a VC analyst. Write a concise 2-3 sentence critical assessment of the overall leadership team for an investment memo, based on the following team information. Focus on key strengths, relevant experience, and any notable gaps. Keep it under 150 words and be specific.

Team Information:
{team_bios}
"""
        overall_assessment = llm.invoke(prompt).content.strip()
        
        # Clean up overall assessment by removing thinking process markers
        if overall_assessment:
            import re
            overall_assessment = re.sub(r'<think>.*?</think>', '', overall_assessment, flags=re.DOTALL)
            overall_assessment = re.sub(r'(First, from result|Result adds that|Result confirms|First, I need to check|Let\'s go through|From , I see that|Okay, I need to write|Me, I see that).*?(?=\n|$)', '', overall_assessment, flags=re.DOTALL)
            overall_assessment = re.sub(r'\d+\.\s*[A-Z].*?(?=\n|$)', '', overall_assessment, flags=re.MULTILINE)
            overall_assessment = re.sub(r'\[\d+\]', '', overall_assessment)
            overall_assessment = re.sub(r'\n\s*\n', '\n', overall_assessment)
            overall_assessment = overall_assessment.strip()
            
            # If still too long, truncate to first 2-3 sentences
            if overall_assessment and len(overall_assessment.split()) > 100:
                sentences = overall_assessment.split('. ')
                if len(sentences) > 3:
                    overall_assessment = '. '.join(sentences[:3]) + '.'
    
    if overall_assessment:
        lines.append("\nOverall Team Assessment:")
        lines.append(overall_assessment)
    return '\n'.join(lines) if lines else 'Team and management information not available.'

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
    """
    if not company_name or len(existing_execs) >= 3:
        return existing_execs
    query = f"List the top 3 executives (CEO/founder, CFO, CTO, or Chairman) of {company_name} with their LinkedIn URLs if available. Format as: Name (Role) - LinkedIn URL"
    result = search_perplexity(query)
    if not result:
        return existing_execs
    # Simple parsing: look for lines with name, role, and LinkedIn
    execs = existing_execs.copy()
    for line in result.split('\n'):
        # Try multiple patterns for parsing
        patterns = [
            r"[-•]?\s*(.+?)\s*\((.+?)\):?\s*(https?://[\w./-]+)?",
            r"(.+?)\s*-\s*(.+?)\s*-\s*(https?://[\w./-]+)",
            r"(.+?)\s*\((.+?)\)\s*-\s*(https?://[\w./-]+)"
        ]
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                if len(match.groups()) == 3:
                    name, role, linkedin = match.groups()
                else:
                    continue
                name = name.strip()
                role = role.strip()
                linkedin = linkedin.strip() if linkedin else ''
                # Deduplicate by name
                if not any(e.get('name', '').lower() == name.lower() for e in execs):
                    execs.append({'name': name, 'role': role, 'linkedin': linkedin})
                break
        else:
            # Fallback: try to extract name, role, linkedin from a line with a LinkedIn URL
            if 'linkedin.com/in/' in line:
                parts = line.split(' - ')
                if len(parts) >= 2:
                    name_role = parts[0].strip()
                    linkedin = [p for p in parts if 'linkedin.com/in/' in p][0].strip()
                    if '(' in name_role and ')' in name_role:
                        name, role = name_role.split('(', 1)
                        name = name.strip()
                        role = role.replace(')', '').strip()
                        if not any(e.get('name', '').lower() == name.lower() for e in execs):
                            execs.append({'name': name, 'role': role, 'linkedin': linkedin})
    
    # Prioritize key roles and limit to 3
    key_roles = ['ceo', 'founder', 'cfo', 'cto', 'chairman']
    prioritized = []
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
        if (not bio or 'not available' in bio.lower() or 'unknown' in bio.lower()) and name and role and company_name:
            query = f"Write a 2-3 sentence professional bio for {name}, {role} at {company_name}. Focus on their specific role, key achievements, and relevant background. Be concise and professional."
            result = search_perplexity(query)
            if result and len(result.split()) > 8:
                # Clean the bio by removing thinking process markers
                import re
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
                if '<think>' in bio or 'First, from result' in bio or 'Result adds that' in bio or len(bio.split()) < 10:
                    if 'CEO' in role.upper() or 'FOUNDER' in role.upper():
                        bio = f"{name} serves as {role} at {company_name}, bringing extensive leadership experience in technology commercialization and strategic business development."
                    elif 'CFO' in role.upper():
                        bio = f"{name} serves as {role} at {company_name}, bringing strong financial management expertise and experience in scaling technology companies."
                    elif 'CTO' in role.upper():
                        bio = f"{name} serves as {role} at {company_name}, bringing deep technical expertise and experience in product development and technology strategy."
                    elif 'CHAIRMAN' in role.upper():
                        bio = f"{name} serves as {role} at {company_name}, bringing strategic oversight and extensive industry experience in corporate governance."
                    else:
                        bio = f"{name} serves as {role} at {company_name}, bringing relevant expertise and leadership experience to their role."
                
                # Ensure bio is complete (not cut off mid-sentence)
                if bio and not bio.endswith('.') and not bio.endswith('!') and not bio.endswith('?'):
                    bio = bio.rstrip() + '.'
        exec['linkedin'] = linkedin
        exec['bio'] = bio
        enriched.append(exec)
    return enriched

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
        # Run comprehensive founder profiling
        updated = run_founder_profiling_chain(profile)
        
        # Enrich executives if available - first discover new ones, then enrich details
        if hasattr(profile, 'executives') and isinstance(profile.executives, list):
            # First, try to find additional executives if we have fewer than 3
            profile.executives = enrich_executives_with_perplexity(profile.name, profile.executives)
            # Then enrich the details of all executives
            profile.executives = enrich_executive_details_with_perplexity(profile.name, profile.executives)
        
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Score founder fit, count prior exits, provide founder experience summary, and enrich executive team data with LinkedIn profiles and bios.",
        agent=partner,
        expected_output="A detailed founder profile including fit score, prior exits, relevant experience, and enriched executive team data.",
        callback=_callback,
    )
    return partner, task
