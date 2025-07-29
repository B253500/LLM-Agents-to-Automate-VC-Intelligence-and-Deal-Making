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
    - DO NOT include any headers or section titles in your response.
    - Start directly with the summary.
    Context:
    Company: {getattr(profile, 'name', '')}
    Sector: {getattr(profile, 'sector', '')}
    Product: {getattr(profile, 'product_description', '')}
    Stage: {getattr(profile, 'funding_stage', '')}
    """
    response = llm.invoke(prompt)
    content = response.content.strip() if hasattr(response, 'content') else str(response)
    
    # Remove any headers that might have been generated
    import re
    # Remove common header patterns
    content = re.sub(r'^#+\s*Detailed Summary\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^\*\*Detailed Summary\*\*\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^Detailed Summary\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^#+\s*DETAILED SUMMARY\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^\*\*DETAILED SUMMARY\*\*\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^DETAILED SUMMARY\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    
    # Clean up any extra whitespace
    content = re.sub(r'^\s*\n+', '', content)  # Remove leading blank lines
    content = re.sub(r'\n+\s*$', '', content)  # Remove trailing blank lines
    
    return content

def run_problem_statement_chain(profile: StartupProfile) -> str:
    """Generate problem statement for the memo."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Problem Statement section for an investment memo.
- Write a comprehensive problem statement that is EXACTLY 4-5 sentences.
- Clearly state the main problem or pain point that the company's product/service is solving.
- Provide context about the market need, industry challenges, and why this problem matters.
- Include specific details about the problem's scope, impact, and urgency.
- Try to be specific to the company's sector, product, and market context.
- Do NOT use generic or sector-wide statements—focus on the actual problem this company addresses.
- Do NOT mention the company's solution or product features—only describe the problem.
- Use plain, non-marketing language.
- DO NOT include any headers or section titles in your response.
- Start directly with the problem description.
- CRITICAL: Ensure your response is exactly 4-5 sentences, no more, no less.

Context:
Company: {getattr(profile, 'name', '')}
Sector: {getattr(profile, 'sector', '')}
Product: {getattr(profile, 'product_description', '')}
Stage: {getattr(profile, 'funding_stage', '')}
Business Model: {getattr(profile, 'business_model', '')}
Go-to-Market: {getattr(profile, 'go_to_market', '')}
"""
    response = llm.invoke(prompt)
    content = response.content.strip() if hasattr(response, 'content') else str(response)
    
    # Remove any headers that might have been generated
    import re
    # Remove common header patterns
    content = re.sub(r'^#+\s*Problem Statement\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^\*\*Problem Statement\*\*\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^Problem Statement\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^#+\s*PROBLEM STATEMENT\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^\*\*PROBLEM STATEMENT\*\*\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^PROBLEM STATEMENT\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    
    # Clean up any extra whitespace
    content = re.sub(r'^\s*\n+', '', content)  # Remove leading blank lines
    content = re.sub(r'\n+\s*$', '', content)  # Remove trailing blank lines
    
    return content

def run_solution_overview_chain(profile: StartupProfile) -> str:
    """Generate solution overview for the memo."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Solution Overview section for an investment memo.
- Write a comprehensive solution overview that is EXACTLY 4-5 sentences.
- Clearly explain how the company's product/service solves the problem described in the Problem Statement.
- Provide context about the solution's approach, methodology, and key differentiators.
- Include specific details about how the solution addresses the core problem and its advantages.
- Focus ONLY on the core solution. Don't describe in detail the product, just the solution.
- Use plain, non-marketing language.
- DO NOT include any headers or section titles in your response.
- Start directly with the solution explanation.
- CRITICAL: Ensure your response is exactly 4-5 sentences, no more, no less.

Context:
Company: {getattr(profile, 'name', '')}
Sector: {getattr(profile, 'sector', '')}
Product: {getattr(profile, 'product_description', '')}
Stage: {getattr(profile, 'funding_stage', '')}
"""
    response = llm.invoke(prompt)
    content = response.content.strip() if hasattr(response, 'content') else str(response)
    
    # Remove any headers that might have been generated
    import re
    # Remove common header patterns
    content = re.sub(r'^#+\s*Solution Overview\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^\*\*Solution Overview\*\*\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^Solution Overview\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^#+\s*SOLUTION OVERVIEW\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^\*\*SOLUTION OVERVIEW\*\*\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^SOLUTION OVERVIEW\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    
    # Clean up any extra whitespace
    content = re.sub(r'^\s*\n+', '', content)  # Remove leading blank lines
    content = re.sub(r'\n+\s*$', '', content)  # Remove trailing blank lines
    
    return content

def run_business_model_chain(profile: StartupProfile) -> str:
    """Generate business model section for the memo."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Business Model section for an investment memo.
- Focus on how the company COULD generate revenue based on available information.
- Use tentative language: "appears to", "seems to", "may", "could", "based on available information"
- Do NOT present assumptions as facts about current revenue streams or business model
- Clearly describe potential revenue streams, customer segments, and go-to-market strategies
- If possible, ALWAYS include a SIMPLE Mermaid diagram focusing on REVENUE STREAMS, using the format:
```mermaid
graph TD;
...SIMPLE diagram focusing on revenue streams...
```
- Create a SIMPLE diagram that shows:
  * Company/Product (1 node)
  * Revenue Streams (2-3 main streams)
  * Customer Segments (2-3 main segments)
- Use 5-7 nodes maximum for clarity
- Focus on revenue streams as the central element
- Use simple connections like "→" 
- Keep it simple and readable for VC memos
- If a Mermaid diagram is not possible, provide only the description.
- DO NOT include "Business Model Schema:" header in your response - it will be added automatically.
- Use plain, non-marketing language.
- CRITICAL: Use bold formatting (**text**) for ALL section headers, NOT markdown headers (###).
- Common headers to bold: **Business Model Overview**, **Potential Revenue Streams**, **Customer Segments**, **Strategy**, **Business Model Schema**, **Additional Research Needed**
- IMPORTANT: Use "Strategy" instead of "Go-to-Market Strategies" as the header
- For "Additional Research Needed" section, provide ONLY ONE SENTENCE summarizing what additional information is needed
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
        # Also remove any standalone "Business Model Schema" lines that might be in the content
        text = re.sub(r'^Business Model Schema$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\*\*Business Model Schema\*\*$', '', text, flags=re.MULTILINE)
        # Convert markdown headers to bold formatting
        text = re.sub(r'^###\s*\*\*(.*?)\*\*', r'**\1**', text, flags=re.MULTILINE)
        text = re.sub(r'^###\s*(.*?)$', r'**\1**', text, flags=re.MULTILINE)
        return f"**Business Model Schema:**\n{diagram}\n\n{text}"
    # Convert markdown headers to bold formatting for text without diagrams
    raw = re.sub(r'^###\s*\*\*(.*?)\*\*', r'**\1**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^###\s*(.*?)$', r'**\1**', raw, flags=re.MULTILINE)
    
    # Fix headers that might be bullet points instead of bold
    raw = re.sub(r'^•\s*Business Model Overview$', r'**Business Model Overview**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*Potential Revenue Streams$', r'**Potential Revenue Streams**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*Customer Segments$', r'**Customer Segments**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*Go-to-Market Strategies$', r'**Strategy**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*Strategy$', r'**Strategy**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*Business Model Schema$', r'**Business Model Schema**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*Additional Research Needed$', r'**Additional Research Needed**', raw, flags=re.MULTILINE)
    
    # Fix market section headers that might be bullet points instead of bold
    raw = re.sub(r'^•\s*📊 Market Size Metrics$', r'📊 Market Size Metrics', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*📈 Growth Metrics$', r'📈 Growth Metrics', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*📰 Sector Analysis$', r'📰 Sector Analysis', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*🔍 Market Research Sources$', r'🔍 Market Research Sources', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*🔗 Additional Sources$', r'🔗 Additional Sources', raw, flags=re.MULTILINE)
    
    # Also convert plain text headers to bold formatting
    raw = re.sub(r'^Business Model Overview$', r'**Business Model Overview**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Potential Revenue Streams$', r'**Potential Revenue Streams**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Customer Segments$', r'**Customer Segments**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Go-to-Market Strategies$', r'**Strategy**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Strategy$', r'**Strategy**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Business Model Schema$', r'**Business Model Schema:**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Additional Research Needed$', r'**Additional Research Needed**', raw, flags=re.MULTILINE)
    
    # Also convert plain text market headers to bold formatting
    raw = re.sub(r'^📊 Market Size Metrics$', r'📊 Market Size Metrics', raw, flags=re.MULTILINE)
    raw = re.sub(r'^📈 Growth Metrics$', r'📈 Growth Metrics', raw, flags=re.MULTILINE)
    raw = re.sub(r'^📰 Sector Analysis$', r'📰 Sector Analysis', raw, flags=re.MULTILINE)
    raw = re.sub(r'^🔍 Market Research Sources$', r'🔍 Market Research Sources', raw, flags=re.MULTILINE)
    raw = re.sub(r'^🔗 Additional Sources$', r'🔗 Additional Sources', raw, flags=re.MULTILINE)
    
    # Convert any remaining plain text headers that might be missed
    raw = re.sub(r'^([A-Z][a-z\s]+):$', r'**\1:**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^([A-Z][A-Za-z\s]+)$', r'**\1**', raw, flags=re.MULTILINE)
    
    # Simplify "Additional Research Needed" section to one sentence
    if "**Additional Research Needed**" in raw:
        # Find the section and replace it with a simplified version
        pattern = r'\*\*Additional Research Needed\*\*\s*\n(.*?)(?=\n\*\*|\n\n|$)'
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            current_content = match.group(1).strip()
            # Extract the first sentence or create a summary
            sentences = re.split(r'[.!?]+', current_content)
            first_sentence = sentences[0].strip() if sentences[0].strip() else "Additional research is needed to better understand the company's business model and revenue streams."
            if not first_sentence.endswith('.'):
                first_sentence += '.'
            simplified_section = f"**Additional Research Needed**\n{first_sentence}"
            raw = re.sub(pattern, simplified_section, raw, flags=re.DOTALL)
    
    return raw

def run_risks_section_chain(profile: StartupProfile) -> str:
    """Generate risks section for the memo."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Risks section for an investment memo.
- Organize risks into clear categories with BOLD headers: **Market Risks**, **Technical Risks**, **Operational Risks**, **Regulatory Risks**, **Financial Risks**
- DO NOT use bullet points for category headers - only use bold formatting (**Header**)
- Use bullet points ONLY for individual risk items under each category
- List the POTENTIAL risks relevant to this company and product, sector with a specific explanation for each risk.
- Make each risk specific to the company's technology, market, or business context. Avoid generic or boilerplate risks.
- Use bullet points for individual risks, with each risk followed by a short, specific explanation.
- Use plain, non-marketing language.

FORMATTING EXAMPLE:
**Market Risks**
• Market Adoption Uncertainty: [specific explanation]
• Competitive Landscape Ambiguity: [specific explanation]

**Technical Risks**
• Technology Maturity Uncertainty: [specific explanation]
• Performance and Reliability Concerns: [specific explanation]

IMPORTANT: Use tentative language and clearly indicate when you are making assumptions or interpretations.
- Use phrases like "appears to be", "seems to", "may be", "could be", "based on available information"
- Do not present assumptions as facts about current risks
- If information is limited, explicitly state what additional research is needed
- DO NOT include any risk score or numerical risk assessment - focus on qualitative risk descriptions

Context:
Company: {getattr(profile, 'name', '')}
Sector: {getattr(profile, 'sector', '')}
Risks: {getattr(profile, 'risk_flags', '')}
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
    
    # Fix category headers that might be bullet points instead of bold
    raw = re.sub(r'^•\s*Market Risks$', r'**Market Risks**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*Technical Risks$', r'**Technical Risks**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*Operational Risks$', r'**Operational Risks**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*Regulatory Risks$', r'**Regulatory Risks**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*Financial Risks$', r'**Financial Risks**', raw, flags=re.MULTILINE)
    
    # Also convert plain text category headers to bold formatting
    raw = re.sub(r'^Market Risks$', r'**Market Risks**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Technical Risks$', r'**Technical Risks**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Operational Risks$', r'**Operational Risks**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Regulatory Risks$', r'**Regulatory Risks**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Financial Risks$', r'**Financial Risks**', raw, flags=re.MULTILINE)
    
    # Remove any risk score mentions
    raw = re.sub(r'Risk Score of [0-9.]+', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'risk score.*?[0-9.]+', '', raw, flags=re.IGNORECASE)
    
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
- Write a single, concise paragraph (4-5 sentences).
- Summarize only the most material ESG factors for this company (environmental, social, and governance), focusing on what matters most for investors.
- Avoid generic, boilerplate, or verbose content. Do not list every ESG subtopic—only mention what is most relevant and specific to the company.
- Use plain, non-marketing language.
- DO NOT use any headers, bold formatting, or section dividers. Write as one flowing paragraph.
- Do NOT separate environmental, social, and governance into different sections.
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
    
    # Remove any bold headers that might have been generated
    raw = re.sub(r'\*\*Environmental:\*\*', 'Environmental', raw)
    raw = re.sub(r'\*\*Social:\*\*', 'Social', raw)
    raw = re.sub(r'\*\*Governance:\*\*', 'Governance', raw)
    raw = re.sub(r'\*\*ESG:\*\*', 'ESG', raw)
    
    # Remove any other bold headers that might appear
    raw = re.sub(r'\*\*([^*]+):\*\*', r'\1', raw)
    
    # Clean up extra spaces and formatting
    raw = re.sub(r'\s+', ' ', raw)
    raw = raw.strip()
    
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
- DO NOT use bullet points for headers - only use bold formatting (**Header**)

FORMATTING EXAMPLE:
**Key Strengths:**
[paragraph about strengths]

**Key Weaknesses:**
[paragraph about weaknesses]

**Opportunities:**
[paragraph about opportunities]

**Risks:**
[paragraph about risks]

**Conclusion:**
[paragraph with conclusion]

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
    
    # Fix headers that might be bullet points instead of bold
    text = re.sub(r'^•\s*Key Strengths:$', r'**Key Strengths:**', text, flags=re.MULTILINE)
    text = re.sub(r'^•\s*Key Weaknesses:$', r'**Key Weaknesses:**', text, flags=re.MULTILINE)
    text = re.sub(r'^•\s*Opportunities:$', r'**Opportunities:**', text, flags=re.MULTILINE)
    text = re.sub(r'^•\s*Risks:$', r'**Risks:**', text, flags=re.MULTILINE)
    text = re.sub(r'^•\s*Conclusion:$', r'**Conclusion:**', text, flags=re.MULTILINE)
    
    # Also convert plain text headers to bold formatting
    text = re.sub(r'^Key Strengths:$', r'**Key Strengths:**', text, flags=re.MULTILINE)
    text = re.sub(r'^Key Weaknesses:$', r'**Key Weaknesses:**', text, flags=re.MULTILINE)
    text = re.sub(r'^Opportunities:$', r'**Opportunities:**', text, flags=re.MULTILINE)
    text = re.sub(r'^Risks:$', r'**Risks:**', text, flags=re.MULTILINE)
    text = re.sub(r'^Conclusion:$', r'**Conclusion:**', text, flags=re.MULTILINE)
    
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
- DO NOT use any headers, bold formatting, or section dividers. Write as one flowing paragraph.
- DO NOT include "Investment & Exit Strategies:" or any similar header in your response.
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
    
    # Remove any bold headers that might have been generated
    raw = re.sub(r'\*\*Investment & Exit Strategies:\*\*', '', raw)
    raw = re.sub(r'\*\*Investment & Exit Strategies\*\*', '', raw)
    raw = re.sub(r'Investment & Exit Strategies:', '', raw)
    raw = re.sub(r'Investment & Exit Strategies', '', raw)
    
    # Remove any other bold headers that might appear
    raw = re.sub(r'\*\*([^*]+):\*\*', r'\1', raw)
    
    # Clean up extra spaces and formatting
    raw = re.sub(r'\s+', ' ', raw)
    raw = raw.strip()
    
    return raw

def run_followup_section_chain(profile: StartupProfile) -> str:
    """Generate follow-up section for the memo."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    prompt = f"""
You are a VC analyst writing the Follow-up Questions & Next Steps section for an investment memo.
- Organize the section by topic, using bold headers (e.g., **Technology Validation & IP**, **Financials & Funding Stage**, **Competitive Landscape**, **OEM & Manufacturing Partnerships**, **Regulatory & Market Timing**).
- DO NOT use bullet points for headers - only use bold formatting (**Header**)
- Use bullet points ONLY for individual questions or action items under each header
- For each topic, list 2-4 specific, actionable follow-up questions or next steps as bullet points.
- Use plain, non-marketing language.

FORMATTING EXAMPLE:
**Technology Validation & IP**
• What specific milestones has the company achieved in technology development?
• Can the company provide detailed information on patents or IP protections?

**Financials & Funding Stage**
• What is the current funding stage and plans for future fundraising?
• Can the company provide financial projections or revenue models?

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
    raw = response.content.strip() if hasattr(response, 'content') else str(response)
    
    # Fix headers that might be bullet points instead of bold
    raw = re.sub(r'^•\s*Technology Validation & IP$', r'**Technology Validation & IP**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*Financials & Funding Stage$', r'**Financials & Funding Stage**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*Competitive Landscape$', r'**Competitive Landscape**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*OEM & Manufacturing Partnerships$', r'**OEM & Manufacturing Partnerships**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*Regulatory & Market Timing$', r'**Regulatory & Market Timing**', raw, flags=re.MULTILINE)
    
    # Also convert plain text headers to bold formatting
    raw = re.sub(r'^Technology Validation & IP$', r'**Technology Validation & IP**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Financials & Funding Stage$', r'**Financials & Funding Stage**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Competitive Landscape$', r'**Competitive Landscape**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^OEM & Manufacturing Partnerships$', r'**OEM & Manufacturing Partnerships**', raw, flags=re.MULTILINE)
    raw = re.sub(r'^Regulatory & Market Timing$', r'**Regulatory & Market Timing**', raw, flags=re.MULTILINE)
    
    # Remove bold formatting from bullet points (questions should not be bold)
    raw = re.sub(r'^\*\*•\s*([^*]+)\*\*$', r'• \1', raw, flags=re.MULTILINE)
    raw = re.sub(r'^•\s*\*\*([^*]+)\*\*$', r'• \1', raw, flags=re.MULTILINE)
    
    return raw 