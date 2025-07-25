from langchain_openai import ChatOpenAI
from core.schemas import StartupProfile

def run_product_description_chain(profile: StartupProfile) -> str:
    """
    Use LLM to synthesize a detailed, multi-paragraph, multi-bullet Product/Service Description section for the memo.
    """
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