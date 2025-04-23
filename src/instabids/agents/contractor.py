from google.adk import LlmAgent
from instabids.tools import supabase_tools

contractor_agent = LlmAgent(
    name="ContractorDispatcher",
    tools=[*supabase_tools],
    system_prompt=(
        "You represent a network of contractors. "
        "Given a project description, decide whether it matches your trade and, "
        "if so, submit a bid via the create_bid tool."
    ),
)
