import sys
import os
from datetime import datetime
from core.download_utils import extract_text
from chains.pitch_deck_chain import run_pitch_deck_chain
from chains.technical_dd_chain import run_technical_dd_chain
from agents.founder_profiling_agent import run_founder_profiling_chain
from chains.market_sizing_chain import run_market_sizing_chain
from chains.financial_analysis_chain import run_financial_analysis_chain
from chains.competitive_intel_chain import run_competitive_intel_chain
from chains.risk_assessment_chain import run_risk_assessment_chain
from core.schemas import StartupProfile
from core.vector_store import clear_collection
from fpdf import FPDF

# --- Perplexity AI and LLM-based memo generation integration ---
import openai
import requests
from dotenv import load_dotenv
load_dotenv()

def search_perplexity(query, num_results=3):
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        print("[Warning] PERPLEXITY_API_KEY not set in environment.")
        return None
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "sonar-reasoning-pro",
        "messages": [
            {"role": "system", "content": "You are a helpful research assistant. Answer with up-to-date, factual, and cited information."},
            {"role": "user", "content": query}
        ],
        "max_tokens": 512,
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                return result
        else:
            print(f"Perplexity API error: {response.status_code} {response.text}")
            return None
    except Exception as e:
        print(f"Perplexity API exception: {e}")
        return None

def generate_llm_memo(profile, extra_context=None):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set.")
    client = openai.OpenAI(api_key=api_key)
    company_query = f"What is the latest news, funding, and overview for {profile.name or 'the company'}?"
    company_info = search_perplexity(company_query)
    company_info_str = company_info if company_info else "No Perplexity results found."
    context = f"""
Company: {profile.name or 'N/A'}\n
Sector: {profile.sector or 'N/A'}\n
Founder: {profile.founder_name or 'N/A'}\n
Website: {profile.website or 'N/A'}\n
Funding Stage: {profile.funding_stage or 'N/A'}\n
TAM: {profile.TAM or 'N/A'}\n
SAM: {profile.SAM or 'N/A'}\n
SOM: {profile.SOM or 'N/A'}\n
Technology Maturity: {profile.tech_maturity or 'N/A'}\n\nMoat Strength: {profile.moat_strength or 'N/A'}\n\nFounder Fit Score: {profile.founder_fit_score or 'N/A'}\n\nPrior Exits: {profile.prior_exits or 'N/A'}\n\nCash Burn (12m): {profile.cash_burn_12m or 'N/A'}\n\nRunway (months): {profile.runway_months or 'N/A'}\n\nImplied Valuation: {profile.implied_valuation or 'N/A'}\n\nRisk Score: {profile.risk_score or 'N/A'}\n\nRisk Flags: {profile.risk_flags or 'N/A'}\n\nTop Competitors: {', '.join(profile.top_competitors) if profile.top_competitors else 'N/A'}\n\n"""
    context += f"\n[Perplexity Company Info]\n{company_info_str}\n"
    if extra_context:
        context += f"\nAdditional Context:\n{extra_context}\n"
    prompt = f"""
You are a top-tier senior venture capitalist with experience in evaluating early-stage startups. Your role is to generate comprehensive investment memorandums based on provided information. Format the output using plain text (no HTML). Limit yourself to the data given in context and do not make up things or people will get fired. Each section should be detailed and comprehensive, with a particular focus on providing extensive information in the product description section. Generating all required sections of the memo is a must. You should approach this with a critical lens, balancing skepticism and insight while recognizing that venture capital focuses on the potential if things go well. For instance, in the diligence section, you could explain the company's go-to-market strategy or product roadmap, but it's perfectly fine to highlight anything unusual or potentially risky.

Generate a detailed and comprehensive investment memorandum based on the following information:\n\n{context}\n\nStructure the memo with the following sections (plain text, no HTML):\n\n1. Executive Summary\n2. Market Opportunity and Sizing\n3. Competitive Landscape\n4. Product/Service Description\n5. Business Model\n6. Team\n7. Go-to-Market Strategy\n8. Main Risks\n9. What Can Go Massively Right\n10. Tech Evaluation and Scores\n11. Follow-up Questions\n"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[Error generating memo with OpenAI: {e}]"

# --- End Perplexity/LLM integration ---

def run_all_sequential_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    print(f"🔍 Processing extracted text ({len(full_text)} characters)")
    print(f"📄 Starting with fresh profile: {profile.name}")
    profile = run_pitch_deck_chain_with_text(full_text, profile)
    print(f"📊 After pitch deck: Company={profile.name}, Founder={profile.founder_name}")
    profile = run_technical_dd_chain_with_text(full_text, profile)
    print(f"🔧 After tech DD: Maturity={profile.tech_maturity}, Moat={profile.moat_strength}")
    profile = run_founder_profiling_chain_with_text(full_text, profile)
    print(f"👤 After founder profiling: Score={profile.founder_fit_score}")
    profile = run_market_sizing_chain_with_text(full_text, profile)
    print(f"📈 After market sizing: TAM={profile.TAM}, SAM={profile.SAM}, SOM={profile.SOM}")
    profile = run_financial_analysis_chain_with_text(full_text, profile)
    print(f"💰 After financial analysis: Burn={profile.cash_burn_12m}, Runway={profile.runway_months}")
    profile = run_competitive_intel_chain_with_text(full_text, profile)
    print(f"🏆 After competitive intel: {len(profile.top_competitors)} competitors found")
    profile = run_risk_assessment_chain_with_text(full_text, profile)
    print(f"⚠️ After risk assessment: Score={profile.risk_score}, {len(profile.risk_flags)} flags")
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

def format_memo(profile: StartupProfile) -> str:
    current_date = datetime.now().strftime("%B %d, %Y")
    market_penetration = (profile.SOM / profile.TAM * 100) if profile.TAM and profile.TAM > 0 and profile.SOM else 0
    burn_rate_months = profile.runway_months if profile.runway_months else 0
    valuation_multiple = (profile.implied_valuation / profile.TAM * 100) if profile.TAM and profile.implied_valuation else 0
    maturity_map = {"prototype": 2, "beta": 4, "production": 8, "enterprise": 10, "unknown": 1, None: 1}
    tech_score = maturity_map.get(str(profile.tech_maturity).lower() if profile.tech_maturity else None, 1)
    risk_level = "LOW" if profile.risk_score and profile.risk_score < 0.3 else "MEDIUM" if profile.risk_score and profile.risk_score < 0.7 else "HIGH"
    return f"""
INVESTMENT MEMO: {profile.name or 'COMPANY ANALYSIS'}\n{'=' * 60}\n\nEXECUTIVE SUMMARY\n{'=' * 60}\nAnalysis Date: {current_date}\nCompany: {profile.name or 'TBD'}\nSector: {profile.sector or 'TBD'}\nFounder: {profile.founder_name or 'TBD'}\nWebsite: {profile.website or 'TBD'}\nFunding Stage: {profile.funding_stage or 'TBD'}\n\nINVESTMENT THESIS\n{'-' * 40}\n{profile.name or 'The company'} represents a compelling investment opportunity in the {profile.sector or 'emerging'} sector, \nleveraging {profile.tech_maturity or 'advanced technology'} to address a ${profile.TAM or 'significant'}M market opportunity. \nThe company's {profile.moat_strength or 'competitive advantages'} provide sustainable differentiation in a rapidly evolving landscape.\n\nKEY INVESTMENT DRIVERS:\n• Market Opportunity: ${profile.TAM or 'N/A'}M TAM with ${profile.SAM or 'N/A'}M SAM (${profile.SOM or 'N/A'}M SOM)\n• Technology Maturity: {profile.tech_maturity or 'N/A'} stage with {profile.moat_strength or 'competitive moat'}\n• Team Strength: Founder fit score {profile.founder_fit_score or 'N/A'} with {profile.prior_exits or '0'} prior exits\n• Financial Position: ${profile.cash_burn_12m or 'N/A'}M burn rate, {burn_rate_months} months runway\n\nMARKET INTELLIGENCE\n{'=' * 60}\n\nMARKET SIZING & OPPORTUNITY\n{'-' * 40}\nTotal Addressable Market (TAM): ${profile.TAM or 'N/A'}M\nServiceable Available Market (SAM): ${profile.SAM or 'N/A'}M  \nServiceable Obtainable Market (SOM): ${profile.SOM or 'N/A'}M\nMarket Penetration Potential: {market_penetration:.1f}%\n\nMarket Dynamics:\n• Current market challenges addressed by {profile.moat_strength or 'company solutions'}\n• Growth drivers in {profile.sector or 'target sector'} creating tailwinds\n• {profile.tech_maturity or 'Technology'} adoption accelerating market expansion\n\nCOMPETITIVE LANDSCAPE ANALYSIS\n{'-' * 40}\n{chr(10).join([f"• {comp.name}: {comp.differentiator or 'Competitive positioning to be analyzed'}" for comp in profile.top_competitors]) if profile.top_competitors else 'Competitive analysis pending - market positioning to be evaluated'}\n\nCompetitive Advantages:\n• {profile.moat_strength or 'Key differentiators provide sustainable competitive edge'}\n• {profile.tech_maturity or 'Technology'} maturity creates barriers to entry\n• {profile.sector or 'Sector'} expertise positions company for market leadership\n\nTECHNICAL DUE DILIGENCE\n{'=' * 60}\n\nTECHNOLOGY ASSESSMENT\n{'-' * 40}\nMaturity Level: {profile.tech_maturity or 'N/A'}\nTechnical Moat: {profile.moat_strength or 'N/A'}\nScalability: {profile.tech_maturity or 'Technology'} architecture supports growth\nSecurity: {profile.tech_maturity or 'Technology'} includes robust security measures\n\nTechnical Differentiation:\n• {profile.moat_strength or 'Unique technical advantages'}\n• {profile.tech_maturity or 'Technology'} stack provides competitive edge\n• Architecture designed for {profile.TAM or 'market'} scale\n\nTEAM & FOUNDER ANALYSIS\n{'=' * 60}\n\nFOUNDER PROFILE\n{'-' * 40}\nName: {profile.founder_name or 'TBD'}\nFounder Fit Score: {profile.founder_fit_score or 'N/A'} / 1.0\nPrior Exits: {profile.prior_exits or '0'}\nSector Experience: {profile.sector or 'TBD'}\n\nTeam Assessment:\n• {profile.founder_fit_score or 'Founder'} demonstrates {profile.founder_fit_score or 'expertise'} in {profile.sector or 'the sector'}\n• {profile.prior_exits or '0'} prior exits indicate proven track record\n• {profile.tech_maturity or 'Technical'} background aligns with company needs\n\nFINANCIAL ANALYSIS\n{'=' * 60}\n\nFINANCIAL METRICS\n{'-' * 40}\nImplied Valuation: ${profile.implied_valuation or 'N/A'}M\nCash Burn (12 months): ${profile.cash_burn_12m or 'N/A'}M\nRunway: {burn_rate_months} months\nValuation Multiple: {valuation_multiple:.1f}% of TAM\n\nFinancial Health Assessment:\n• {burn_rate_months} months runway provides {burn_rate_months} months of operational runway\n• ${profile.cash_burn_12m or 'N/A'}M burn rate indicates {profile.cash_burn_12m or 'sustainable'} operations\n• ${profile.implied_valuation or 'N/A'}M valuation reflects {profile.implied_valuation or 'market'} positioning\n\nRISK ASSESSMENT\n{'=' * 60}\n\nRISK PROFILE\n{'-' * 40}\nOverall Risk Level: {risk_level}\nRisk Score: {profile.risk_score or 'N/A'} / 1.0\n\nIDENTIFIED RISKS:\n{chr(10).join([f"{i+1}. {risk}" for i, risk in enumerate(profile.risk_flags)]) if profile.risk_flags else 'Risk assessment pending - comprehensive risk analysis required'}\n\nRisk Mitigation Strategies:\n• {profile.moat_strength or 'Competitive advantages'} help mitigate market risks\n• {profile.tech_maturity or 'Technology'} maturity reduces technical risks\n• {profile.founder_fit_score or 'Team'} expertise addresses execution risks\n\nINVESTMENT RECOMMENDATION\n{'=' * 60}\n\nINVESTMENT THESIS VALIDATION\n{'-' * 40}\nBased on comprehensive analysis of {profile.name or 'the company'}, the investment thesis is supported by:\n\nSTRENGTHS:\n• Strong market opportunity (${profile.TAM or 'N/A'}M TAM)\n• {profile.moat_strength or 'Competitive advantages'} provide sustainable differentiation\n• {profile.founder_fit_score or 'Team'} expertise aligns with company needs\n• {profile.tech_maturity or 'Technology'} maturity supports growth objectives\n\nCONCERNS:\n• {', '.join(profile.risk_flags[:3]) if profile.risk_flags else 'Market and execution risks to be monitored'}\n• {burn_rate_months} months runway requires careful cash management\n• {profile.tech_maturity or 'Technology'} evolution may impact competitive position\n\nRECOMMENDATION: {'PROCEED' if (profile.founder_fit_score or 0) > 0.6 and (profile.TAM or 0) > 100 else 'FURTHER DUE DILIGENCE' if (profile.founder_fit_score or 0) > 0.4 else 'PASS'}\n\nDUE DILIGENCE NEXT STEPS\n{'-' * 40}\n1. Technical deep-dive on {profile.tech_maturity or 'technology'} architecture and scalability\n2. Customer validation and market feedback collection\n3. Financial model validation and cash flow projections\n4. Competitive landscape deep-dive and positioning analysis\n5. Team reference checks and background verification\n6. Legal and regulatory compliance review\n7. Market size validation and growth projections\n8. Risk mitigation strategy development\n9. Investment structure and terms negotiation\n\nANALYTICAL FRAMEWORK SCORES\n{'-' * 40}\nMarket Opportunity: {min(10, max(1, int((profile.TAM or 0) / 100)))}/10\nTeam Quality: {min(10, max(1, int((profile.founder_fit_score or 0.5) * 10)))}/10\nTechnology: {tech_score}/10\nCompetitive Position: {min(10, max(1, int((profile.SAM or 0) / 50)))}/10\nFinancial Health: {min(10, max(1, int((burn_rate_months / 12) * 10)))}/10\n\nOVERALL SCORE: {min(10, max(1, int(((profile.TAM or 0) / 100 + (profile.founder_fit_score or 0.5) * 10 + (profile.SAM or 0) / 50 + burn_rate_months / 12) / 4)))}/10\n\n---\nGenerated by VC Analysis System on {current_date}\nData Sources: Company documents, market research, competitive intelligence, technical analysis\nAnalysis Framework: Multi-agent AI system with specialized domain expertise\n"""

def save_memo_as_pdf(text: str, output_path: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in text.split("\n"):
        clean_line = line.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, clean_line)
    pdf.output(output_path)

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_pdf_memo.py <path_to_file1> [<path_to_file2> ...] [--llm]")
        sys.exit(1)
    file_paths = []
    use_llm = False
    for arg in sys.argv[1:]:
        if arg == "--llm":
            use_llm = True
        else:
            file_paths.append(arg)
    for file_path in file_paths:
        print(f"Extracting text from: {file_path}")
        try:
            text = extract_text(file_path)
        except Exception as e:
            print(f"Error extracting {file_path}: {e}")
            continue
        clear_collection()
        profile = StartupProfile()
        profile = run_all_sequential_with_text(text, profile)
        if use_llm:
            memo_text = generate_llm_memo(profile, extra_context=text)
        else:
            memo_text = format_memo(profile)
        print(memo_text)
        output_dir = "out"
        os.makedirs(output_dir, exist_ok=True)
        company_name = profile.name or "unknown_company"
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"memo_{company_name.replace(' ', '_')}_{date_str}.pdf"
        output_path = os.path.join(output_dir, filename)
        save_memo_as_pdf(memo_text, output_path)
        print(f"\nPDF memo saved to {output_path}")

if __name__ == "__main__":
    main() 