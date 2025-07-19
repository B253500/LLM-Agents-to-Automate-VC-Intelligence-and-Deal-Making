from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile
import json
from hashlib import sha1

def web_search_esg_context(company_name):
    # Placeholder: Integrate EXA, Perplexity, or other API here
    # Return a string with web search results
    return ""

llm = ChatOpenAI(model="gpt-4", temperature=0.2)

SYSTEM = """
You are an ESG (Environmental, Social, Governance) analyst for venture capital deals.
Analyze the startup's materials and provide:
- A concise summary of key ESG considerations
- Discussion of sustainability, social impact, governance, and regulatory alignment
- Any recent ESG news or controversies (use web search context if available)
- Attribute sources where possible
Return a summary (3-6 sentences). If insufficient data, state what is missing.
"""
PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Startup info:\n{context}\nWeb search context:\n{web_context}\n")
])

def build_esg_chain_agent(profile, text, deck_payload):
    def _callback(context, *args, **kwargs):
        # In hierarchical mode, ignore incoming context and start fresh
        profile = StartupProfile()
        if deck_payload:
            print(f"[esg_agent] Deck text (first 200 chars): {deck_payload.get('text', '')[:200]}")
        else:
            print(f"[esg_agent] No deck_payload provided.")
        from core.hybrid_context import safe_truncate
        context_str = safe_truncate(text[:5000] if 'text' in locals() else '', max_chars=1500)
        deck_text = safe_truncate(deck_payload.get('text', '') if deck_payload else '', max_chars=1500)
        prompt_context = f"{context_str}\n\nFull Deck Text:\n{deck_text}"
        print(f"[esg_agent] LLM prompt context (first 300 chars): {prompt_context[:300]}")
        raw = llm.invoke(PROMPT.format(context=prompt_context)).content.strip()
        print(f"[esg_agent] LLM raw output (first 300 chars): {raw[:300]}")
        # ...rest of your logic...
        print(f"[esg_agent] Output profile: {profile.model_dump()}")
        output = profile.model_dump()
        print(f"[esg_agent] Output type: {type(output)}")
        print(f"[esg_agent] Output keys: {list(output.keys()) if isinstance(output, dict) else 'N/A'}")
        return output
    agent = Agent(
        role="ESG Extractor",
        goal="Extract ESG analysis from the deck.",
        backstory="A specialized agent for extracting ESG analysis from pitch decks.",
        verbose=True
    )
    task = Task(
        description="Extract ESG analysis from the deck.",
        agent=agent,
        callback=_callback,
        args=[profile.model_dump(), deck_payload],
        expected_output="Profile with ESG analysis."
    )
    return agent, task 