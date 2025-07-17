from crewai import Agent, Task

def build_followup_chain_agent(profile, text):
    def chain_callback(*_):
        from chains.follow_up_chain import run_follow_up_chain_with_text
        updated_profile = run_follow_up_chain_with_text(text, profile)
        return updated_profile.model_dump()
    agent = Agent(
        role="Follow-Up Extractor",
        goal="Extract follow-up questions and next steps from the deck.",
        backstory="A specialized agent for extracting follow-up questions and next steps from pitch decks.",
        verbose=True
    )
    task = Task(
        description="Extract follow-up questions and next steps from the deck.",
        agent=agent,
        callback=chain_callback,
        args=[profile.model_dump()],
        expected_output="Profile with follow-up questions and next steps."
    )
    return agent, task 