from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context
from core.perplexity_utils import search_perplexity
import json
from hashlib import sha1

llm = ChatOpenAI(model="gpt-4", temperature=0.2)

SYSTEM = """
You are a senior CTO performing technical due diligence for venture capital investment.
For the given company, provide a detailed, critical analysis of the technology, including:
- Technical feasibility and performance (with specific strengths and weaknesses)
- Scalability and architecture
- Integration complexity and dependencies
- Security and data protection risks
- Regulatory and compliance issues
- Implementation complexity and testing requirements
- Assumption risks and dependencies
- What needs to be validated or further investigated
Structure your answer with subheadings and bullet points for each area. Be specific, critical, and highlight both strengths and weaknesses. If information is missing, note it explicitly.
Return a detailed, multi-paragraph, multi-bullet analysis suitable for a VC investment memo.
"""
PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Startup info:\n{context}\n")
])

def get_recent_tech_news(company_name):
    if not company_name:
        return None
    query = f"Recent technical news, product launches, or technology updates for {company_name} (past 12 months)."
    return search_perplexity(query)

def build_technical_dd_agent(profile: StartupProfile, trace_id=None):
    ctto = Agent(
        role="Technical due-diligence lead",
        goal="Assess technical maturity, product moat, and technology risks of the startup.",
        backstory="25-year CTO who has evaluated 500+ VC deals. Expert in technical due diligence, product evaluation, and technology risk assessment.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(context, *args, **kwargs):
        # In hierarchical mode, ignore incoming context and start fresh
        profile = StartupProfile()
        if deck_payload:
            print(f"[technical_dd_agent] Deck text (first 200 chars): {deck_payload.get('text', '')[:200]}")
        else:
            print(f"[technical_dd_agent] No deck_payload provided.")
        # Build context and prompt
        from core.hybrid_context import safe_truncate
        ctx = get_hybrid_context(profile, "technical OR product OR solution OR technology", 3, 3)
        ctx = safe_truncate(ctx, max_chars=2000)
        deck_text = safe_truncate(deck_payload.get('text', '') if deck_payload else '', max_chars=2000)
        prompt_context = f"{ctx}\n\nFull Deck Text:\n{deck_text}"
        print(f"[technical_dd_agent] LLM prompt context (first 300 chars): {prompt_context[:300]}")
        raw = llm.invoke(PROMPT.format(context=prompt_context)).content.strip()
        print(f"[technical_dd_agent] LLM raw output (first 300 chars): {raw[:300]}")
        # --- Chain logic inlined here ---
        first, last = raw.find("{"), raw.rfind("}")
        if first != -1 and last != -1:
            try:
                data = json.loads(raw[first : last + 1])
                # Flatten dicts if needed
                if isinstance(data.get("tech_maturity"), dict):
                    data["tech_maturity"] = str(data["tech_maturity"])
                if isinstance(data.get("moat_strength"), dict):
                    data["moat_strength"] = str(data["moat_strength"])
                # Only set values if they are not null/None
                if data.get("tech_maturity") is not None:
                    profile.tech_maturity = data.get("tech_maturity")
                if data.get("moat_strength") is not None:
                    profile.moat_strength = data.get("moat_strength")
            except Exception as e:
                print(f"[Error] Failed to parse LLM output: {e}")
        if not profile.startup_id:
            profile.startup_id = sha1((profile.name or ctx[:40]).encode()).hexdigest()[:10]
        # 2. Enrich: web search for recent technical news
        news = get_recent_tech_news(profile.name)
        profile.tech_news = news
        print(f"[technical_dd_agent] Output profile: {profile.model_dump()}")
        output = profile.model_dump()
        print(f"[technical_dd_agent] Output type: {type(output)}")
        print(f"[technical_dd_agent] Output keys: {list(output.keys()) if isinstance(output, dict) else 'N/A'}")
        return output

    task = Task(
        description="Analyze tech stack, rate maturity, summarize moat, assess technology risks, and enrich with recent technical news.",
        agent=ctto,
        expected_output="A detailed technical due diligence report including tech maturity, moat strength, risks, and recent technical news.",
        callback=_callback,
    )
    return ctto, task


def build_technical_chain_agent(profile):
    def chain_callback(*_):
        from chains.technical_dd_chain import run_technical_dd_chain
        updated_profile = run_technical_dd_chain(profile)
        return updated_profile.model_dump()
    agent = Agent(
        role="Technical DD Extractor",
        goal="Extract technical due diligence data from the deck.",
        backstory="A specialized agent for extracting technical due diligence data from pitch decks.",
        verbose=True
    )
    task = Task(
        description="Extract technical due diligence data from the deck.",
        agent=agent,
        callback=chain_callback,
        args=[profile.model_dump()],
        expected_output="Profile with technical DD fields extracted."
    )
    return agent, task
