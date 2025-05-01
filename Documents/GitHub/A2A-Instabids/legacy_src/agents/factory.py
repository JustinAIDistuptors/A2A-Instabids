from google.adk import LlmAgent, enable_tracing
from instabids.tools.supabase import supabase_tools

_homeowner_agent: LlmAgent | None = None


def get_homeowner_agent() -> LlmAgent:
    global _homeowner_agent
    if _homeowner_agent is None:
        _homeowner_agent = LlmAgent(
            name="HomeownerAgent",
            tools=[*supabase_tools],
            system_prompt="You help homeowners collect and compare contractor bids.",
        )
        enable_tracing("stdout")
    return _homeowner_agent
