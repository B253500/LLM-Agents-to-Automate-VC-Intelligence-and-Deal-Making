from crewai import Agent, Task

def build_exit_chain_agent(profile, text):
    def chain_callback(*_):
        from chains.exit_strategy_chain import run_exit_strategy_chain_with_text
        updated_profile = run_exit_strategy_chain_with_text(text, profile)
        return updated_profile.model_dump()
    agent = Agent(
        role="Exit Strategy Extractor",
        goal="Extract exit strategy analysis from the deck.",
        backstory="A specialized agent for extracting exit strategy analysis from pitch decks.",
        verbose=True
    )
    task = Task(
        description="Extract exit strategy analysis from the deck.",
        agent=agent,
        callback=chain_callback,
        args=[profile.model_dump()],
        expected_output="Profile with exit strategy analysis."
    )
    return agent, task 