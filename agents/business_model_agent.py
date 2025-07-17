from crewai import Agent, Task

def build_business_model_chain_agent(profile, text):
    def chain_callback(*_):
        from chains.business_model_chain import run_business_model_chain_with_text
        updated_profile = run_business_model_chain_with_text(text, profile)
        return updated_profile.model_dump()
    agent = Agent(
        role="Business Model Extractor",
        goal="Extract business model analysis from the deck.",
        backstory="A specialized agent for extracting business model analysis from pitch decks.",
        verbose=True
    )
    task = Task(
        description="Extract business model analysis from the deck.",
        agent=agent,
        callback=chain_callback,
        args=[profile.model_dump()],
        expected_output="Profile with business model analysis."
    )
    return agent, task 