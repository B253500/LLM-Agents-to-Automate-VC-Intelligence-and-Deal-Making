from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile
import json
from hashlib import sha1

llm = ChatOpenAI(model="gpt-4", temperature=0.2)

SYSTEM = """
You are a VC analyst specializing in exit strategies.
Analyze the startup's materials and summarize potential exit scenarios, including likely acquirers, IPO potential, and recommended exit strategies and timelines.
Return a concise summary (3-6 sentences). If insufficient data, state what is missing.
"""
PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Startup info:\n{context}\n")
])

def build_exit_chain_agent(profile, text, deck_payload):
    def _callback(context, *args, **kwargs):
        # In hierarchical mode, ignore incoming context and start fresh
        profile = StartupProfile()
        if deck_payload:
            print(f"[exit_strategy_agent] Deck text (first 200 chars): {deck_payload.get('text', '')[:200]}")
        else:
            print(f"[exit_strategy_agent] No deck_payload provided.")
        from core.hybrid_context import safe_truncate
        context_str = safe_truncate(text[:5000] if 'text' in locals() else '', max_chars=1500)
        deck_text = safe_truncate(deck_payload.get('text', '') if deck_payload else '', max_chars=1500)
        prompt_context = f"{context_str}\n\nFull Deck Text:\n{deck_text}"
        print(f"[exit_strategy_agent] LLM prompt context (first 300 chars): {prompt_context[:300]}")
        raw = llm.invoke(PROMPT.format(context=prompt_context)).content.strip()
        print(f"[exit_strategy_agent] LLM raw output (first 300 chars): {raw[:300]}")
        # ...rest of your logic...
        print(f"[exit_strategy_agent] Output profile: {profile.model_dump()}")
        output = profile.model_dump()
        print(f"[exit_strategy_agent] Output type: {type(output)}")
        print(f"[exit_strategy_agent] Output keys: {list(output.keys()) if isinstance(output, dict) else 'N/A'}")
        return output
    agent = Agent(
        role="Exit Strategy Extractor",
        goal="Extract exit strategy analysis from the deck.",
        backstory="A specialized agent for extracting exit strategy analysis from pitch decks.",
        verbose=True
    )
    task = Task(
        description="Extract exit strategy analysis from the deck.",
        agent=agent,
        callback=_callback,
        args=[profile.model_dump(), deck_payload],
        expected_output="Profile with exit strategy analysis."
    )
    return agent, task 