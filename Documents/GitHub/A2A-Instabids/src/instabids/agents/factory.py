"""Agent singleton factory & cache."""

from google.adk import Agent
from instabids.tools import supabase_tools
from instabids.agents.contractor import create_contractor_agent
from memory.persistent_memory import PersistentMemory

# Tracing is now configured differently in newer versions of google.adk
# enable_tracing("stdout")

_homeowner: Agent | None = None
_contractor: Agent | None = None


def get_homeowner_agent(memory: PersistentMemory = None) -> Agent:
    global _homeowner
    if _homeowner is None:
        _homeowner = Agent(
            name="HomeownerAgent",
            tools=[*supabase_tools],
            system_prompt=(
                "You help homeowners collect and compare contractor bids. "
                "When you need to store or fetch data, call the appropriate Supabase tool."
            ),
            memory=memory,
        )
    return _homeowner


def get_contractor_agent(memory: PersistentMemory = None) -> Agent:
    """Returns a contractor agent with memory injection if provided."""
    global _contractor
    if _contractor is None or memory is not None:
        _contractor = create_contractor_agent(memory)
    return _contractor
