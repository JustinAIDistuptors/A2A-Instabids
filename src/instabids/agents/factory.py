"""Agent singleton factory & cache."""
from google.adk import LlmAgent, enable_tracing
from instabids.tools import supabase_tools
from instabids.agents.contractor import contractor_agent

enable_tracing("stdout")

_homeowner: LlmAgent | None = None

def get_homeowner_agent() -> LlmAgent:
    global _homeowner
    if _homeowner is None:
        _homeowner = LlmAgent(
            name="HomeownerAgent",
            tools=[*supabase_tools],
            system_prompt=(
                "You help homeowners collect and compare contractor bids. "
                "When you need to store or fetch data, call the appropriate Supabase tool."
            ),
        )
    return _homeowner

def get_contractor_agent() -> LlmAgent:
    """Currently returns a single dispatcher; later phases can load many."""
    return contractor_agent
