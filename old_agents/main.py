import sys
import os
import re
from datetime import datetime
from core.download_utils import extract_text
from chains.pitch_deck_chain import run_pitch_deck_chain
from chains.technical_dd_chain import run_technical_dd_chain
from chains.founder_profiling_chain import run_founder_profiling_chain
from chains.market_sizing_chain import run_market_sizing_chain
from chains.financial_analysis_chain import run_financial_analysis_chain
from chains.competitive_intel_chain import run_competitive_intel_chain
from chains.risk_assessment_chain import run_risk_assessment_chain
from core.schemas import StartupProfile
from core.vector_store import clear_collection
from fpdf import FPDF
from langchain_openai import ChatOpenAI
from agents.technical_dd_agent import build_technical_dd_agent
from agents.market_sizing_agent import build_market_sizing_agent
from agents.competitive_intel_agent import build_competitive_intel_agent
from agents.founder_profiling_agent import build_founder_profiling_agent
from agents.financial_analysis_agent import build_financial_analysis_agent
from agents.risk_assessment_agent import build_risk_assessment_agent
from agents.deck_agent import build_deck_agent

import hashlib
import json as pyjson
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import subprocess
from core.perplexity_utils import search_perplexity
from core.visual_utils import extract_images_from_pdf, generate_sample_market_chart, extract_market_and_financials_from_visuals

CACHE_DIR = "extraction_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_path(file_path):
    # Use file hash for uniqueness
    with open(file_path, 'rb') as f:
        file_hash = hashlib.sha1(f.read()).hexdigest()
    return os.path.join(CACHE_DIR, f"{os.path.basename(file_path)}_{file_hash}.json")

def load_from_cache(file_path):
    cache_path = get_cache_path(file_path)
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return pyjson.load(f)
    return None

def save_to_cache(file_path, data):
    cache_path = get_cache_path(file_path)
    with open(cache_path, 'w', encoding='utf-8') as f:
        pyjson.dump(data, f)

def extract_market_size_from_text(text):
    """Extract market size values with better error handling and logging"""
    results = {}
    try:
        tam_match = re.search(r'(Total Addressable Market|Addressable market|TAM)[^\d$]{0,20}(\$?\d+[,.]?\d*)\s*[Bb]?', text, re.IGNORECASE)
        if tam_match:
            val = tam_match.group(2).replace(',', '').replace('$', '')
            try:
                results['TAM'] = float(val) * 1e9 if 'B' in tam_match.group(0) or 'billion' in tam_match.group(0).lower() else float(val)
                print(f"[Market Size] Found TAM={results['TAM']}")
            except Exception as e:
                print(f"[Market Size] Error parsing TAM value '{val}': {e}")
                results['TAM'] = val
    # SAM
            sam_match = re.search(r'(Serviceable Available Market|SAM)[^\d$]{0,20}(\$?\d+[,.]?\d*)\s*[BbMmKk]?', text, re.IGNORECASE)
        if sam_match:
            val = sam_match.group(2).replace(',', '').replace('$', '')
            try:
                results['SAM'] = float(val) * 1e9 if 'B' in sam_match.group(0) or 'billion' in sam_match.group(0).lower() else float(val)
                print(f"[Market Size] Found SAM={results['SAM']}")
            except Exception as e:
                print(f"[Market Size] Error parsing SAM value '{val}': {e}")

        # SOM
        som_match = re.search(r'(Serviceable Obtainable Market|SOM)[^\d$]{0,20}(\$?\d+[,.]?\d*)\s*[BbMmKk]?', text, re.IGNORECASE)
        if som_match:
            val = som_match.group(2).replace(',', '').replace('$', '')
            try:
                results['SOM'] = float(val) * 1e9 if 'B' in som_match.group(0) or 'billion' in som_match.group(0).lower() else float(val)
                print(f"[Market Size] Found SOM={results['SOM']}")
            except Exception as e:
                print(f"[Market Size] Error parsing SOM value '{val}': {e}")

        # CAGR
        cagr_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%\s*CAGR', text)
        if cagr_match:
            try:
                results['cagr'] = float(cagr_match.group(1))
                print(f"[Market Size] Found CAGR={results['cagr']}%")
            except Exception as e:
                print(f"[Market Size] Error parsing CAGR: {e}")

    except Exception as e:
        print(f"[Market Size] Error extracting market sizes: {e}")
    return results

def update_market_value(profile, key, value, source):
    """Update market size value if new source has higher priority"""
    current_value = getattr(profile, key, None)
    current_source = getattr(profile, f"{key}_source", None)
    
    # Priority order: deck_text > deck_ocr/table > web_search
    source_priority = {
        "deck_text": 3,
        "deck_ocr/table": 2, 
        "web_search": 1
    }
    
    if not current_value or source_priority.get(source, 0) > source_priority.get(current_source, 0):
        setattr(profile, key, value)
        setattr(profile, f"{key}_source", source)
        print(f"[Market Size] Updated {key}={value} from {source}")

def log_market_size_changes(profile):
    """Debug helper to track market size changes"""
    market_fields = ['TAM', 'SAM', 'SOM', 'cagr', 'market_growth_rate']
    print("\n=== Market Size Values ===")
    for field in market_fields:
        value = getattr(profile, field, None)
        source = getattr(profile, f"{field}_source", None)
        print(f"[Market Size] {field}={value} (source: {source})")
    print("========================\n")

# Update run_all_sequential_with_text to use these functions
def run_all_sequential_with_text(full_text: str, profile: StartupProfile, file_path: str) -> StartupProfile:
    print(f"🔍 Processing extracted text ({len(full_text)} characters)")
    
    # Extract and validate market size values
    market_vals = extract_market_size_from_text(full_text)
    for k, v in market_vals.items():
        if v:
            update_market_value(profile, k, v, "deck_text")
    
    # Log initial market values
    log_market_size_changes(profile)
    
def enrich_executives_with_perplexity(company_name, existing_execs):
    """
    Use Perplexity to find additional executives and their LinkedIn profiles if fewer than 3 are found.
    """
    if not company_name or len(existing_execs) >= 3:
        return existing_execs
    query = f"List the CEO/founder, CFO, CTO, and Chairman of {company_name} with their LinkedIn URLs if available."
    result = search_perplexity(query)
    if not result:
        return existing_execs
    # Simple parsing: look for lines with name, role, and LinkedIn
    import re
    execs = existing_execs.copy()
    for line in result.split('\n'):
        match = re.match(r"[-•]?\s*(.+?)\s*\((.+?)\):?\s*(https?://[\w./-]+)?", line)
        if match:
            name, role, linkedin = match.groups()
            name = name.strip()
            role = role.strip()
            linkedin = linkedin.strip() if linkedin else ''
            # Deduplicate by name
            if not any(e.get('name', '').lower() == name.lower() for e in execs):
                execs.append({'name': name, 'role': role, 'linkedin': linkedin})
        elif 'linkedin.com/in/' in line:
            # Fallback: try to extract name, role, linkedin from a line with a LinkedIn URL
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
    return execs[:3]

def enrich_executive_details_with_perplexity(company_name, executives):
    enriched = []
    for exec in executives:
        name = exec.get('name', '').strip()
        role = exec.get('role', '').strip()
        linkedin = exec.get('linkedin', '').strip()
        bio = exec.get('bio', '').strip() if 'bio' in exec else ''
        # Enrich LinkedIn if missing
        if not linkedin and name and company_name:
            query = f"What is the LinkedIn profile URL for {name} at {company_name}?"
            result = search_perplexity(query)
            if result and 'linkedin.com/in/' in result:
                import re
                # Find LinkedIn URL in result
                match = re.search(r"https?://[\w./-]*linkedin.com/in/[\w/_-]+", result)
                if match:
                    linkedin = match.group(0)
        # Enrich bio if missing or generic
        if (not bio or 'not available' in bio.lower() or 'unknown' in bio.lower()) and name and role and company_name:
            query = f"Write a 2-3 sentence professional bio for {name}, {role} at {company_name}. Include notable past roles, companies, and achievements if available."
            result = search_perplexity(query)
            if result and len(result.split()) > 8:
                bio = result.strip()
        exec['linkedin'] = linkedin
        exec['bio'] = bio
        enriched.append(exec)
    return enriched

# Add product_description to StartupProfile if not present
if not hasattr(StartupProfile, 'product_description'):
    StartupProfile.product_description = None

# Helper to merge chain and agent outputs
import json
def merge_outputs(chain_output, agent_output):
    if not agent_output:
        return chain_output
    if not chain_output:
        return agent_output
    # If both are dicts, merge keys; if both are strings, concatenate
    if isinstance(chain_output, dict) and isinstance(agent_output, dict):
        merged = chain_output.copy()
        merged.update(agent_output)
        return merged
    return f"{chain_output}\n{agent_output}"

# --- Enhanced Product Description Extraction ---
def synthesize_product_description(profile):
    # Prefer explicit product_description, else synthesize from solution, tech, business model
    descs = [
        getattr(profile, 'product_description', None),
        getattr(profile, 'tech_stack', None),
        getattr(profile, 'moat_strength', None),
        getattr(profile, 'business_model', None),
        getattr(profile, 'tech_maturity', None),
    ]
    descs = [d for d in descs if d and (not isinstance(d, str) or d.lower() not in ['n/a', 'not available', 'unknown'])]

    if not descs:
        return 'Product description not available.'
    # Remove duplicates and repetitive phrases
    seen = set()
    result = []
    for d in descs:
        if d not in seen and len(d.split()) > 6:
            result.append(d)
            seen.add(d)
    return '\n'.join(result) if result else descs[0]

def synthesize_product_description_llm(profile):
    """
    Use LLM to synthesize a detailed, multi-paragraph, multi-bullet Product/Service Description section for the memo, matching the style of memo_generator's generate_llm_memo.
    """
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
    You are a VC analyst writing the Product/Service Description section for an investment memo.
    - Do NOT repeat information already covered in the Detailed Summary or Solution Overview.
    - Focus on the unique technical features, product roadmap, and what sets this product apart from competitors.
    - Be concise: no more than 8 sentences.
    - Use plain, non-marketing language.
    Context:
    Company: {getattr(profile, 'name', '')}
    Sector: {getattr(profile, 'sector', '')}
    Product: {getattr(profile, 'product_description', '')}
    Stage: {getattr(profile, 'funding_stage', '')}
    Business Model: {getattr(profile, 'business_model', '')}
    Go-to-Market: {getattr(profile, 'go_to_market', '')}
    """
    response = llm.invoke(prompt)
    return response.content.strip() if hasattr(response, 'content') else str(response)

# Update run_all_sequential_with_text to use both chains and agents

def run_all_sequential_with_text(full_text: str, profile: StartupProfile, file_path: str) -> StartupProfile:
    print(f"🔍 Processing extracted text ({len(full_text)} characters)")
    print(f"📄 Starting with fresh profile: {profile.name}")

     # --- NEW: Extract market size from text before running agents ---
    market_vals = extract_market_size_from_text(full_text)
    for k, v in market_vals.items():
        if hasattr(profile, k) and v:
            setattr(profile, k, v)
            setattr(profile, f"{k}_source", "deck_text")
            print(f"[Market Size] Found {k}={v} in deck text")
    # Deck extraction (chain + agent)    
    from chains.pitch_deck_chain import run_pitch_deck_chain_with_text as run_pitch_chain
    profile = run_pitch_chain(full_text, profile, pdf_path=file_path)
    deck_agent, deck_task = build_deck_agent(file_path)
    deck_agent_output = deck_task.callback()
    try:
        deck_agent_data = json.loads(deck_agent_output)
        for k, v in deck_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    # --- Enrich executives from LinkedIn/Crunchbase if needed ---
    execs = getattr(profile, 'executives', None) or []
    founder = getattr(profile, 'founder_name', None)
    # Only keep up to 3 key roles: founder/CEO, CFO, chairman, CTO (in that order)
    key_roles = ['founder', 'ceo', 'chief executive officer', 'cfo', 'chief financial officer', 'chairman', 'cto', 'chief technology officer']
    filtered_execs = []
    seen = set()
    if founder:
        filtered_execs.append({'name': founder, 'role': 'Founder', 'linkedin': getattr(profile, 'founder_linkedin', '')})
        seen.add(founder.lower())
    for role in key_roles:
        for exec in execs:
            name = exec.get('name', '').strip()
            role_str = exec.get('role', '').lower()
            if name and role in role_str and name.lower() not in seen:
                filtered_execs.append(exec)
                seen.add(name.lower())
            if len(filtered_execs) >= 3:
                break
        if len(filtered_execs) >= 3:
            break
    # If fewer than 3, enrich with Perplexity
    if len(filtered_execs) < 3:
        filtered_execs = enrich_executives_with_perplexity(profile.name, filtered_execs)
    profile.executives = filtered_execs[:3]
    print(f"📊 After pitch deck: Company={profile.name}, Founder={profile.founder_name}, Executives={len(getattr(profile, 'executives', []))}")
    # Technical Due Diligence (chain + agent)
    from chains.technical_dd_chain import run_technical_dd_chain
    profile = run_technical_dd_chain(profile)
    tech_agent, tech_task = build_technical_dd_agent(profile)
    tech_agent_output = tech_task.callback()
    try:
        tech_agent_data = json.loads(tech_agent_output)
        for k, v in tech_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"🔧 After tech DD: Maturity={profile.tech_maturity}, Moat={profile.moat_strength}")
    # --- Internet search fallback for technical due diligence ---
    missing_tech = []
    if not getattr(profile, 'tech_maturity', None): missing_tech.append('tech_maturity')
    if not getattr(profile, 'moat_strength', None): missing_tech.append('moat_strength')
    if not getattr(profile, 'tech_stack', None): missing_tech.append('tech_stack')
    if not getattr(profile, 'security', None): missing_tech.append('security')
    if not getattr(profile, 'implementation', None): missing_tech.append('implementation')
    if not getattr(profile, 'regulatory', None): missing_tech.append('regulatory')
    if not getattr(profile, 'testing', None): missing_tech.append('testing')
    if missing_tech:
        try:
            from core.perplexity_utils import search_perplexity
            from langchain_openai import ChatOpenAI
            query = f"What are the key technical details (maturity, moat, tech stack, security, implementation, regulatory, testing) for {profile.name} in the {profile.sector} sector?"
            web_result = search_perplexity(query)
            print(f"[Tech DD Perplexity] Web result:\n{web_result}")
            if web_result:
                llm = ChatOpenAI(model='gpt-4')
                prompt = f"""
You are a VC analyst. Extract the following fields from the web search result below. Respond ONLY with a valid JSON object with these keys: {', '.join(missing_tech)}. If a field is missing, use null. Do NOT include any explanation or markdown.

Web search result:
{web_result}
"""
                result = llm.invoke(prompt)
                import json
                raw = result.content.strip()
                if raw.startswith('```'):
                    lines = raw.splitlines()
                    if lines[0].startswith('```'):
                        lines = lines[1:]
                    if lines and lines[-1].startswith('```'):
                        lines = lines[:-1]
                    raw = '\n'.join(lines).strip()
                try:
                    extracted = json.loads(raw)
                    for k, v in extracted.items():
                        if hasattr(profile, k) and v:
                            # Try to cast to float for numeric fields
                            if k in ['TAM', 'SAM', 'SOM', 'cagr', 'market_growth_rate']:
                                try:
                                    setattr(profile, k, float(v))
                                except Exception:
                                    setattr(profile, k, v)
                            else:
                                setattr(profile, k, v)
                            # Set source for each value
                            if k in ['TAM', 'SAM', 'SOM', 'cagr', 'market_growth_rate']:
                                setattr(profile, f"{k}_source", 'deck_ocr/table')
                                print(f"[Market Size Extraction] Found {k} in deck figures/tables: {v}")
                    print(f"[Tech DD Perplexity] Extracted: {extracted}")
                except Exception as e:
                    print(f"[Tech DD Perplexity] Failed to parse LLM output: {e}")
        except Exception as e:
            print(f"[Tech DD Perplexity] Error: {e}")
    # Founder Profiling (chain + agent)
    from chains.founder_profiling_chain import run_founder_profiling_chain
    profile = run_founder_profiling_chain(profile)
    founder_agent, founder_task = build_founder_profiling_agent(profile)
    founder_agent_output = founder_task.callback()
    try:
        founder_agent_data = json.loads(founder_agent_output)
        for k, v in founder_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"👤 After founder profiling: Score={profile.founder_fit_score}")
    # Market Sizing (agent only; all logic is now in the agent)
    market_agent, market_task = build_market_sizing_agent(profile)
    market_agent_output = market_task.callback()
    try:
        market_agent_data = json.loads(market_agent_output)
        for k, v in market_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"📈 After market sizing: TAM={profile.TAM}, SAM={profile.SAM}, SOM={profile.SOM}")
    # Financial Analysis (chain + agent)
    from chains.financial_analysis_chain import run_financial_analysis_chain
    profile = run_financial_analysis_chain(profile)
    fin_agent, fin_task = build_financial_analysis_agent(profile)
    fin_agent_output = fin_task.callback()
    try:
        fin_agent_data = json.loads(fin_agent_output)
        for k, v in fin_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"💰 After financial analysis: Burn={profile.cash_burn_12m}, Runway={profile.runway_months}")
    # Competitive Intelligence (chain + agent)
    from chains.competitive_intel_chain import run_competitive_intel_chain
    profile = run_competitive_intel_chain(profile)
    comp_agent, comp_task = build_competitive_intel_agent(profile)
    comp_agent_output = comp_task.callback()
    try:
        comp_agent_data = json.loads(comp_agent_output)
        for k, v in comp_agent_data.items():
            if hasattr(profile, k) and v:
                # Only overwrite top_competitors if v is a non-empty list
                if k == "top_competitors" and isinstance(v, list) and not v:
                    continue
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"🏆 After competitive intel: {len(profile.top_competitors)} competitors found")
    # After competitive intel enrichment, ensure each competitor has a website
    from core.external_enrichment import find_company_website
    for comp in getattr(profile, 'top_competitors', []):
        if not comp.get('website'):
            website = find_company_website(
                company_name=comp.get('name', ''),
                sector=getattr(profile, 'sector', None),
                deck_text=None
            )
            if website:
                comp['website'] = website
    # Risk Assessment (chain + agent)
    from chains.risk_assessment_chain import run_risk_assessment_chain
    profile = run_risk_assessment_chain(profile)
    risk_agent, risk_task = build_risk_assessment_agent(profile)
    risk_agent_output = risk_task.callback()
    try:
        risk_agent_data = json.loads(risk_agent_output)
        for k, v in risk_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"⚠️ After risk assessment: Score={profile.risk_score}, {len(profile.risk_flags)} flags")
    # ESG, Business Model, Exit, Follow-up (chains only for now)
    from chains.esg_chain import run_esg_chain_with_text
    from chains.business_model_chain import run_business_model_chain_with_text
    from chains.exit_strategy_chain import run_exit_strategy_chain_with_text
    from chains.follow_up_chain import run_follow_up_chain_with_text
    profile = run_esg_chain_with_text(full_text, profile)
    print(f"🌱 After ESG: {profile.esg_summary}")
    profile = run_business_model_chain_with_text(full_text, profile)
    print(f"💼 After business model: {profile.business_model}")
    profile = run_exit_strategy_chain_with_text(full_text, profile)
    print(f"🚪 After exit strategy: {profile.exit_strategy}")
    profile = run_follow_up_chain_with_text(full_text, profile)
    print(f"❓ After follow-up: {profile.follow_up_questions}")
    # Product Description (enhanced)
    profile.product_description = synthesize_product_description(profile)

    # --- Visual OCR value extraction for market size and financials ---
    from core.visual_utils import extract_market_and_financials_from_visuals
    if getattr(profile, 'figures_ocr', None) or getattr(profile, 'tables_text', None):
        profile = extract_market_and_financials_from_visuals(profile, getattr(profile, 'figures_ocr', None), getattr(profile, 'tables_text', None))
    # --- Fallback: targeted web search for market size ---
    if not profile.TAM or not profile.SAM or not profile.SOM or not profile.cagr or not profile.market_growth_rate:
        from core.perplexity_utils import search_perplexity
        company = getattr(profile, 'name', '')
        product = getattr(profile, 'product_description', '')
        sector = getattr(profile, 'sector', '')
        queries = []
        if sector:
            queries += [
                f"global {sector} market size 2024",
                f"{sector} TAM 2024",
                f"{sector} total addressable market",
                f"{sector} market CAGR 2024",
                f"{sector} market growth rate 2024"
            ]
        if product:
            queries += [
                f"market size for {product} 2024",
                f"{product} TAM 2024"
            ]
        if company:
            queries += [
                f"market size for {company} 2024",
                f"{company} TAM 2024"
            ]
        market_size_sources = []
        max_web_searches = 2
        web_search_count = 0
        for q in queries:
            if web_search_count >= max_web_searches:
                print("[Market Size Web Search] Reached web search limit.")
                break
            print(f"[Market Size Web Search] Querying: {q}")
            try:
                import signal
                import time
                class TimeoutException(Exception): pass
                def handler(signum, frame): raise TimeoutException()
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(30)  # 30 second timeout
                result = search_perplexity(q)
                web_search_count += 1
                signal.alarm(0)
                print(f"[Market Size Web Search] Result: {result[:500]}")
                # Try to extract a source URL from the result
                import re
                urls = re.findall(r'https?://[\w./\-_%#?=&]+', result)
                if urls:
                    market_size_sources.extend(urls)
                # Use LLM to extract values from result
                llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
                prompt = f"""
Extract the following fields if present: TAM, SAM, SOM, CAGR, market_growth_rate. Use only the provided context. Return as JSON.
Context:
{result}
"""
                txt = llm.invoke(prompt).content.strip()
                first, last = txt.find("{"), txt.rfind("}")
                if first != -1 and last != -1:
                    import json
                    data = json.loads(txt[first : last + 1])
                    for k, v in data.items():
                        # Only set if not already set from deck/ocr
                        if hasattr(profile, k) and v and not getattr(profile, k, None):
                            # Try to cast to float for numeric fields
                            if k in ['TAM', 'SAM', 'SOM', 'cagr', 'market_growth_rate']:
                                try:
                                    setattr(profile, k, float(v))
                                except Exception:
                                    setattr(profile, k, v)
                            else:
                                setattr(profile, k, v)
                            # Set source for each value
                            if k in ['TAM', 'SAM', 'SOM', 'cagr', 'market_growth_rate']:
                                if urls:
                                    setattr(profile, f"{k}_source", urls[0])
                                else:
                                    setattr(profile, f"{k}_source", 'web_search')
                # Save sources to profile if found
                if market_size_sources:
                    profile.market_size_sources = list(set(market_size_sources))
                # If all found, break
                if profile.TAM and profile.SAM and profile.SOM and profile.cagr and profile.market_growth_rate:
                    break
            except Exception as e:
                print(f"[Market Size Web Search] Error: {e}")
                continue
    # --- Website enrichment if missing ---
    if not profile.website or profile.website.lower() in ['unknown', 'n/a', '']:
        try:
            from core.external_enrichment import find_company_website
            website = find_company_website(
                company_name=profile.name,
                founder_name=profile.founder_name,
                sector=profile.sector,
                deck_text=full_text if 'full_text' in locals() else None
            )
            if website:
                profile.website = website
                print(f"[Website Enrichment] Found website: {website}")
            else:
                print("[Website Enrichment] No website found.")
        except Exception as e:
            print(f"[Website Enrichment] Error: {e}")

    # --- Funding stage and amount enrichment ---
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
        funding_query = f"What is the latest funding stage and total funding amount for {profile.name}? Prefer Crunchbase, PitchBook, or TechCrunch as sources. Return the answer as: Funding Stage: <stage>, Funding Amount: <amount>, Source: <url>"
        funding_result = llm.invoke(funding_query).content.strip()
        import re
        stage_match = re.search(r'Funding Stage:\s*([^,\n]+)', funding_result)
        amount_match = re.search(r'Funding Amount:\s*([^,\n]+)', funding_result)
        source_match = re.search(r'Source:\s*(https?://\S+)', funding_result)
        if stage_match:
            profile.funding_stage = stage_match.group(1).strip()
        if amount_match:
            profile.funding_amount = amount_match.group(1).strip()
        if source_match:
            profile.funding_source = source_match.group(1).strip()
        print(f"[Funding Enrichment] Stage: {getattr(profile, 'funding_stage', None)}, Amount: {getattr(profile, 'funding_amount', None)}, Source: {getattr(profile, 'funding_source', None)}")
    except Exception as e:
        print(f"[Funding Enrichment] Error: {e}")

    if hasattr(profile, 'executives') and isinstance(profile.executives, list):
        profile.executives = enrich_executive_details_with_perplexity(profile.name, profile.executives)
    return profile


def run_pitch_deck_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    from chains.pitch_deck_chain import run_pitch_deck_chain_with_text as run_pitch_chain
    return run_pitch_chain(full_text, profile)


def run_technical_dd_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_technical_dd_chain(profile)


def run_founder_profiling_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_founder_profiling_chain(profile)


def run_market_sizing_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_market_sizing_chain(profile)


def run_financial_analysis_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_financial_analysis_chain(profile)


def run_competitive_intel_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_competitive_intel_chain(profile)


def run_risk_assessment_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_risk_assessment_chain(profile)


# --- Enhanced Detailed Summary Paragraph ---
def synthesize_detailed_summary(profile):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
    You are a VC analyst writing the DETAILED SUMMARY section for an investment memo.
    - Write a concise, high-level summary of the company in 3-5 sentences (no more than half a page).
    - Focus on what the company does, its unique value, business model, and market positioning.
    - Do NOT include technical details, product specs, or deep business model mechanics—leave those for later sections.
    - Use plain, non-marketing language.
    Context:
    Company: {getattr(profile, 'name', '')}
    Sector: {getattr(profile, 'sector', '')}
    Product: {getattr(profile, 'product_description', '')}
    Stage: {getattr(profile, 'funding_stage', '')}
    """
    response = llm.invoke(prompt)
    return response.content.strip() if hasattr(response, 'content') else str(response)

# --- Enhanced Problem Statement and Solution Reasoning ---
def synthesize_problem_statement_llm(profile):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
    You are a VC analyst writing the Problem Statement section for an investment memo.
    - Clearly state the main problem or pain point that the company's product/service is solving.
    - Try to be specific to the company's sector, product, and market context.
    - Do NOT use generic or sector-wide statements—focus on the actual problem this company addresses.
    - Do NOT mention the company's solution or product features—only describe the problem.
    - Use plain, non-marketing language.
    Context:
    Company: {getattr(profile, 'name', '')}
    Sector: {getattr(profile, 'sector', '')}
    Product: {getattr(profile, 'product_description', '')}
    Stage: {getattr(profile, 'funding_stage', '')}
    Business Model: {getattr(profile, 'business_model', '')}
    Go-to-Market: {getattr(profile, 'go_to_market', '')}
    """
    response = llm.invoke(prompt)
    return response.content.strip() if hasattr(response, 'content') else str(response)

def synthesize_solution_overview_llm(profile):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
    You are a VC analyst writing the Solution Overview section for an investment memo.
    - Clearly explain how the company's product/service solves the problem described in the Problem Statement.
    - Focus ONLY on the core solution. Don't describe in detail the product, just the solution.
    - Use plain, non-marketing language.
    Context:
    Company: {getattr(profile, 'name', '')}
    Sector: {getattr(profile, 'sector', '')}
    Product: {getattr(profile, 'product_description', '')}
    Stage: {getattr(profile, 'funding_stage', '')}
    """
    response = llm.invoke(prompt)
    return response.content.strip() if hasattr(response, 'content') else str(response)

# --- Inline Source Attribution for Market Size & Analysis ---
def format_money(val):
    try:
        val = float(val)
    except (TypeError, ValueError):
        return str(val)
    print(f"[DEBUG] format_money raw value: {val}")  # Debug print for diagnosis
    abs_val = abs(val)
    if abs_val >= 1_000_000_000:
        if val % 1_000_000_000 == 0:
            return f"${val/1_000_000_000:,.0f} B"
        else:
            return f"${val/1_000_000_000:,.1f} B"
    elif abs_val >= 1_000_000:
        if val % 1_000_000 == 0:
            return f"${val/1_000_000:,.0f} M"
        else:
            return f"${val/1_000_000:,.1f} M"
    elif abs_val >= 1_000:
        if val % 1_000 == 0:
            return f"${val/1_000:,.0f} K"
        else:
            return f"${val/1_000:,.1f} K"
    else:
        return f"${val:,.0f}"

def format_market_size_section(profile):
    from langchain_openai import ChatOpenAI
    TAM = format_money(getattr(profile, 'TAM', 0))
    TAM_source = getattr(profile, 'TAM_source', None)
    SAM = format_money(getattr(profile, 'SAM', 0))
    SAM_source = getattr(profile, 'SAM_source', None)
    SOM = format_money(getattr(profile, 'SOM', 0))
    SOM_source = getattr(profile, 'SOM_source', None)
    CAGR = getattr(profile, 'cagr', None)
    CAGR_source = getattr(profile, 'cagr_source', None)
    growth_rate = getattr(profile, 'market_growth_rate', None)
    growth_rate_source = getattr(profile, 'market_growth_rate_source', None)
    sector = getattr(profile, 'sector', '')
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    web_sources = getattr(profile, 'market_size_sources', []) or []
    web_links = [url for url in web_sources if url.startswith('http')][:3]
    web_links_str = '\n'.join(f"- [Source Link]({url})" for url in web_links)
    prompt = f"""
You are a VC analyst writing the Market Size & Analysis section for an investment memo.
- Use the following data and web sources to write a concise, insightful market discussion (3-5 sentences).
- Discuss market size, growth, key trends, and what the company could achieve or challenges it may face.
- If web sources are available, reference them and include clickable links.
- Use plain, non-marketing language.

Data:
TAM: {TAM}
SAM: {SAM}
SOM: {SOM}
CAGR: {CAGR}%
Growth Rate: {growth_rate}
Sector: {sector}
Web Sources:\n{web_links_str}
"""
    market_discussion = llm.invoke(prompt).content.strip()
    def format_source(source):
        if isinstance(source, str):
            if source.startswith('http'):
                return f"[Source: {source}]"
            elif source == 'web_search':
                urls = getattr(profile, 'market_size_sources', []) or []
                if urls:
                    return f"[Source: {urls[0]}]"
        return f"[Source: {source}]" if source else ""
    lines = []
    lines.append(market_discussion)
    lines.append("")
    try:
        som_val = float(getattr(profile, 'SOM', 0) or 0)
        tam_val = float(getattr(profile, 'TAM', 1) or 1)
        market_penetration = (som_val / tam_val * 100) if tam_val else 0.0
    except Exception:
        market_penetration = 0.0
    lines.append(f"TAM {TAM}{format_source(TAM_source)}, SAM {SAM}{format_source(SAM_source)}, SOM {SOM}{format_source(SOM_source)}; Market Penetration: {market_penetration:.1f} %")
    if CAGR:
        lines.append(f"CAGR: {CAGR}%{format_source(CAGR_source)}")
    if growth_rate:
        lines.append(f"Market Growth Rate: {growth_rate}{format_source(growth_rate_source)}")
    web_metrics = []
    for key, label in [("TAM", "TAM"), ("CAGR", "CAGR"), ("challenges", "Key Challenges"), ("drivers", "Key Drivers")]:
        val = getattr(profile, f'web_{key}', None)
        src = getattr(profile, f'web_{key}_source', None)
        if val:
            if src and src.startswith('http'):
                web_metrics.append(f"• {label}: {val} [Source: {src}]")
            else:
                web_metrics.append(f"• {label}: {val}")
    if web_metrics:
        lines.append("\nWeb-Enriched Market Metrics:")
        lines.extend(web_metrics)
    if web_links:
        lines.append("\nMarket Data Sources:")
        for url in web_links:
            lines.append(f"- {url}")
    # Add alternative market size estimates if available
    if hasattr(profile, 'alternative_market_sizes') and profile.alternative_market_sizes:
        lines.append("\nAlternative Market Size Estimates:")
        for entry in profile.alternative_market_sizes:
            if entry.get('url'):
                lines.append(f"• {entry['value']} ({entry['year']}) – [{entry['source']}]({entry['url']})")
            else:
                lines.append(f"• {entry['value']} ({entry['year']}) – {entry['source']}")
    return '\n'.join(lines)

def format_competitive_landscape(profile):
    """Enhanced competitive landscape with detailed competitor analysis"""
    competitors = getattr(profile, 'top_competitors', [])
    if not competitors:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        # Try to generate competitors from context
        prompt = f"""
        Based on this company's profile, list 3-5 likely competitors in their space:
        Company: {getattr(profile, 'name', '')}
        Sector: {getattr(profile, 'sector', '')}
        Product: {getattr(profile, 'product_description', '')}
        Market: {getattr(profile, 'market_summary', '')}
        """
        competitors_text = llm.invoke(prompt).content.strip()
        if competitors_text:
            return f"Potential Competitors (AI-generated based on company profile):\n{competitors_text}\n\nNote: This is an AI-generated competitive landscape and should be verified."

    lines = ["Key Competitors Analysis:"]
    
    for comp in competitors:
        name = comp.get('name', 'Unknown')
        website = comp.get('website', '') or comp.get('url', '')
        product = comp.get('product_offering', '') or comp.get('product', '') or comp.get('description', '')
        differentiator = comp.get('differentiator', '')
        
        # Header with name and website
        if website:
            lines.append(f"\n• {name} ({website})")
        else:
            lines.append(f"\n• {name}")
            
        if product:
            lines.append(f"  Product: {product}")
        if differentiator and differentiator != product:
            lines.append(f"  Differentiator: {differentiator}")
            
        # Add competitive positioning
        if getattr(profile, 'competitive_positioning', None):
            lines.append(f"  Positioning vs {name}: {profile.competitive_positioning}")
            
    # Add competitive summary if available
    if getattr(profile, 'competitive_summary', None):
        lines.append(f"\nCompetitive Summary:\n{profile.competitive_summary}")
        
    return '\n'.join(lines)

def format_technical_dd_section(profile):
    # Display the full LLM-generated technical due diligence narrative if available
    narrative = getattr(profile, 'technical_dd_narrative', '') or getattr(profile, 'technical_dd_analysis', '')
    tech = profile.tech_maturity or 'N/A'
    moat = profile.moat_strength or ''
    tech_stack = getattr(profile, 'tech_stack', None)
    regulatory = getattr(profile, 'regulatory', None)
    testing = getattr(profile, 'testing', None)
    security = getattr(profile, 'security', None)
    complexity = getattr(profile, 'complexity', None)
    implementation = getattr(profile, 'implementation', None)
    # assumption_risks = getattr(profile, 'assumption_risks', None)  # Removed
    bullets = []
    bullets.append(f"• Technical Feasibility and Performance: {tech}.")
    if moat:
        bullets.append(f"• Moat: {moat}.")
    if tech_stack:
        bullets.append(f"• Tech Stack: {tech_stack}.")
    bullets.append(f"• Complexity: {complexity or 'Not specified.'}")
    bullets.append(f"• Security: {security or 'Product safety, data, and IP protection should be addressed.'}")
    bullets.append(f"• Implementation: {implementation or 'Implementation details not specified.'}")
    # bullets.append(f"• Assumption Risks: {assumption_risks or 'Assumption risks not specified.'}")  # Removed
    bullets.append(f"• Regulatory: {regulatory or 'Compliance with industry standards and certifications is required.'}")
    bullets.append(f"• Testing: {testing or 'Independent validation and certification are recommended.'}")
    bullets.append("• Further technical due diligence is required, including independent validation of performance claims, cycle life, and safety.")
    lines = []
    if narrative:
        lines.append(narrative.strip())
    lines.extend(bullets)
    return '\n'.join(lines)

def format_product_description_section(profile):
    # Gather all relevant fields
    desc = getattr(profile, 'product_description', None)
    specs = getattr(profile, 'product_specs', None)
    roadmap = getattr(profile, 'product_roadmap', None)
    unique = getattr(profile, 'unique_features', None)
    status = getattr(profile, 'status', None)
    cell_format = getattr(profile, 'cell_format', None)
    cycle_life = getattr(profile, 'cycle_life', None)
    energy_density = getattr(profile, 'energy_density', None)
    uniqueness = getattr(profile, 'uniqueness', None)
    diff = getattr(profile, 'difference_from_competitors', None)
    scalability = getattr(profile, 'scalability', None)
    sustainability = getattr(profile, 'sustainability', None)
    regulatory = getattr(profile, 'regulatory', None)
    testing = getattr(profile, 'testing', None)
    security = getattr(profile, 'security', None)

    # Synthesize a narrative lead sentence
    lead = None
    if desc and len(desc.split()) > 6:
        lead = desc
    else:
        # Try to synthesize a narrative
        parts = []
        if cell_format or status:
            parts.append(f"The core product is a {cell_format or ''} {status or ''} battery".strip() + ".")
        if unique:
            parts.append(f"It features {unique}.")
        if specs:
            parts.append(f"Key specs: {specs}.")
        if cycle_life or energy_density:
            ce = []
            if cycle_life:
                ce.append(f"cycle life of {cycle_life}")
            if energy_density:
                ce.append(f"energy density of {energy_density}")
            if ce:
                parts.append("It offers " + " and ".join(ce) + ".")
        if roadmap:
            parts.append(f"Product roadmap: {roadmap}.")
        if uniqueness:
            parts.append(f"What makes it unique: {uniqueness}.")
        if diff:
            parts.append(f"Compared to competitors: {diff}.")
        if scalability:
            parts.append(f"Scalability: {scalability}.")
        if sustainability:
            parts.append(f"Sustainability: {sustainability}.")
        if regulatory:
            parts.append(f"Regulatory: {regulatory}.")
        if testing:
            parts.append(f"Testing: {testing}.")
        if security:
            parts.append(f"Security: {security}.")
        # Compose a paragraph
        lead = ' '.join(parts)
    if not lead or len(lead.strip()) < 20:
        # Fallback: concatenate all fields if no narrative possible
        all_fields = [desc, specs, roadmap, unique, status, cell_format, cycle_life, energy_density, uniqueness, diff, scalability, sustainability, regulatory, testing, security]
        all_fields = [str(f) for f in all_fields if f]
        if all_fields:
            lead = ' '.join(all_fields)
        else:
            return 'Product description not available.'
    return lead.strip()

def format_funding_stage(profile):
    funding_stage = getattr(profile, 'funding_stage', None) or 'Undisclosed'
    # Try to pull from PitchBook if available
    pitchbook_round = getattr(profile, 'pitchbook_last_round', None)
    pitchbook_year = getattr(profile, 'pitchbook_last_year', None)
    if funding_stage.lower() in ['unknown', 'n/a', '']:
        if pitchbook_round and pitchbook_year:
            funding_stage = f"{pitchbook_round} ({pitchbook_year})"
        else:
            last_round = getattr(profile, 'last_funding_round', None)
            last_round_year = getattr(profile, 'last_funding_year', None)
            if last_round and last_round_year:
                funding_stage = f"Undisclosed (last round: {last_round} - {last_round_year})"
            else:
                funding_stage = "Undisclosed (no public data found)"
    return funding_stage

def format_financials_section(profile, current_date):
    # Collect all financial metrics
    metrics = [
        ("Revenue", getattr(profile, 'revenue', None)),
        ("Projected Revenue", getattr(profile, 'projected_revenue', None)),
        ("Cash Burn (12m)", getattr(profile, 'cash_burn_12m', None)),
        ("Runway (months)", getattr(profile, 'runway_months', None)),
        ("Implied Valuation", getattr(profile, 'implied_valuation', None)),
        ("Gross Margin", getattr(profile, 'gross_margin', None)),
        ("EBITDA", getattr(profile, 'ebitda', None)),
        ("Net Income", getattr(profile, 'net_income', None)),
        ("ARR", getattr(profile, 'arr', None)),
        ("MRR", getattr(profile, 'mrr', None)),
        ("CAC", getattr(profile, 'cac', None)),
        ("LTV", getattr(profile, 'ltv', None)),
        ("Payback Period", getattr(profile, 'payback_period', None)),
        ("Revenue Growth Rate", getattr(profile, 'revenue_growth_rate', None)),
        ("Debt", getattr(profile, 'debt', None)),
        ("Cash on Hand", getattr(profile, 'cash_on_hand', None)),
    ]
    # Cap Table/Investors
    major_investors = getattr(profile, 'major_investors', None)
    ownership_breakdown = getattr(profile, 'ownership_breakdown', None)
    # Check if any metrics are available
    has_metrics = any(v is not None and v != '' for _, v in metrics) or (major_investors or ownership_breakdown)
    if not has_metrics:
        return f"Company has not released financials as of {current_date}. No detailed financials were disclosed in the deck or public sources. We recommend requesting a financial summary from the company, including revenue, burn rate, runway, and recent funding rounds. Independent verification of financials is advised before proceeding."
    # Table header
    lines = ["| Metric | Value |", "|--------|-------|"]
    for label, value in metrics:
        if value is not None and value != '':
            lines.append(f"| {label} | {value} |")
    # Cap Table/Investors
    if major_investors:
        lines.append(f"| Major Investors | {', '.join(major_investors)} |")
    if ownership_breakdown:
        for owner in ownership_breakdown:
            name = owner.get('name', 'Unknown')
            percent = owner.get('percent', '')
            lines.append(f"| Ownership: {name} | {percent} |")
    return '\n'.join(lines)

def format_risk_score(profile):
    risk_score = getattr(profile, 'risk_score', None)
    if risk_score is not None and risk_score != 'N/A':
        return f"Risk Score: {risk_score}"
    else:
        return ""

# --- De-duplication Post-processing ---
def deduplicate_memo(text):
    import re
    lines = text.split('\n')
    seen = set()
    result = []
    for line in lines:
        l = line.strip()
        if l and l not in seen:
            result.append(line)
            seen.add(l)
        elif l and len(l) > 30 and not any(l in r for r in result):
            result.append(line)
    return '\n'.join(result)

def format_risk_section(profile):
    risk_flags = getattr(profile, 'risk_flags', [])
    regulatory = getattr(profile, 'regulatory', None)
    testing = getattr(profile, 'testing', None)
    security = getattr(profile, 'security', None)
    discussion = []
    # Enumerate and describe all risks
    if risk_flags:
        for rf in risk_flags:
            discussion.append(f"• {rf}")
    else:
        discussion.append("• Risks are present but not fully disclosed. Investors should request more information and conduct further diligence.")
    # Always include regulatory, testing, security
    discussion.append(f"• Regulatory: {regulatory or 'Compliance with evolving standards and certifications is required.'}")
    discussion.append(f"• Testing: {testing or 'Independent validation and certification are recommended.'}")
    discussion.append(f"• Security: {security or 'Product safety, data, and IP protection should be addressed.'}")
    return '\n'.join(discussion)

def synthesize_risks_section_llm(profile):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Risks section for an investment memo.
- List the risks relevant to this company and product, sector with a specific explanation for each risk.
- Make each risk specific to the company's technology, market, or business context. Avoid generic or boilerplate risks.
- If possible cover market, technical, operational, regulatory and financial risks. Use a critical, VC-style lens.
- Use bullet points, with each risk followed by a short, specific explanation.
- Use plain, non-marketing language.
Context:
Company: {getattr(profile, 'name', '')}
Sector: {getattr(profile, 'sector', '')}
Risks: {getattr(profile, 'risk_flags', '')}
Risk Score: {getattr(profile, 'risk_score', '')}
Risk Summary: {getattr(profile, 'risk_summary', '')}
Financials: {getattr(profile, 'financials', '')}
Technical: {getattr(profile, 'tech_maturity', '')}
Competitive: {getattr(profile, 'top_competitors', '')}
Regulatory: {getattr(profile, 'regulatory', '')}
"""
    response = llm.invoke(prompt)
    return response.content.strip() if hasattr(response, 'content') else str(response)

def format_team_section(profile):
    lines = []
    execs = getattr(profile, 'executives', None) or []
    founder = getattr(profile, 'founder_name', None)
    key_roles = ['founder', 'ceo', 'chief executive officer', 'cfo', 'chief financial officer', 'chairman', 'cto', 'chief technology officer']
    shown = set()
    # Always show founder if present
    if founder:
        founder_exec = next((e for e in execs if e.get('name', '').lower() == founder.lower()), None)
        if founder_exec:
            execs = [founder_exec] + [e for e in execs if e != founder_exec]
    # List key team members
    for exec in execs:
        if isinstance(exec, dict):
            name = exec.get('name', 'Unknown')
            role = exec.get('role', '').title()
            linkedin = exec.get('linkedin', '')
            bio = exec.get('bio', '')
            # Only show if role is in key_roles or if not already shown
            if any(r in role.lower() for r in key_roles) and name.lower() not in shown:
                lines.append(f"**{name} – {role}**")
                if linkedin:
                    lines.append(f"• LinkedIn: {linkedin}")
                if bio:
                    lines.append(f"• Bio: {bio}")
                shown.add(name.lower())
    # Add Overall Team Assessment (critical analysis) at the end
    overall_assessment = getattr(profile, 'overall_team_assessment', None)
    if not overall_assessment:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        team_bios = '\n'.join([e.get('bio', '') for e in execs if isinstance(e, dict) and e.get('bio', '')])
        prompt = f"""
You are a VC analyst. Write a single-paragraph critical assessment of the overall leadership team for an investment memo, based on the following team bios and roles. Focus on strengths, gaps, and relevance to the company's sector. Do not repeat individual bios.

Team Bios:
{team_bios}
"""
        overall_assessment = llm.invoke(prompt).content.strip()
    if overall_assessment:
        lines.append("\nOverall Team Assessment:")
        lines.append(overall_assessment)
    return '\n'.join(lines) if lines else 'Team and management information not available.'

def synthesize_team_section_llm(profile):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    context = f"""
Company: {getattr(profile, 'name', 'N/A')}
Executives: {getattr(profile, 'executives', '')}
Sector: {getattr(profile, 'sector', '')}
"""
    prompt = f"""
You are a top-tier VC analyst. Write a detailed, multi-paragraph, multi-bullet Team & Management section for an investment memo, using only the provided context. For each of the 3 key team members (founder/CEO, CFO, CTO/Chairman), include:
- Name and role
- LinkedIn (if available) 
- Short bio/track record (notable companies, roles, achievements)
Use a critical, VC-style lens. Do not make up facts. Use plain text, no HTML.
Context:
{context}
"""
    response = llm.invoke(prompt)
    return response.content if hasattr(response, 'content') else response

def synthesize_business_model_llm(profile):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Business Model section for an investment memo.
- Do NOT repeat the company's mission, product, or technology—focus only on how the company generates revenue.
- Clearly describe the main revenue streams, customer segments.
- If possible, ALWAYS include a Mermaid diagram (or ASCII schema) summarizing the business model, using the format:
Business Model Schema:
```mermaid
graph TD;
...diagram...
```
- If a Mermaid diagram is not possible, provide only the description.
- Use plain, non-marketing language.
Context:
Company: {getattr(profile, 'name', '')}
Business Model: {getattr(profile, 'business_model', '')}
Product: {getattr(profile, 'product_description', '')}
Customer Segments: {getattr(profile, 'customer_segments', '')}
Go-to-Market: {getattr(profile, 'go_to_market', '')}
Revenue Streams: {getattr(profile, 'revenue_streams', '')}
Partners: {getattr(profile, 'partners', '')}
"""
    response = llm.invoke(prompt)
    raw = response.content.strip() if hasattr(response, 'content') else str(response)
    print(f"[Business Model LLM Output]\n{raw}\n")
    # Post-process: ensure Mermaid diagram is preserved and clearly separated
    import re
    mermaid_match = re.search(r'(```mermaid[\s\S]+?```)', raw)
    if mermaid_match:
        diagram = mermaid_match.group(1)
        text = raw.replace(diagram, '').strip()
        # Remove any redundant 'Business Model Schema:' header in the text (not just at the start)
        text = re.sub(r'(?i)business model schema:\s*', '', text)
        return f"Business Model Schema:\n{diagram}\n\n{text}"
    return raw

def synthesize_esg_section_llm(profile):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the ESG Considerations section for an investment memo.
- Write a single, concise paragraph (3-4 sentences maximum).
- Summarize only the most material ESG factors for this company (environmental, social, and governance), focusing on what matters most for investors.
- Avoid generic, boilerplate, or verbose content. Do not list every ESG subtopic—only mention what is most relevant and specific to the company.
- Use plain, non-marketing language.
Context:
Company: {getattr(profile, 'name', '')}
Sector: {getattr(profile, 'sector', '')}
ESG Summary: {getattr(profile, 'esg_summary', '')}
Sustainability: {getattr(profile, 'sustainability', '')}
Supply Chain: {getattr(profile, 'supply_chain', '')}
Labor Practices: {getattr(profile, 'labor_practices', '')}
Diversity: {getattr(profile, 'diversity', '')}
Governance: {getattr(profile, 'governance', '')}
Controversies: {getattr(profile, 'esg_controversies', '')}
Certifications: {getattr(profile, 'esg_certifications', '')}
"""
    response = llm.invoke(prompt)
    return response.content.strip() if hasattr(response, 'content') else str(response)

def synthesize_analyst_commentary_llm(profile):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Analyst Commentary section for an investment memo.
- Provide a critical, multi-paragraph analysis of the company, covering strengths, weaknesses, opportunities, and risks.
- Only synthesize and comment on information present in the provided context.
- Use plain, non-marketing language.
Context:
Company: {getattr(profile, 'name', '')}
Sector: {getattr(profile, 'sector', '')}
Product: {getattr(profile, 'product_description', '')}
Financials: {getattr(profile, 'financials', '')}
Technical: {getattr(profile, 'tech_maturity', '')}
Competitive: {getattr(profile, 'top_competitors', '')}
ESG: {getattr(profile, 'esg_summary', '')}
Risks: {getattr(profile, 'risk_flags', '')}
"""
    response = llm.invoke(prompt)
    text = response.content.strip() if hasattr(response, 'content') else str(response)
    # Clean stray/blank bullets
    return clean_blank_bullets(text.strip())

def synthesize_exit_strategies_llm(profile):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Investment & Exit Strategies section for an investment memo.
- Write a single, concise paragraph (3-5 sentences maximum) discussing the most likely investment and exit strategies for this company.
- Summarize the key options and rationale, but do NOT list them in detail or use bullets/tables.
- Focus on what is most relevant for investors, based on the company's technology, market, and growth prospects.
- Use plain, non-marketing language.
Context:
Company: {getattr(profile, 'name', '')}
Sector: {getattr(profile, 'sector', '')}
Financials: {getattr(profile, 'financials', '')}
Market Traction: {getattr(profile, 'market_traction', '')}
Partnerships: {getattr(profile, 'partners', '')}
Technology: {getattr(profile, 'tech_maturity', '')}
Competitive: {getattr(profile, 'top_competitors', '')}
"""
    response = llm.invoke(prompt)
    return response.content.strip() if hasattr(response, 'content') else str(response)

def synthesize_followup_section_llm(profile):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Follow-up Questions & Next Steps section for an investment memo.
- Organize the section by topic, using bold headers (e.g., **Technology Validation & IP**, **OEM & Manufacturing Partnerships**).
- Do NOT use bullet points for headers—only for the actual questions or action items under each header.
- For each topic, list 2-4 specific, actionable follow-up questions or next steps as bullet points.
- Use plain, non-marketing language.
Context:
Company: {getattr(profile, 'name', '')}
Sector: {getattr(profile, 'sector', '')}
Risks: {getattr(profile, 'risk_flags', '')}
Technical: {getattr(profile, 'tech_maturity', '')}
Financials: {getattr(profile, 'financials', '')}
Competitive: {getattr(profile, 'top_competitors', '')}
Regulatory: {getattr(profile, 'regulatory', '')}
"""
    response = llm.invoke(prompt)
    # Post-process: ensure headers are bold and not bulleted
    lines = response.content.strip().split('\n') if hasattr(response, 'content') else str(response).split('\n')
    formatted = []
    for i, line in enumerate(lines):
        if line.strip().startswith('•') and not line.strip().startswith('••'):
            formatted.append(line)
        elif line.strip() and not line.strip().startswith('•'):
            header = line.strip().lstrip('•').strip()
            if not header.startswith('**'):
                header = f"**{header}**"
            formatted.append(header)
        else:
            formatted.append(line)
    return '\n'.join(formatted)

def format_followup_section(profile):
    fq = getattr(profile, 'follow_up_questions', None) or ''
    # Remove all '**' and leading '-' from every line
    lines = []
    for line in fq.split('\n'):
        clean_line = line.replace('**', '').strip()
        # Remove leading '-' and any whitespace after it
        if clean_line.startswith('-'):
            clean_line = clean_line[1:].lstrip()
        if clean_line.startswith('• -'):
            clean_line = clean_line[3:].lstrip()
        elif clean_line.startswith('•') and clean_line[1:2] in [' ', '-']:
            clean_line = '•' + clean_line[2:].lstrip('-').lstrip()
        # Header if ends with ':' after cleaning, or if it is a title-like line (contains & or is Title Case)
        is_header = False
        if clean_line.endswith(':'):
            is_header = True
        elif clean_line and (clean_line.istitle() or ('&' in clean_line and clean_line == clean_line.title())):
            is_header = True
        # Special case: if line started with '• -', treat as header if it looks like a section
        if line.strip().startswith('• -') and (':' not in clean_line and (clean_line.istitle() or '&' in clean_line)):
            is_header = True
        if is_header:
            lines.append(f"<HEADER>{clean_line.rstrip(':')}")
        elif clean_line:
            lines.append(f"• {clean_line}")
    return '\n'.join(lines) if lines else 'No follow-up questions generated.'

def clean_discussion_section(discussion):
    lines = discussion.split('\n')
    cleaned = []
    for line in lines:
        # Remove lines that are just a bullet or whitespace
        if line.strip() in ['•', '-', '*', '']:
            continue
        # Remove leading bullet from the first non-empty line
        if cleaned == [] and line.strip().startswith('•'):
            line = line.lstrip('•').strip()
        cleaned.append(line)
    return '\n'.join(cleaned)

def clean_blank_bullets(text):
    lines = text.split('\n')
    cleaned = []
    for i, line in enumerate(lines):
        # Remove lines that are just a bullet or a bullet with whitespace
        if line.strip() in ['•', '-']:
            # Also skip if the next line is blank or whitespace
            if i + 1 < len(lines) and not lines[i + 1].strip():
                continue
            # Or if it's the last line
            if i + 1 == len(lines):
                continue
        cleaned.append(line)
    return '\n'.join(cleaned)

from langchain_openai import ChatOpenAI

def deduplicate_and_paraphrase(text, min_phrase_len=3, max_allowed=2):
    """
    Deduplicate and paraphrase repeated phrases in text.
    - Finds repeated phrases (sequences of min_phrase_len+ words).
    - If a phrase occurs more than max_allowed times, paraphrase extra occurrences.
    - Keeps the first occurrence as-is.
    """
    import re
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    # Find all phrases of min_phrase_len+ words
    words = text.split()
    phrase_counts = {}
    phrase_locs = {}
    for i in range(len(words) - min_phrase_len + 1):
        phrase = ' '.join(words[i:i+min_phrase_len])
        phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        phrase_locs.setdefault(phrase, []).append(i)
    # Only process phrases that occur more than max_allowed times
    for phrase, count in phrase_counts.items():
        if count > max_allowed:
            # Paraphrase all but the first occurrence
            locs = phrase_locs[phrase][1:]
            for loc in locs:
                # Find the phrase in the text and paraphrase it
                pattern = re.escape(phrase)
                matches = list(re.finditer(pattern, text))
                if len(matches) > 1:
                    match = matches[1]  # Paraphrase the second occurrence
                    start, end = match.start(), match.end()
                    context = text[max(0, start-50):min(len(text), end+50)]
                    prompt = f"Paraphrase the following phrase to avoid duplication, keeping the meaning and context:\n\nPhrase: {phrase}\nContext: {context}"
                    paraphrased = llm.invoke(prompt).content.strip()
                    text = text[:start] + paraphrased + text[end:]
    return text

def format_memo(profile: StartupProfile) -> str:
    current_date = datetime.now().strftime("%B %d, %Y")
    def clean(text):
        return text.replace('B253500', '') if isinstance(text, str) else text
    # --- Team line for Company Overview ---
    execs = getattr(profile, 'executives', []) or []
    if execs:
        team_line = "Team: " + ", ".join(
            f"{e.get('name', 'Unknown')} ({e.get('role', '')})" for e in execs[:3]
        )
    else:
        team_line = f"Team: {getattr(profile, 'founder_name', 'TBD')}"

    # --- Funding line for Company Overview ---
    funding_line = f"Funding Stage: {getattr(profile, 'funding_stage', 'Undisclosed')}"
    if getattr(profile, 'funding_amount', None):
        funding_line += f", {profile.funding_amount}"
    if getattr(profile, 'funding_source', None):
        funding_line += f" [Source: {profile.funding_source}]"

    memo_body = f"""
1. DETAILED SUMMARY
{clean(synthesize_detailed_summary(profile))}

2. COMPANY OVERVIEW
Company: {clean(getattr(profile, 'name', None) or 'TBD')}
Sector: {clean(getattr(profile, 'sector', None) or 'TBD')}
Website: {clean(getattr(profile, 'website', None) or 'TBD')}
{funding_line}
{team_line}
{clean(getattr(profile, 'founder_linkedin_formatted', ''))}
    
3. PROBLEM STATEMENT
{clean(synthesize_problem_statement_llm(profile))}
    
4. SOLUTION OVERVIEW
{clean(synthesize_solution_overview_llm(profile))}
    
5. PRODUCT/SERVICE DESCRIPTION
{synthesize_product_description_llm(profile)}

6. MARKET SIZE & ANALYSIS
{format_market_size_section(profile)}
{clean(getattr(profile, 'sector', ''))}

7. COMPETITORS
{format_competitive_landscape(profile)}
{clean(getattr(profile, 'competitive_summary', ''))}

8. BUSINESS MODEL
{synthesize_business_model_llm(profile)}

9. TECHNICAL DUE DILIGENCE
{format_technical_dd_section(profile)}

10. FINANCIAL ANALYSIS
{format_financials_section(profile, current_date)}

11. TEAM & MANAGEMENT
{synthesize_team_section_llm(profile)}

12. ESG CONSIDERATIONS
{synthesize_esg_section_llm(profile)}

13. RISKS & MITIGATIONS
{synthesize_risks_section_llm(profile)}

14. INVESTMENT & EXIT STRATEGIES
{synthesize_exit_strategies_llm(profile)}

15. COUNTERFACTUAL ANALYSIS: WHAT IF WE DON'T INVEST?
{synthesize_counterfactual_section(profile)}

16. FOLLOW-UP QUESTIONS & NEXT STEPS
{synthesize_followup_section_llm(profile)}

17. ADDITIONAL FIGURES & VISUALS
{clean(getattr(profile, 'figures_section', ''))}
"""
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)
    discussion_prompt = f"""
You are a senior VC analyst. Based on the following investment memo, provide a critical discussion and analyst commentary. Highlight key strengths, weaknesses, opportunities, and risks. Be concise but insightful.

MEMO:
{memo_body}
"""
    discussion = llm.invoke(discussion_prompt).content.strip()
    import re
    # Replace any 'Conclusion and Recommendation' or 'Recommendation' with just 'Conclusion' in bold
    discussion = re.sub(r'^(#+\s*)?(Conclusion and Recommendation|Recommendation)(\s*[:\-]?)', r'**Conclusion**', discussion, flags=re.IGNORECASE | re.MULTILINE)
    # Replace any 'Conclusion' header with bold (no hashtags)
    discussion = re.sub(r'^(#+\s*)?Conclusion(\s*[:\-]?)', r'**Conclusion**', discussion, flags=re.IGNORECASE | re.MULTILINE)
    # Remove any remaining markdown headers (hashtags) from the start of lines
    discussion = re.sub(r'^#+\s*', '', discussion, flags=re.MULTILINE)
    # Remove any sentences before the first 'Key Strengths' or similar main header
    match = re.search(r'(Key Strengths[\s\S]*)', discussion, re.IGNORECASE)
    if match:
        discussion = match.group(1).lstrip()
    return deduplicate_memo(f"{memo_body}\n18. AI DISCUSSION AND COMMENTARY\n{clean_discussion_section(discussion)}\n\n---\nGenerated by VC Analysis System on {current_date}\nData Sources: Company documents, market research, competitive intelligence, technical analysis\nAnalysis Framework: Multi-agent AI system with specialized domain expertise\n")


def save_memo_as_pdf(text: str, output_path: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in text.split("\n"):
        clean_line = line.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, clean_line)
    pdf.output(output_path)


# --- HTML memo generation and conversion DISABLED ---
# The following code for HTML memo output and HTML-to-PDF conversion is commented out as DOCX is now the primary output.
# def save_memo_as_html(...):
#     ...
#
# try:
#     HTML(filename=html_path).write_pdf(pdf_path)
#     os.remove(html_path)
#     print(f"PDF memo with logos saved to {pdf_path}")
# except Exception as e:
#     print(f"❌ Error converting HTML to PDF: {e}")
#     print(f"HTML memo with logos saved to {html_path}")


def save_memo_with_template(memo_text, profile, output_path):
    """
    Use template.docx as the base. Replace {{COVER_TEXT}} and {{MEMO_CONTENT}} in-place, inheriting the alignment/formatting of the placeholder paragraph, but always center-align the front page title and date.
    No extra blank lines or page breaks are added—content starts exactly where the placeholder is.
    """
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt
    import re
    import os
    from docx import Document
    import requests
    import tempfile
    template_path = os.path.abspath('template.docx')
    doc = Document(template_path)
    now = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    company_name = getattr(profile, 'name', 'Company')

    # --- Mermaid diagram rendering automation ---
    mermaid_blocks = list(re.finditer(r'```mermaid\s*([\s\S]+?)```', memo_text))
    mermaid_images = {}
    for idx, match in enumerate(mermaid_blocks):
        code = match.group(1).strip()
        try:
            resp = requests.post('https://kroki.io/mermaid/png', data=code.encode('utf-8'))
            if resp.status_code == 200:
                img_path = os.path.join('extraction_cache', f'mermaid_{idx}.png')
                with open(img_path, 'wb') as f:
                    f.write(resp.content)
                mermaid_images[f'<MERMAID_IMAGE_{idx}>'] = img_path
                print(f"[Mermaid] Rendered diagram {idx} to {img_path}")
            else:
                print(f"[Mermaid] Failed to render diagram {idx}: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"[Mermaid] Exception rendering diagram {idx}: {e}")

    # --- Replace {{COVER_TEXT}} in-place, always center-aligned ---
    cover_found = False
    for i, p in enumerate(doc.paragraphs):
        if '{{COVER_TEXT}}' in p.text:
            cover_found = True
            p.clear()
            phrase_run = p.add_run(f"This Investment Memo for {company_name} was Automatically Generated by the VC Intelligence System")
            phrase_run.font.size = Pt(22)
            phrase_run.bold = True
            phrase_run.font.name = 'Times New Roman'
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            date_para = doc.add_paragraph()
            date_run = date_para.add_run(f"Prepared on {now}")
            date_run.font.size = Pt(14)
            date_run.font.name = 'Times New Roman'
            date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p._element.addnext(date_para._element)
            break
    if not cover_found:
        print("[Warning] {{COVER_TEXT}} placeholder not found in template.")

    # --- Replace {{MEMO_CONTENT}} in-place, inheriting alignment ---
    memo_found = False
    section_header_pattern = re.compile(r"^\d+\.\s+[A-Z][A-Z &()]+")
    all_caps_pattern = re.compile(r"^[A-Z0-9 &:'\-]+$")
    known_headers = [
        'Detailed Summary', 'Company Overview', 'Problem Statement', 'Solution Overview', 'Market Size & Analysis',
        'Competitive Landscape', 'Business Model', 'Technical Due Diligence', 'Product Description',
        'Financial Analysis', 'Team & Management', 'ESG Considerations', 'Risks',
        'Investment & Exit Strategies', 'Follow-up Questions & Next Steps', 'Figures & Visuals',
        'Appendix: Additional Tables', 'AI DISCUSSION AND COMMENTARY', 'Key Strengths',
        'Key Weaknesses', 'Opportunities', 'Risks', 'Conclusion',
        'Summary', 'Analysis Framework', 'Strengths', 'Weaknesses',
        'Appendix', 'Figures & Visuals',
        'ESG Alignment', 'Technical Validation Gaps', 'Competitive Landscape Challenges',
        'Execution & Commercialization Risk', 'Technology Risk', 'Competitive Displacement',
        'IP & Freedom to Operate', 'Financial & Funding Risk', 'Market Adoption & Regulatory Risk',
    ]
    known_headers_lower = [h.lower() for h in known_headers]
    for i, p in enumerate(doc.paragraphs):
        if '{{MEMO_CONTENT}}' in p.text:
            memo_found = True
            alignment = p.alignment
            p.clear()
            # --- Split memo into text and diagram blocks ---
            blocks = re.split(r'(```mermaid[\s\S]+?```)', memo_text)
            mermaid_idx = 0
            for block in blocks:
                block = block.strip('\n')
                if block.startswith('```mermaid') and block.endswith('```'):
                    # Mermaid diagram block
                    img_path = mermaid_images.get(f'<MERMAID_IMAGE_{mermaid_idx}>')
                    if img_path and os.path.exists(img_path):
                        para = doc.add_paragraph()
                        para.paragraph_format.first_line_indent = Pt(0)
                        run = para.add_run()
                        try:
                            run.add_picture(img_path, width=Pt(320))
                            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            print(f"[Mermaid] Inserted diagram {mermaid_idx} into DOCX.")
                        except Exception as e:
                            run.add_text(f"[Could not insert Mermaid diagram: {img_path}]")
                            print(f"[Mermaid] Error inserting diagram {mermaid_idx}: {e}")
                    mermaid_idx += 1
                    continue
                # Otherwise, process as text (split by lines)
                for line in block.split('\n'):
                    line_stripped = line.strip().replace('**', '').replace('<HEADER>', '').strip()
                    if line_stripped == '•' or not line_stripped:
                        continue
                    header_cleaned = re.sub(r"\s*\([^)]*\)", "", line_stripped)
                    header_cleaned = re.sub(r"^[-=*•#]+\s*", "", header_cleaned)
                    header_cleaned = header_cleaned.replace("**", "").replace("#", "").strip()
                    is_numbered_header = section_header_pattern.match(header_cleaned)
                    is_all_caps = all_caps_pattern.match(header_cleaned) and len(header_cleaned) > 6
                    is_known_header = header_cleaned.lower() in known_headers_lower
                    if is_numbered_header or is_all_caps or is_known_header:
                        if is_numbered_header:
                            header_style = "Heading 1"
                        elif is_all_caps:
                            header_style = "Heading 2"
                        else:
                            header_style = "Heading 3"
                        para = doc.add_paragraph()
                        para.paragraph_format.space_before = Pt(12)
                        run = para.add_run(header_cleaned)
                        run.font.name = 'Times New Roman'
                        run.font.size = Pt(12)
                        run.bold = True
                        para.alignment = alignment if alignment is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
                        para.paragraph_format.line_spacing = 1.5
                        para.paragraph_format.space_after = Pt(6)
                        para.paragraph_format.first_line_indent = Pt(0)
                        last_para = para
                        continue
                    if (line_stripped.startswith('•') or line_stripped.startswith('-') or line_stripped.startswith('*')):
                        bullet_line = re.sub(r"^[•\-*#]+\s*", "• ", line_stripped)
                        bullet_line = bullet_line.replace('*', '').replace('-', '').strip()
                        if not bullet_line.startswith('•'):
                            bullet_line = '• ' + bullet_line.lstrip()
                        para = doc.add_paragraph()
                        run = para.add_run(bullet_line)
                        run.font.name = 'Times New Roman'
                        run.font.size = Pt(12)
                        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                        para.paragraph_format.line_spacing = 1.5
                        para.paragraph_format.first_line_indent = Pt(0)
                        last_para = para
                        continue
                    # Normal paragraph
                    para = doc.add_paragraph()
                    run = para.add_run(line_stripped)
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
                    para.alignment = alignment if alignment is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
                    para.paragraph_format.line_spacing = 1.5
                    para.paragraph_format.first_line_indent = Pt(0)
                    last_para = para
            break
    if not memo_found:
        print("[Warning] {{MEMO_CONTENT}} placeholder not found in template.")
    doc.save(output_path)
    print(f"✅ DOCX memo generated from template and saved to {output_path}")
    for img_path in mermaid_images.values():
        try:
            if os.path.exists(img_path):
                os.remove(img_path)
                print(f"[Mermaid] Deleted temporary image {img_path}")
        except Exception as e:
            print(f"[Mermaid] Error deleting temporary image {img_path}: {e}")


# --- DOCX to PDF conversion ---
def convert_docx_to_pdf(docx_path, output_dir=None):
    if output_dir is None:
        output_dir = os.path.dirname(docx_path)
    try:
        subprocess.run([
            "soffice", "--headless", "--convert-to", "pdf", "--outdir", output_dir, docx_path
        ], check=True)
        pdf_path = os.path.splitext(docx_path)[0] + ".pdf"
        print(f"✅ PDF generated from DOCX: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"❌ Error converting DOCX to PDF: {e}")
        return None


# --- Counterfactual Analysis Section ---
def synthesize_counterfactual_section(profile):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a senior VC analyst at a top investment firm. Write a concise, professional paragraph for an investment memo answering: 'What are the likely outcomes and opportunity costs if we do NOT invest in this company?' Consider market, competitive, and strategic risks, and the potential for missed upside. Use the style and tone of leading VC/investment firms. Do not use marketing language.
Context:
Company: {getattr(profile, 'name', '')}
Sector: {getattr(profile, 'sector', '')}
Top Competitors: {getattr(profile, 'top_competitors', '')}
Market Size: {getattr(profile, 'TAM', '')}
Stage: {getattr(profile, 'funding_stage', '')}
"""
    response = llm.invoke(prompt)
    return response.content.strip() if hasattr(response, 'content') else str(response)

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_file1> [<path_to_file2> ...]")
        sys.exit(1)

    file_paths = sys.argv[1:]
    for file_path in file_paths:
        print(f"Extracting text and structured data from: {file_path}")
        # --- Caching logic ---
        extracted = load_from_cache(file_path)
        if extracted is None:
            try:
                extracted = extract_text(file_path, return_structured=True)
                save_to_cache(file_path, extracted)
                print(f"[CACHE] Saved extraction for {file_path}")
            except Exception as e:
                print(f"Error extracting {file_path}: {e}")
                continue
        else:
            print(f"[CACHE] Loaded extraction for {file_path}")
        text = extracted["text"]
        tables = extracted["tables"]
        figures = extracted["figures"]

        clear_collection()
        profile = StartupProfile()
        profile = run_all_sequential_with_text(text, profile, file_path)
        # Populate structured data
        profile.tables = tables
        profile.figures = figures

        # --- Extract images from PDF and generate chart ---
        output_dir = "out"
        os.makedirs(output_dir, exist_ok=True)
        company_name = profile.name or "unknown_company"
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        images_dir = os.path.join(output_dir, f"{company_name.replace(' ', '_')}_images_{date_str}")
        extracted_image_paths = extract_images_from_pdf(file_path, images_dir)
        # Example: Generate a sample market chart if market size data is available
        market_chart_path = None
        if hasattr(profile, "market_size_by_year") and profile.market_size_by_year:
            chart_path = os.path.join(output_dir, f"{company_name.replace(' ', '_')}_market_chart_{date_str}.png")
            generate_sample_market_chart(profile.market_size_by_year, chart_path)
            market_chart_path = chart_path
        # Attach visuals to profile for use in memo formatting
        profile.extracted_image_paths = extracted_image_paths
        profile.market_chart_path = market_chart_path

        memo_text = format_memo(profile)
        print(memo_text)

        docx_filename = f"memo_{company_name.replace(' ', '_')}_{date_str}.docx"
        docx_path = os.path.join(output_dir, docx_filename)
        save_memo_with_template(memo_text, profile, docx_path)
        convert_docx_to_pdf(docx_path)


if __name__ == "__main__":
    main()


