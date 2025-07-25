from langchain_openai import ChatOpenAI
from core.schemas import StartupProfile
import re

def clean_blank_bullets(text):
    """Remove empty bullet points and clean up formatting."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped and stripped not in ['•', '-', '*', '• ', '- ', '* ']:
            cleaned.append(line)
    return '\n'.join(cleaned)

def run_detailed_summary_chain(profile: StartupProfile) -> str:
    """Generate detailed summary for the memo."""
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

def run_problem_statement_chain(profile: StartupProfile) -> str:
    """Generate problem statement for the memo."""
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

def run_solution_overview_chain(profile: StartupProfile) -> str:
    """Generate solution overview for the memo."""
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

def run_business_model_chain(profile: StartupProfile) -> str:
    """Generate business model section for the memo."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Business Model section for an investment memo.
- Focus on how the company COULD generate revenue based on available information.
- Use tentative language: "appears to", "seems to", "may", "could", "based on available information"
- Do NOT present assumptions as facts about current revenue streams or business model
- Clearly describe potential revenue streams, customer segments, and go-to-market strategies
- If possible, ALWAYS include a Mermaid diagram (or ASCII schema) summarizing the potential business model, using the format:
Business Model Schema:
```mermaid
graph TD;
...diagram...
```
- If a Mermaid diagram is not possible, provide only the description.
- Use plain, non-marketing language.
- CRITICAL: Use bold formatting (**text**) for ALL section headers, NOT markdown headers (###).
- Common headers to bold: **Business Model Overview**, **Potential Revenue Streams**, **Customer Segments**, **Go-to-Market Strategies**, **Business Model Schema**, **Additional Research Needed**
- If information is limited, explicitly state what additional research is needed
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
    mermaid_match = re.search(r'(```mermaid[\s\S]+?```)', raw)
    if mermaid_match:
        diagram = mermaid_match.group(1)
        text = raw.replace(diagram, '').strip()
        # Remove any redundant 'Business Model Schema:' header in the text (not just at the start)
        text = re.sub(r'(?i)business model schema:\s*', '', text)
        # Convert markdown headers to bold formatting
        text = re.sub(r'^###\s*\*\*(.*?)\*\*', r'**\1**', text, flags=re.MULTILINE)
        text = re.sub(r'^###\s*(.*?)$', r'**\1**', text, flags=re.MULTILINE)
        return f"Business Model Schema:\n{diagram}\n\n{text}"
    # Convert markdown headers to bold formatting for text without diagrams
    raw = re.sub(r'^###\s*\*\*(.*?)\*\*', r'**\1**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^###\s*(.*?)$', r'**\1**', raw, flags=re.MULTILINE)
    
    # Also convert plain text headers to bold formatting
    raw = re.sub(r'^Business Model Overview$', r'**Business Model Overview**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Potential Revenue Streams$', r'**Potential Revenue Streams**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Customer Segments$', r'**Customer Segments**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Go-to-Market Strategies$', r'**Go-to-Market Strategies**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Business Model Schema$', r'**Business Model Schema**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Additional Research Needed$', r'**Additional Research Needed**', raw, flags=re.MULTILINE)
    
    # Convert any remaining plain text headers that might be missed
    raw = re.sub(r'^([A-Z][a-z\s]+):$', r'**\1:**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^([A-Z][A-Za-z\s]+)$', r'**\1**', raw, flags=re.MULTILINE)
    
    return raw

def run_risks_section_chain(profile: StartupProfile) -> str:
    """Generate risks section for the memo."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Risks section for an investment memo.
- List the POTENTIAL risks relevant to this company and product, sector with a specific explanation for each risk.
- Make each risk specific to the company's technology, market, or business context. Avoid generic or boilerplate risks.
- If possible cover market, technical, operational, regulatory and financial risks. Use a critical, VC-style lens.
- Use bullet points, with each risk followed by a short, specific explanation.
- Use plain, non-marketing language.
- Use bold formatting (**text**) for headers, NOT markdown headers (###).

IMPORTANT: Use tentative language and clearly indicate when you are making assumptions or interpretations.
- Use phrases like "appears to be", "seems to", "may be", "could be", "based on available information"
- Do not present assumptions as facts about current risks
- If information is limited, explicitly state what additional research is needed

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
    raw = response.content.strip() if hasattr(response, 'content') else str(response)
    # Convert markdown headers to bold formatting
    raw = re.sub(r'^###\s*\*\*(.*?)\*\*', r'**\1**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^###\s*(.*?)$', r'**\1**', raw, flags=re.MULTILINE)
    return raw

def run_team_section_chain(profile: StartupProfile) -> str:
    """Generate team section for the memo."""
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
- Use bold formatting (**text**) for headers, NOT markdown headers (###).

IMPORTANT: Use tentative language and clearly indicate when you are making assumptions or interpretations.
- Use phrases like "appears to be", "seems to", "may be", "could be", "based on available information"
- Do not present assumptions as facts about team members' backgrounds
- If information is limited, explicitly state what additional research is needed

Context:
{context}
"""
    response = llm.invoke(prompt)
    raw = response.content if hasattr(response, 'content') else response
    # Convert markdown headers to bold formatting
    raw = re.sub(r'^###\s*\*\*(.*?)\*\*', r'**\1**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^###\s*(.*?)$', r'**\1**', raw, flags=re.MULTILINE)
    return raw

def run_esg_section_chain(profile: StartupProfile) -> str:
    """Generate ESG section for the memo."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the ESG Considerations section for an investment memo.
- Write a single, concise paragraph (3-4 sentences maximum).
- Summarize only the most material ESG factors for this company (environmental, social, and governance), focusing on what matters most for investors.
- Avoid generic, boilerplate, or verbose content. Do not list every ESG subtopic—only mention what is most relevant and specific to the company.
- Use plain, non-marketing language.
- Use bold formatting (**text**) for headers, NOT markdown headers (###).
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
    raw = response.content.strip() if hasattr(response, 'content') else str(response)
    # Convert markdown headers to bold formatting
    raw = re.sub(r'^###\s*\*\*(.*?)\*\*', r'**\1**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^###\s*(.*?)$', r'**\1**', raw, flags=re.MULTILINE)
    return raw

def run_analyst_commentary_chain(profile: StartupProfile) -> str:
    """Generate analyst commentary for the memo."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Analyst Commentary section for an investment memo.
- Provide a critical, multi-paragraph analysis of the company, covering strengths, weaknesses, opportunities, and risks and give conclusion.
- Only synthesize and comment on information present in the provided context.
- Use plain, non-marketing language.
- Use bold formatting (**text**) for headers, NOT markdown headers (###).
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
    # Convert markdown headers to bold formatting
    text = re.sub(r'^###\s*\*\*(.*?)\*\*', r'**\1**', text, flags=re.MULTILINE)
    text = re.sub(r'^###\s*(.*?)$', r'**\1**', text, flags=re.MULTILINE)
    return clean_blank_bullets(text)

def run_exit_strategies_chain(profile: StartupProfile) -> str:
    """Generate exit strategies section for the memo."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Investment & Exit Strategies section for an investment memo.
- Write a single, concise paragraph (3-5 sentences maximum) discussing the most likely investment and exit strategies for this company.
- Summarize the key options and rationale, but do NOT list them in detail or use bullets/tables.
- Focus on what is most relevant for investors, based on the company's technology, market, and growth prospects.
- Use plain, non-marketing language.
- Use bold formatting (**text**) for headers, NOT markdown headers (###).
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
    raw = response.content.strip() if hasattr(response, 'content') else str(response)
    # Convert markdown headers to bold formatting
    raw = re.sub(r'^###\s*\*\*(.*?)\*\*', r'**\1**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^###\s*(.*?)$', r'**\1**', raw, flags=re.MULTILINE)
    return raw

def run_followup_section_chain(profile: StartupProfile) -> str:
    """Generate follow-up section for the memo."""
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