from crewai import Agent, Task

def build_esg_chain_agent(profile, text):
    def chain_callback(*_):
        from chains.esg_chain import run_esg_chain_with_text
        updated_profile = run_esg_chain_with_text(text, profile)
        return updated_profile.model_dump()
    agent = Agent(
        role="ESG Extractor",
        goal="Extract ESG analysis from the deck.",
        backstory="A specialized agent for extracting ESG analysis from pitch decks.",
        verbose=True
    )
    task = Task(
        description="Extract ESG analysis from the deck.",
        agent=agent,
        callback=chain_callback,
        args=[profile.model_dump()],
        expected_output="Profile with ESG analysis."
    )
    return agent, task 