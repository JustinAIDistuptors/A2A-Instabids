"""
Implementation for the Contractor Agent.

This agent will help contractors find projects (Bid Cards) and submit bids.
"""

import logging
from typing import Any, Dict, Optional, Tuple  # Added Tuple
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import uuid  # Import uuid

# Assuming ADK and A2A types are accessible
# Adjust import paths based on final project structure
from google.adk.agents import Agent as AdkAgent
from ...a2a_types.core import (
    Task,
    Message,
    Artifact,
    AgentId,
    TaskId,
    MessageId,
    Agent as A2aAgentInfo,
    TaskStatus,
)  # Added TaskStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

AGENT_ID: AgentId = "contractor-agent-001"  # Example ID - Should be configurable


class ContractorAgent(AdkAgent):
    """
    InstaBids Agent responsible for contractor interactions.
    """

    def __init__(
        self,
        agent_info: Optional[A2aAgentInfo] = None,
        supabase_client: Optional[Client] = None,  # Allow injecting client for testing
    ):
        """Initializes the ContractorAgent."""
        agent_endpoint = os.getenv("CONTRACTOR_AGENT_ENDPOINT", "http://localhost:8003")
        self.agent_info = agent_info or A2aAgentInfo(
            id=AGENT_ID,
            name="Contractor Agent",
            description="Assists contractors with finding projects and submitting bids.",
            endpoint=agent_endpoint,
            capabilities=["project_discovery", "bid_submission"],
        )
        logger.info(f"Initializing ContractorAgent (ID: {self.agent_info.id})")

        # Initialize Supabase client if not injected
        if supabase_client:
            self.db: Client = supabase_client
        else:
            supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
            supabase_key: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
            if not supabase_url or not supabase_key:
                logger.error(
                    "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables."
                )
                self.db = None
            else:
                try:
                    self.db: Client = create_client(supabase_url, supabase_key)
                    logger.info("Supabase client initialized successfully.")
                except Exception as e:
                    logger.error(f"Failed to initialize Supabase client: {e}")
                    self.db = None

    async def handle_create_task(self, task: Task) -> None:
        """Handles tasks assigned to this agent (e.g., 'find relevant projects')."""
        logger.info(f"ContractorAgent received task: {task.id} - '{task.description}'")
        await self._update_task_status(task.id, "IN_PROGRESS")
        # Placeholder Logic:
        # - Could be triggered by a contractor user via UI to find projects.
        # - Might involve querying the MatchingAgent or a project database.
        # - Could involve presenting Bid Cards back to the user/contractor.
        print(f"TODO: Implement task handling logic for task {task.id}")
        # Simulate completion for now
        await self._update_task_status(
            task.id, "COMPLETED", result={"message": "Placeholder task handled"}
        )

    async def handle_message(self, message: Message) -> None:
        """Handles incoming messages (e.g., a contractor confirming bid details)."""
        logger.info(
            f"ContractorAgent received message: {message.id} for task {message.task_id}"
        )
        # Placeholder Logic:
        # - Process message content (e.g., bid details).
        # - Potentially create a bid artifact or call a bid submission tool.
        # - Send confirmation message back.
        print(f"TODO: Implement message handling logic for message {message.id}")
        # Example: If message content contains structured bid details
        if isinstance(message.content, dict) and "bid_amount" in message.content:
            logger.info(f"Attempting to submit bid based on message {message.id}")
            # TODO: Get contractor_user_id from message context or agent state
            contractor_user_id = str(uuid.uuid4())  # Placeholder
            project_id = message.content.get("project_id")  # Need project_id in message

            if not project_id:
                logger.error(
                    f"Cannot submit bid from message {message.id}: Missing project_id."
                )
                # TODO: Send error response message back
                return

            success = await self.submit_bid(
                project_id=project_id,
                contractor_user_id=contractor_user_id,
                amount=message.content.get("bid_amount"),
                description=message.content.get("bid_description"),
                metadata=message.content.get("bid_metadata"),  # e.g., timeline
            )
            # TODO: Send response message back to user/sender confirming success/failure

    async def submit_bid(
        self,
        project_id: str,
        contractor_user_id: str,  # Should ideally come from authenticated user context
        amount: float,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Saves a new bid to the database."""
        if not self.db:
            logger.error("Supabase client not initialized. Cannot submit bid.")
            return False
        if not project_id or not contractor_user_id or amount is None:
            logger.error(
                "Missing required fields for bid submission (project_id, contractor_user_id, amount)."
            )
            return False

        logger.info(
            f"Submitting bid for project {project_id} by contractor {contractor_user_id}"
        )

        bid_data = {
            "project_id": project_id,
            "contractor_id": contractor_user_id,
            "amount": amount,
            "description": description,
            "status": "pending",  # Default status
            "metadata": metadata,
        }
        # Clean None values
        bid_data = {k: v for k, v in bid_data.items() if v is not None}
        bid_metadata = bid_data.get("metadata", {})
        bid_metadata = {k: v for k, v in bid_metadata.items() if v is not None}
        bid_data["metadata"] = bid_metadata if bid_metadata else None

        try:
            insert_res = await self.db.table("bids").insert(bid_data).execute()
            logger.debug(f"Supabase bid insert response: {insert_res}")

            if insert_res.data and len(insert_res.data) > 0:
                bid_id = insert_res.data[0]["id"]
                logger.info(
                    f"Bid {bid_id} submitted successfully for project {project_id}."
                )
                return True
            else:
                logger.error(
                    f"Failed to insert bid for project {project_id}. Response: {insert_res}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error submitting bid for project {project_id}: {e}", exc_info=True
            )
            return False

    async def _update_task_status(
        self,
        task_id: TaskId,
        status: TaskStatus,
        result: Optional[Dict] = None,
        error_message: Optional[str] = None,
    ):
        """Placeholder for updating task status via A2A or DB."""
        # TODO: Implement actual task status update mechanism.
        log_message = f"Task {task_id}: Status changed to {status}."
        if result:
            log_message += f" Result: {result}"
        if error_message:
            log_message += f" Error: {error_message}"
        logger.info(log_message)
        print(f"TODO: Implement actual status update for task {task_id} to {status}")

    def get_agent_info(self) -> A2aAgentInfo:
        """Returns the configuration/details of this agent."""
        return self.agent_info


# --- Agent Instantiation ---
# contractor_agent_instance = ContractorAgent()
