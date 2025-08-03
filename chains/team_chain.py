"""
Team Chain - Deterministic functions for team/executive data processing and formatting.
Moved from agents/founder_profiling_agent.py to separate deterministic logic from LLM orchestration.
"""

import re
import os
import requests
from typing import List, Dict, Any
from core.schemas import StartupProfile


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
        
        # Use background_summary if available, otherwise use bio
        if background_summary:
            # Clean up any remaining AI thinking patterns
            import re
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
        elif bio:
            # Clean up bio as well
            import re
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


def get_linkedin_profile_perplexity(name, company_name=None):
    """Get LinkedIn profile data using Perplexity search for executive profiling."""
    from core.perplexity_utils import search_perplexity
    
    try:
        # Search for LinkedIn profile with more specific query
        query = f"What is the LinkedIn profile URL for {name} at {company_name or ''}? Please provide the direct LinkedIn URL."
        result = search_perplexity(query)
        
        if result:
            # Extract LinkedIn URL if found (more flexible pattern)
            import re
            linkedin_patterns = [
                r'https?://[\w./-]*linkedin\.com/in/[\w/_-]+',
                r'https://www\.linkedin\.com/in/[\w/_-]+',
                r'https://linkedin\.com/in/[\w/_-]+',
                r'linkedin\.com/in/[\w/_-]+'
            ]
            
            linkedin_url = None
            for pattern in linkedin_patterns:
                linkedin_url_match = re.search(pattern, result)
                if linkedin_url_match:
                    linkedin_url = linkedin_url_match.group(0)
                    # Ensure it starts with https://
                    if linkedin_url.startswith('linkedin.com'):
                        linkedin_url = 'https://' + linkedin_url
                    # Clean up any trailing characters
                    linkedin_url = re.sub(r'[^\w/._-]+$', '', linkedin_url)
                    break
            
            # If no LinkedIn URL found with patterns, try flexible line-by-line parsing (like old logic)
            if not linkedin_url:
                for line in result.split('\n'):
                    # Try the old logic pattern: name (role): linkedin_url
                    match = re.match(r"[-•]?\s*(.+?)\s*\((.+?)\):?\s*(https?://[\w./-]+)?", line)
                    if match:
                        name_match, role_match, linkedin_match = match.groups()
                        if linkedin_match and 'linkedin.com/in/' in linkedin_match:
                            linkedin_url = linkedin_match.strip()
                            break
                    
                    # Fallback: try to extract from lines with LinkedIn URLs
                    elif 'linkedin.com/in/' in line:
                        parts = line.split(' - ')
                        if len(parts) >= 2:
                            name_role = parts[0].strip()
                            linkedin_candidates = [p for p in parts if 'linkedin.com/in/' in p]
                            if linkedin_candidates:
                                linkedin_url = linkedin_candidates[0].strip()
                                if not linkedin_url.startswith('http'):
                                    linkedin_url = 'https://' + linkedin_url
                                break
            
            if linkedin_url:
                # Get more detailed profile info
                profile_query = f"{name} {company_name or ''} current role position background experience"
                profile_result = search_perplexity(profile_query)
                
                # Parse the results into structured data
                profile_data = {
                    'profile_url': linkedin_url,
                    'headline': extract_headline(profile_result, name),
                    'summary': extract_summary(profile_result),
                    'experiences': extract_experiences(profile_result)
                }
                
                print(f"Perplexity: Found LinkedIn profile for {name}")
                return profile_data
            else:
                # Even if no LinkedIn URL found, try to extract profile data from the search result
                print(f"Perplexity: No LinkedIn URL found for {name}, but extracting profile data from search result")
                
                # Try to generate a LinkedIn URL based on name and company
                linkedin_url = generate_linkedin_url(name, company_name)
                
                profile_data = {
                    'profile_url': linkedin_url,
                    'headline': extract_headline(result, name),
                    'summary': extract_summary(result),
                    'experiences': extract_experiences(result)
                }
                
                # Only return if we have some meaningful data
                if profile_data['headline'] or profile_data['summary']:
                    print(f"Perplexity: Extracted profile data for {name}")
                    return profile_data
                else:
                    print(f"Perplexity: No meaningful profile data found for {name}")
                    return None
        else:
            print(f"Perplexity: No profile data found for {name}")
            return None
            
    except Exception as e:
        print(f"Perplexity LinkedIn search error for {name}: {e}")
        return None

def generate_linkedin_url(name, company_name=None):
    """Generate a LinkedIn URL based on name and company."""
    if not name:
        return None
    
    # Clean the name for URL generation
    name_clean = re.sub(r'[^\w\s]', '', name).strip()
    name_parts = name_clean.split()
    
    if len(name_parts) >= 2:
        # Use first and last name
        first_name = name_parts[0].lower()
        last_name = name_parts[-1].lower()
        linkedin_url = f"https://www.linkedin.com/in/{first_name}-{last_name}"
    else:
        # Use full name if only one part
        full_name = name_clean.lower().replace(' ', '-')
        linkedin_url = f"https://www.linkedin.com/in/{full_name}"
    
    return linkedin_url

def extract_headline(text, name):
    """Extract current headline/role from text."""
    import re
    
    # Clean up the text first - remove Perplexity thinking patterns
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'Okay,.*?\.', '', text, flags=re.DOTALL)
    text = re.sub(r'Let me.*?\.', '', text, flags=re.DOTALL)
    text = re.sub(r'First,.*?\.', '', text, flags=re.DOTALL)
    
    # Look for actual role patterns
    role_patterns = [
        rf'{name}.*?(CEO|CFO|CTO|Chief|President|Founder|Co-founder|Director|Manager|Deputy|Head)',
        rf'(CEO|CFO|CTO|Chief|President|Founder|Co-founder|Director|Manager|Deputy|Head).*?{name}',
        rf'{name}.*?is.*?(CEO|CFO|CTO|Chief|President|Founder|Co-founder|Director|Manager|Deputy|Head)',
        rf'{name}.*?serves as.*?',
        rf'{name}.*?currently.*?',
        rf'currently.*?{name}.*?'
    ]
    
    for pattern in role_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            headline = match.group(0).strip()
            # Clean up the headline
            headline = re.sub(rf'^{name}\s+', '', headline)
            headline = re.sub(rf'{name}\s+', '', headline)
            if len(headline) > 5 and headline != "at":
                return headline
    
    return ""

def extract_summary(text):
    """Extract summary/background from text."""
    import re
    
    # Clean up the text first - remove Perplexity thinking patterns
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'Okay,.*?\.', '', text, flags=re.DOTALL)
    text = re.sub(r'Let me.*?\.', '', text, flags=re.DOTALL)
    text = re.sub(r'First,.*?\.', '', text, flags=re.DOTALL)
    text = re.sub(r'Based on.*?', '', text, flags=re.DOTALL)
    text = re.sub(r'According to.*?', '', text, flags=re.DOTALL)
    
    # Look for actual content about the person
    lines = text.split('\n')
    summary_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip lines that are just thinking or navigation
        if (line and len(line) > 20 and 
            not line.startswith('http') and
            not line.startswith('Okay,') and
            not line.startswith('Let me') and
            not line.startswith('First,') and
            not line.startswith('Based on') and
            not line.startswith('According to') and
            not 'search result' in line.lower() and
            not 'indicates that' in line.lower()):
            
            summary_lines.append(line)
            if len(' '.join(summary_lines)) > 300:
                break
    
    summary = ' '.join(summary_lines) if summary_lines else ""
    
    # If we still have poor content, try to extract meaningful sentences
    if not summary or len(summary) < 50:
        sentences = text.split('.')
        meaningful_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if (len(sentence) > 30 and 
                not sentence.startswith('Okay,') and
                not sentence.startswith('Let me') and
                not 'search result' in sentence.lower() and
                not 'indicates that' in sentence.lower()):
                meaningful_sentences.append(sentence)
                if len(' '.join(meaningful_sentences)) > 200:
                    break
        summary = '. '.join(meaningful_sentences)
    
    return summary

def extract_experiences(text):
    """Extract work experiences from text."""
    import re
    
    # Clean up the text first
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'Okay,.*?\.', '', text, flags=re.DOTALL)
    text = re.sub(r'Let me.*?\.', '', text, flags=re.DOTALL)
    
    experiences = []
    
    # Look for actual company and role patterns
    experience_patterns = [
        r'(?:previously|formerly|worked|was)\s+(?:at|with|for)\s+([A-Z][a-zA-Z\s&\.]+)',
        r'([A-Z][a-zA-Z\s&\.]+)\s+(?:as|CEO|CFO|CTO|Chief|Founder|Co-founder)',
        r'(?:CEO|CFO|CTO|Chief|Founder|Co-founder)\s+(?:at|of)\s+([A-Z][a-zA-Z\s&\.]+)',
        r'([A-Z][a-zA-Z\s&\.]+)\s+(?:University|College|School)',
        r'(?:graduated|studied|attended)\s+([A-Z][a-zA-Z\s&\.]+)'
    ]
    
    for pattern in experience_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            company = match.strip()
            # Filter out common non-company words
            if (len(company) > 3 and 
                company.lower() not in ['the', 'and', 'or', 'search', 'result', 'first', 'second', 'third'] and
                not company.lower().startswith('okay') and
                not company.lower().startswith('let me') and
                not company.lower().startswith('s a') and
                not company.lower().startswith('they want') and
                not company.lower().startswith('to locate') and
                not company.lower().startswith('to find') and
                not 'public figure' in company.lower() and
                not 'linkedin profile' in company.lower() and
                not 'search results' in company.lower()):
                
                # Try to extract role from context
                role = "Executive"
                role_patterns = [
                    rf'{company}.*?(CEO|CFO|CTO|Chief|Founder|Co-founder|Director|Manager)',
                    rf'(CEO|CFO|CTO|Chief|Founder|Co-founder|Director|Manager).*?{company}'
                ]
                
                for role_pattern in role_patterns:
                    role_match = re.search(role_pattern, text, re.IGNORECASE)
                    if role_match:
                        role = role_match.group(1)
                        break
                
                experiences.append({
                    'company': company,
                    'title': role,
                    'duration': ''
                })
    
    # Remove duplicates and return top 3
    unique_experiences = []
    seen_companies = set()
    for exp in experiences:
        if exp['company'] not in seen_companies:
            unique_experiences.append(exp)
            seen_companies.add(exp['company'])
    
    return unique_experiences[:3]


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

def generate_executive_background_summary(name: str, role: str, linkedin_data: dict, company_name: str) -> str:
    """Generate a concise 4-sentence background summary for an executive."""
    from core.perplexity_utils import search_perplexity
    
    # If we have LinkedIn data, use it to generate a summary
    if linkedin_data:
        headline = linkedin_data.get('headline', '')
        summary = linkedin_data.get('summary', '')
        experience = linkedin_data.get('experiences', [])
        
        # Build 4-sentence summary from LinkedIn data
        sentences = []
        
        # Sentence 1: Current role (improved)
        if headline and len(headline) > 5 and headline != f"{name} at":
            # Clean up the headline
            clean_headline = headline.replace(f"{name} ", "").replace(f" {name}", "")
            if clean_headline and clean_headline != "at":
                sentences.append(f"{name} is currently {clean_headline}.")
            else:
                sentences.append(f"{name} serves as {role} at {company_name}.")
        else:
            sentences.append(f"{name} serves as {role} at {company_name}.")
        
        # Sentence 2: Previous role (if available)
        if experience and len(experience) > 0:
            recent_exp = experience[0] if isinstance(experience, list) else experience
            if isinstance(recent_exp, dict):
                company = recent_exp.get('company', '')
                title = recent_exp.get('title', '')
                if (company and title and 
                    company.lower() != company_name.lower() and
                    company.lower() not in ['search', 'result', 'first', 'second', 'third'] and
                    not company.lower().startswith('he currently') and
                    not company.lower().startswith('while the') and
                    not company.lower().startswith('note that') and
                    not company.lower().startswith('founder and') and
                    not company.lower().startswith('sources confirm') and
                    len(company) > 3):
                    sentences.append(f"Previously, {name} was {title} at {company}.")
        
        # Sentence 3: Education or key background (improved)
        if summary and len(summary) > 50:
            # Extract education or key background info
            education_keywords = ['university', 'college', 'mba', 'phd', 'bachelor', 'master', 'degree', 'graduated', 'studied']
            if any(keyword in summary.lower() for keyword in education_keywords):
                # Find education sentence
                lines = summary.split('.')
                for line in lines:
                    if any(keyword in line.lower() for keyword in education_keywords):
                        clean_line = line.strip()
                        if len(clean_line) > 20 and not clean_line.startswith('Okay'):
                            sentences.append(clean_line + ".")
                            break
                else:
                    # If no education found, try to extract meaningful background
                    meaningful_sentences = []
                    for line in summary.split('.'):
                        line = line.strip()
                        if (len(line) > 30 and 
                            not line.startswith('Okay') and
                            not line.startswith('Let me') and
                            not line.startswith('Even if') and
                            not line.startswith('To locate') and
                            not line.startswith('Let\'s start') and
                            not 'search result' in line.lower() and
                            not 'privacy policies' in line.lower() and
                            not 'consent' in line.lower()):
                            meaningful_sentences.append(line)
                            if len(meaningful_sentences) >= 1:
                                break
                    
                    if meaningful_sentences:
                        sentences.append(meaningful_sentences[0] + ".")
                    else:
                        sentences.append(f"{name} has extensive experience in the industry.")
            else:
                # Try to extract meaningful background from summary
                meaningful_sentences = []
                for line in summary.split('.'):
                    line = line.strip()
                    if (len(line) > 30 and 
                        not line.startswith('Okay') and
                        not line.startswith('Let me') and
                        not line.startswith('Even if') and
                        not line.startswith('To locate') and
                        not line.startswith('Let\'s start') and
                        not 'search result' in line.lower() and
                        not 'privacy policies' in line.lower() and
                        not 'consent' in line.lower()):
                        meaningful_sentences.append(line)
                        if len(meaningful_sentences) >= 1:
                            break
                
                if meaningful_sentences:
                    sentences.append(meaningful_sentences[0] + ".")
                else:
                    sentences.append(f"{name} has extensive experience in the industry.")
        else:
            sentences.append(f"{name} has extensive experience in the industry.")
        
        # Sentence 4: Key achievement or focus (improved)
        if summary and len(summary) > 100:
            # Look for achievement-related content
            achievement_keywords = ['led', 'managed', 'grew', 'increased', 'developed', 'founded', 'co-founded', 'oversaw', 'built']
            lines = summary.split('.')
            for line in lines:
                if any(keyword in line.lower() for keyword in achievement_keywords):
                    clean_line = line.strip()
                    if (len(clean_line) > 20 and 
                        not clean_line.startswith('Okay') and
                        not 'search result' in clean_line.lower()):
                        sentences.append(clean_line + ".")
                        break
            else:
                sentences.append(f"{name} focuses on driving growth and innovation at {company_name}.")
        else:
            sentences.append(f"{name} focuses on driving growth and innovation at {company_name}.")
        
        # Ensure we have exactly 4 sentences
        while len(sentences) < 4:
            sentences.append(f"{name} brings valuable expertise to {company_name}.")
        
        return " ".join(sentences[:4])
    
    # If no LinkedIn data, try web search for concise summary
    try:
        query = f"{name} {role} {company_name} background experience education"
        search_result = search_perplexity(query)
        
        if search_result:
            # Clean up the search result - remove AI thinking patterns
            import re
            cleaned_result = re.sub(r'<think>.*?</think>', '', search_result, flags=re.DOTALL)
            cleaned_result = re.sub(r'Based on.*?', '', cleaned_result, flags=re.DOTALL)
            cleaned_result = re.sub(r'According to.*?', '', cleaned_result, flags=re.DOTALL)
            cleaned_result = re.sub(r'Okay,.*?\.', '', cleaned_result, flags=re.DOTALL)
            cleaned_result = re.sub(r'Let me.*?\.', '', cleaned_result, flags=re.DOTALL)
            cleaned_result = re.sub(r'First,.*?\.', '', cleaned_result, flags=re.DOTALL)
            cleaned_result = re.sub(r'Now,.*?\.', '', cleaned_result, flags=re.DOTALL)
            cleaned_result = re.sub(r'I need to.*?\.', '', cleaned_result, flags=re.DOTALL)
            cleaned_result = re.sub(r'Let\'s.*?\.', '', cleaned_result, flags=re.DOTALL)
            
            # Extract meaningful sentences
            sentences = cleaned_result.split('.')
            valid_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if (len(sentence) > 20 and 
                    len(valid_sentences) < 4 and
                    not sentence.startswith('Okay') and
                    not sentence.startswith('Let me') and
                    not sentence.startswith('First,') and
                    not sentence.startswith('Now,') and
                    not sentence.startswith('I need to') and
                    not sentence.startswith('Let\'s') and
                    not 'search result' in sentence.lower() and
                    not 'thinking' in sentence.lower() and
                    not 'analysis' in sentence.lower()):
                    valid_sentences.append(sentence + ".")
            
            if valid_sentences:
                return " ".join(valid_sentences)
    except Exception as e:
        print(f"[Background Summary] Error searching for {name}: {e}")
    
    # Fallback: return basic 4-sentence summary
    return f"{name} serves as {role} at {company_name}. {name} has extensive experience in the industry. {name} brings valuable expertise to {company_name}. {name} focuses on driving growth and innovation at {company_name}."


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
    import re
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

def enrich_executive_details_with_perplexity(company_name, executives):
    """
    Enrich executive details with LinkedIn URLs and bios using Perplexity.
    Based on the old logic approach for better quality.
    """
    from core.perplexity_utils import search_perplexity
    
    enriched = []
    for exec in executives:
        name = exec.get('name', '').strip()
        role = exec.get('role', '').strip()
        linkedin = exec.get('linkedin', '').strip()
        bio = exec.get('bio', '').strip()
        background_summary = exec.get('background_summary', '').strip()
        
        # Enrich LinkedIn if missing
        if not linkedin and name and company_name:
            query = f"What is the LinkedIn profile URL for {name} at {company_name}?"
            result = search_perplexity(query)
            if result and 'linkedin.com/in/' in result:
                import re
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
                
                # If still no LinkedIn URL found, try flexible line-by-line parsing
                if not linkedin:
                    for line in result.split('\n'):
                        # Try the old logic pattern: name (role): linkedin_url
                        match = re.match(r"[-•]?\s*(.+?)\s*\((.+?)\):?\s*(https?://[\w./-]+)?", line)
                        if match:
                            name_match, role_match, linkedin_match = match.groups()
                            if linkedin_match and 'linkedin.com/in/' in linkedin_match:
                                linkedin = linkedin_match.strip()
                                break
                        
                        # Fallback: try to extract from lines with LinkedIn URLs
                        elif 'linkedin.com/in/' in line:
                            parts = line.split(' - ')
                            if len(parts) >= 2:
                                name_role = parts[0].strip()
                                linkedin_candidates = [p for p in parts if 'linkedin.com/in/' in p]
                                if linkedin_candidates:
                                    linkedin = linkedin_candidates[0].strip()
                                    if not linkedin.startswith('http'):
                                        linkedin = 'https://' + linkedin
                                    break
        
        # Enrich bio if missing or generic
        if (not bio or 'not available' in bio.lower() or 'unknown' in bio.lower()) and name and role and company_name:
            query = f"Write a 2-3 sentence professional bio for {name}, {role} at {company_name}. Include notable past roles, companies, and achievements if available."
            result = search_perplexity(query)
            if result and len(result.split()) > 8:
                # Clean up the bio - remove AI thinking text
                import re
                bio = result.strip()
                # Remove common AI thinking patterns
                thinking_patterns = [
                    r'<think>.*?</think>',
                    r'Okay, let me.*?\.',
                    r'Let me analyze.*?\.',
                    r'Based on.*?\.',
                    r'According to.*?\.',
                    r'First, looking at.*?\.',
                    r'Now, putting this together.*?\.',
                    r'I need to.*?\.',
                    r'Let me start by.*?\.',
                    r'Okay, I need to.*?\.',
                    r'Let\'s tackle this.*?\.',
                    r'Let me.*?\.',
                    r'First,.*?\.',
                    r'Now,.*?\.'
                ]
                for pattern in thinking_patterns:
                    bio = re.sub(pattern, '', bio, flags=re.DOTALL | re.IGNORECASE)
                bio = bio.strip()
                # If bio is now too short, skip it
                if len(bio.split()) < 5:
                    bio = ''
        
        # Generate background summary if missing
        if not background_summary and name and role and company_name:
            background_summary = generate_executive_background_summary(name, role, None, company_name)
        
        exec['linkedin'] = linkedin
        exec['bio'] = bio
        exec['background_summary'] = background_summary
        enriched.append(exec)
    
    return enriched


def run_team_chain(profile: StartupProfile) -> StartupProfile:
    """Run team chain to process and validate executive data."""
    # Check if we already have executives from PDF extraction
    existing_execs = getattr(profile, 'executives', []) or []
    
    print(f"[Team Chain] Found {len(existing_execs)} executives from PDF extraction")
    
    # If we have executives from PDF, use them (don't override with web search)
    if existing_execs and len(existing_execs) > 0:
        print("[Team Chain] Using executives from PDF extraction - skipping web search")
        
        # Only enrich existing executives with LinkedIn data
        enriched_execs = []
        
        # Sort executives by priority and limit to top 3
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
        
        # Sort and limit to top 3
        sorted_execs = sorted(existing_execs, key=lambda x: get_role_priority(x.get('role', '')) if isinstance(x, dict) else len(key_roles))
        top_3_execs = sorted_execs[:3]
        
        for i, exec in enumerate(top_3_execs):
            if isinstance(exec, dict):
                name = exec.get('name', '')
                role = exec.get('role', '')
                
                if name and name.lower() not in ['unknown', 'n/a', 'none']:
                    print(f"[Team Chain] Enriching LinkedIn for PDF executive {i+1}: {name} ({role})")
                    
                    # Use the improved enrichment approach (based on old logic)
                    enriched_exec = exec.copy()
                    
                    # Enrich with LinkedIn URL and bio using dedicated functions
                    if not enriched_exec.get('linkedin') and name and profile.name:
                        query = f"What is the LinkedIn profile URL for {name} at {profile.name}?"
                        from core.perplexity_utils import search_perplexity
                        result = search_perplexity(query)
                        if result and 'linkedin.com/in/' in result:
                            import re
                            match = re.search(r"https?://[\w./-]*linkedin.com/in/[\w/_-]+", result)
                            if match:
                                enriched_exec['linkedin'] = match.group(0)
                    
                    # Generate better bio if missing
                    if not enriched_exec.get('bio') and name and role and profile.name:
                        # Use a more structured query to avoid AI thinking patterns
                        query = f"{name} {role} {profile.name} professional background experience achievements"
                        from core.perplexity_utils import search_perplexity
                        result = search_perplexity(query)
                        if result and len(result.split()) > 8:
                            # Clean up the bio - remove AI thinking text
                            import re
                            bio = result.strip()
                            # Remove common AI thinking patterns
                            thinking_patterns = [
                                r'<think>.*?</think>',
                                r'Okay, let me.*?\.',
                                r'Let me analyze.*?\.',
                                r'Based on.*?\.',
                                r'According to.*?\.',
                                r'First, looking at.*?\.',
                                r'Now, putting this together.*?\.',
                                r'I need to.*?\.',
                                r'Let me start by.*?\.',
                                r'Okay, I need to.*?\.',
                                r'Let\'s tackle this.*?\.',
                                r'Let me.*?\.',
                                r'First,.*?\.',
                                r'Now,.*?\.'
                            ]
                            for pattern in thinking_patterns:
                                bio = re.sub(pattern, '', bio, flags=re.DOTALL | re.IGNORECASE)
                            bio = bio.strip()
                            # If bio is now too short, skip it
                            if len(bio.split()) < 5:
                                bio = ''
                            enriched_exec['bio'] = bio
                    
                    # Generate background summary
                    background_summary = generate_executive_background_summary(name, role, None, profile.name)
                    enriched_exec['background_summary'] = background_summary
                    
                    # Enrich with LinkedIn and bio using the enhanced function
                    enriched_exec = enrich_executive_details_with_perplexity(profile.name, [enriched_exec])[0]
                    
                    enriched_execs.append(enriched_exec)
                else:
                    enriched_execs.append(exec)
            else:
                enriched_execs.append(exec)
        
        # Add any remaining executives without enrichment (beyond top 3)
        for exec in existing_execs[3:]:
            enriched_execs.append(exec)
        
        # Update profile with enriched executives (keeping PDF data)
        profile.executives = enriched_execs
        
    else:
        # Only if NO executives found in PDF, then try web search
        print("[Team Chain] No executives found in PDF - falling back to web search")
        profile = ensure_executives_found(profile)
        
        # Process web-found executives
        execs = getattr(profile, 'executives', []) or []
        enriched_execs = []
        
        # Sort executives by priority and limit to top 3
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
        
        # Sort and limit to top 3
        sorted_execs = sorted(execs, key=lambda x: get_role_priority(x.get('role', '')) if isinstance(x, dict) else len(key_roles))
        top_3_execs = sorted_execs[:3]
        
        for i, exec in enumerate(top_3_execs):
            if isinstance(exec, dict):
                name = exec.get('name', '')
                role = exec.get('role', '')
                
                if name and name.lower() not in ['unknown', 'n/a', 'none']:
                    print(f"[Team Chain] Enriching LinkedIn for web executive {i+1}: {name} ({role})")
                    
                    # Get LinkedIn data using Perplexity (since Proxycurl shut down)
                    linkedin_data = get_linkedin_profile_perplexity(name, profile.name)
                    
                    # Generate background summary
                    background_summary = generate_executive_background_summary(name, role, linkedin_data, profile.name)
                    
                    # Update executive with enriched data
                    enriched_exec = exec.copy()
                    enriched_exec['linkedin_data'] = linkedin_data
                    enriched_exec['background_summary'] = background_summary
                    
                    # If we have LinkedIn data, update the LinkedIn URL
                    if linkedin_data and linkedin_data.get('profile_url'):
                        enriched_exec['linkedin'] = linkedin_data.get('profile_url')
                    
                    enriched_execs.append(enriched_exec)
                else:
                    enriched_execs.append(exec)
            else:
                enriched_execs.append(exec)
        
        # Add any remaining executives without enrichment (beyond top 3)
        for exec in execs[3:]:
            enriched_execs.append(exec)
        
        # Update profile with enriched executives
        profile.executives = enriched_execs
    
    # Keep legacy founder LinkedIn data for backward compatibility
    if profile.founder_name:
        linkedin_data = get_linkedin_profile_perplexity(profile.founder_name, profile.name)
        profile.founder_linkedin_data = linkedin_data
        profile.founder_linkedin_formatted = format_linkedin_profile(linkedin_data)
    
    return profile 