"""Framework integrations for Nous.

Plug Nous into any agent framework with minimal code:

    # LangChain
    from nous.integrations.langchain import NousCallback
    agent.run(callbacks=[NousCallback()])

    # OpenAI Agents / generic
    from nous.integrations.generic import guard_agent_loop
    for step, result in guard_agent_loop(agent_steps):
        if not result:
            handle_violation(result)
"""
