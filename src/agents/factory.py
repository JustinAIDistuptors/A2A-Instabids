"""
Factory for creating and managing user-specific agent instances.
"""
import logging
from typing import Dict, Any, Optional, Type
import asyncio
import weakref

from google.adk.agents import Agent as AdkAgent
from supabase import Client

from ..a2a_types.core import Agent as A2aAgentInfo
from ..memory.persistent_memory import PersistentMemory
from .homeowner.agent import HomeownerAgent
from .contractor.agent import ContractorAgent

logger = logging.getLogger(__name__)

# Cache of active agent instances by user_id and type
_agent_cache = weakref.WeakValueDictionary()

# Lock to prevent concurrent creation of the same agent
_agent_creation_locks = {}

async def get_user_agent(
    db: Client,
    user_id: str,
    agent_type: str,
    base_endpoint: str,
    **kwargs
) -> Optional[AdkAgent]:
    """
    Get or create a user-specific agent instance.
    
    Args:
        db: Supabase database client
        user_id: User ID to create agent for
        agent_type: Type of agent ("homeowner" or "contractor")
        base_endpoint: Base URL for agent endpoints
        **kwargs: Additional arguments for agent constructor
        
    Returns:
        Agent instance or None if creation failed
    """
    cache_key = f"{user_id}:{agent_type}"
    
    # Check cache first
    if cache_key in _agent_cache:
        logger.info(f"Retrieved cached agent instance for {cache_key}")
        return _agent_cache[cache_key]
    
    # Use a lock to prevent concurrent creation
    if cache_key not in _agent_creation_locks:
        _agent_creation_locks[cache_key] = asyncio.Lock()
    
    async with _agent_creation_locks[cache_key]:
        # Check again in case another task created it while we were waiting
        if cache_key in _agent_cache:
            logger.info(f"Retrieved cached agent instance for {cache_key} after lock")
            return _agent_cache[cache_key]
            
        try:
            # Get user data
            user_res = await db.table("users") \
                .select("*") \
                .eq("id", user_id) \
                .maybe_single() \
                .execute()
                
            if not user_res.data:
                logger.error(f"User {user_id} not found when creating agent")
                return None
                
            user_data = user_res.data
            
            # Create persistent memory for this user
            memory = PersistentMemory(db, user_id)
            await memory.load()
            
            # Create appropriate agent type
            agent_class: Type[AdkAgent] = None
            agent_id: str = None
            
            if agent_type == "homeowner":
                agent_class = HomeownerAgent
                agent_id = f"homeowner-agent-{user_id}"
            elif agent_type == "contractor":
                agent_class = ContractorAgent
                agent_id = f"contractor-agent-{user_id}"
            else:
                logger.error(f"Unknown agent type: {agent_type}")
                return None
                
            # Create agent info
            agent_info = A2aAgentInfo(
                id=agent_id,
                name=f"{agent_type.capitalize()} Agent for {user_data.get('email')}",
                description=f"Personalized {agent_type} assistant.",
                endpoint=f"{base_endpoint}/{agent_type}/{user_id}",
                capabilities=[]  # Will be set by agent class
            )
            
            # Create the agent instance
            agent = agent_class(
                agent_info=agent_info,
                supabase_client=db,
                memory_service=memory,
                **kwargs
            )
            
            # Cache the instance
            _agent_cache[cache_key] = agent
            logger.info(f"Created new agent instance for {cache_key}")
            
            return agent
            
        except Exception as e:
            logger.error(f"Error creating agent for {cache_key}: {e}", exc_info=True)
            return None
