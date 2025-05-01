"""
Implementation for the Messaging Agent.

This agent manages and filters communication between homeowners and contractors,
handling message routing, filtering based on project/bid status, and potentially
content redaction and pseudonymity.
"""

import logging
from typing import Any, Dict, Optional, Tuple, List
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import uuid
import json
import asyncio  # Import asyncio
import datetime  # Import datetime

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
)

# Import A2A client functions if this agent needs to forward messages
from ...a2a_comm import client as a2a_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

AGENT_ID: AgentId = "messaging-agent-001"  # Example ID - Should be configurable

# --- Agent Registry (Simple Placeholder) ---
# TODO: Centralize agent registry/discovery
AGENT_REGISTRY_JSON = os.getenv("AGENT_REGISTRY", "{}")
try:
    # Expecting format like: {"agent-id": {"name": "...", "endpoint": "...", "user_id": "user-uuid", "role": "homeowner|contractor"}, ...}
    AGENT_REGISTRY: Dict[AgentId, Dict[str, str]] = json.loads(AGENT_REGISTRY_JSON)
    logger.info(f"Loaded agent registry: {list(AGENT_REGISTRY.keys())}")
except json.JSONDecodeError:
    logger.error(
        "Failed to parse AGENT_REGISTRY env var as JSON. Using default fallbacks."
    )
    AGENT_REGISTRY = {}

# Add default endpoints if not in registry (for local dev)
DEFAULT_ENDPOINTS = {
    "homeowner-agent-001": "http://localhost:8001",
    "contractor-agent-001": "http://localhost:8003",
    "bid-card-agent-001": "http://localhost:8002",
    "matching-agent-001": "http://localhost:8004",
    "messaging-agent-001": "http://localhost:8005",
    "outreach-agent-001": "http://localhost:8006",  # Added outreach agent
}


class MessagingAgent(AdkAgent):
    """
    InstaBids Agent responsible for filtering and routing messages.
    """

    def __init__(
        self,
        agent_info: Optional[A2aAgentInfo] = None,
        supabase_client: Optional[Client] = None,  # Allow injecting client for testing
    ):
        """Initializes the MessagingAgent."""
        agent_endpoint = os.getenv(
            "MESSAGING_AGENT_ENDPOINT", DEFAULT_ENDPOINTS.get(AGENT_ID)
        )
        self.agent_info = agent_info or A2aAgentInfo(
            id=AGENT_ID,
            name="Messaging Agent",
            description="Filters and routes messages between homeowners and contractors.",
            endpoint=agent_endpoint,
            capabilities=["message_filtering", "message_routing"],
        )
        logger.info(f"Initializing MessagingAgent (ID: {self.agent_info.id})")

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
        """Handles tasks, e.g., 'broadcast message X for project Y'."""
        logger.info(f"MessagingAgent received task: {task.id} - '{task.description}'")
        await self._update_task_status(task.id, "IN_PROGRESS")

        # Example: Handle broadcast task
        if task.metadata and task.metadata.get("action") == "broadcast":
            project_id = task.metadata.get("project_id")
            broadcast_content = task.metadata.get("content")
            sender_id = task.creator_agent_id  # Agent initiating the broadcast

            if project_id and broadcast_content and sender_id:
                logger.info(
                    f"Task {task.id}: Processing broadcast for project {project_id}"
                )
                await self._handle_broadcast(project_id, sender_id, broadcast_content)
                # Assume broadcast itself completes the task for now
                await self._update_task_status(task.id, "COMPLETED")
            else:
                error_msg = "Missing data for broadcast task."
                logger.error(f"Task {task.id}: {error_msg}")
                await self._update_task_status(
                    task.id, "FAILED", error_message=error_msg
                )
        else:
            error_msg = "Unsupported task type for MessagingAgent."
            logger.warning(f"Task {task.id}: {error_msg}")
            await self._update_task_status(task.id, "FAILED", error_message=error_msg)

    async def handle_message(self, message: Message) -> None:
        """
        Handles incoming messages, applies filtering rules, and forwards if allowed.
        This is the core function of this agent.
        """
        logger.info(
            f"MessagingAgent received message: {message.id} for task {message.task_id} from {message.sender_agent_id} to {message.recipient_agent_id}"
        )

        # TODO: Handle potential message attachments

        if not self.db:
            logger.error(
                f"Message {message.id}: Supabase client not available. Cannot process."
            )
            return

        # 1. Determine final recipient
        final_recipient_agent_id = message.recipient_agent_id
        logger.debug(
            f"Message {message.id}: Identified final recipient as {final_recipient_agent_id}"
        )

        # 2. Determine project_id (crucial for filtering)
        project_id = message.metadata.get("project_id") if message.metadata else None
        if not project_id:
            logger.warning(
                f"Message {message.id}: Missing project_id context. Applying default deny."
            )
            # TODO: Optionally notify sender
            return

        # 3. Check filtering rules
        allowed, reason = await self._should_allow_message(
            project_id, message.sender_agent_id, final_recipient_agent_id
        )

        if allowed:
            # 4. TODO: Apply content redaction if necessary
            modified_content = message.content  # Placeholder
            print(f"TODO: Implement content redaction for message {message.id}")

            # 5. TODO: Apply pseudonymity if necessary
            print(f"TODO: Implement pseudonymity logic for message {message.id}")

            # 6. Get recipient agent details (endpoint)
            recipient_agent_info = await self._get_recipient_agent_info(
                final_recipient_agent_id
            )

            if recipient_agent_info:
                # 7. Forward the message
                logger.info(
                    f"Message {message.id}: Forwarding to {final_recipient_agent_id}"
                )
                try:
                    forward_success = await a2a_client.send_message(
                        target_agent=recipient_agent_info,
                        task_id=message.task_id,
                        role=message.role,
                        content=modified_content,
                        sender_agent_id=message.sender_agent_id,
                        session_id=message.session_id,
                        artifacts=message.artifacts,
                        metadata=message.metadata,
                    )
                    if not forward_success:
                        logger.error(
                            f"Message {message.id}: Failed to forward message via A2A client."
                        )
                        # TODO: Handle forwarding failure
                except Exception as e:
                    logger.error(
                        f"Message {message.id}: Error forwarding message: {e}",
                        exc_info=True,
                    )
                    # TODO: Handle forwarding exception
            else:
                logger.error(
                    f"Message {message.id}: Could not find recipient agent details for {final_recipient_agent_id}. Cannot forward."
                )
                # TODO: Handle recipient not found
        else:
            # 8. Message blocked
            logger.warning(f"Message {message.id}: Blocked. Reason: {reason}")
            # TODO: Optionally notify the sender.

    async def _should_allow_message(
        self, project_id: Optional[str], sender_id: AgentId, recipient_id: AgentId
    ) -> Tuple[bool, str]:
        """Checks if communication is allowed based on project/bid status."""
        logger.debug(
            f"Checking filter rules for project {project_id}, sender {sender_id}, recipient {recipient_id}"
        )

        if not project_id:
            return False, "Blocked: Missing project context"
        if not self.db:
            return False, "Blocked: Database connection unavailable"

        try:
            # Map Agent IDs to User UUIDs and Roles
            sender_user_id, sender_role = await self._get_user_id_and_role(sender_id)
            recipient_user_id, recipient_role = await self._get_user_id_and_role(
                recipient_id
            )

            if not sender_user_id or not recipient_user_id:
                logger.warning(
                    f"Could not map agent IDs to user roles/UUIDs for project {project_id}. Sender: {sender_id}, Recipient: {recipient_id}"
                )
                return False, "Blocked: Could not identify user roles"

            # Identify homeowner and contractor based on roles
            homeowner_user_id = None
            contractor_user_id = None
            if sender_role == "homeowner" and recipient_role == "contractor":
                homeowner_user_id = sender_user_id
                contractor_user_id = recipient_user_id
            elif sender_role == "contractor" and recipient_role == "homeowner":
                contractor_user_id = sender_user_id
                homeowner_user_id = recipient_user_id
            else:
                return (
                    False,
                    f"Blocked: Invalid communication roles ({sender_role} to {recipient_role})",
                )

            # Fetch relevant bid(s) between this contractor and project
            query = self.db.table("bids").select("status")
            query = query.eq("project_id", project_id)
            query = query.eq(
                "contractor_id", contractor_user_id
            )  # Use the contractor's user UUID
            bid_res = await query.execute()

            bids = bid_res.data or []
            has_accepted_bid = any(bid.get("status") == "accepted" for bid in bids)
            has_pending_bid = any(bid.get("status") == "pending" for bid in bids)

            # Rule 1: Always allow if bid is accepted
            if has_accepted_bid:
                return True, "Allowed: Bid accepted"

            # Rule 2: Allow if bid is pending
            if has_pending_bid:
                # TODO: Add logic here or in handle_message to redact contact info
                return True, "Allowed: Bid pending (redaction may apply)"

            # Rule 3: Allow initial contact from contractor pre-bid (if no bids exist yet)
            # TODO: Implement a more robust way to track 'initial contact'
            if sender_role == "contractor" and not bids:
                return True, "Allowed: Initial pre-bid contact"

            # Default Deny
            return False, "Blocked: No accepted/pending bid or prior contact"

        except Exception as e:
            logger.error(
                f"Error checking message permissions for project {project_id}: {e}",
                exc_info=True,
            )
            return False, "Blocked: Error checking permissions"

    async def _get_user_id_and_role(
        self, agent_id: AgentId
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Maps Agent ID to User UUID and role.
        Placeholder implementation - Requires a robust mapping strategy.
        """
        logger.info(f"Attempting to map Agent ID {agent_id} to User ID and Role.")
        # Option 1: Check Agent Registry (if populated with user_id and role)
        agent_details = AGENT_REGISTRY.get(agent_id)
        if agent_details and agent_details.get("user_id") and agent_details.get("role"):
            logger.info(f"Mapped {agent_id} via AGENT_REGISTRY.")
            return agent_details["user_id"], agent_details["role"]

        # Option 2: Database Lookup (Requires schema modification to users table)
        # if self.db:
        #     try:
        #         # Assumes 'users' table has an 'agent_id_mapping' column
        #         user_res = await self.db.table("users").select("id, user_type").eq("agent_id_mapping", agent_id).maybe_single().execute()
        #         if user_res.data:
        #             logger.info(f"Mapped {agent_id} via DB lookup.")
        #             return user_res.data['id'], user_res.data['user_type']
        #     except Exception as e:
        #         logger.error(f"DB error mapping agent ID {agent_id}: {e}")

        # Option 3: Fallback to Naming Convention (Less Robust)
        logger.warning(
            f"Using PLACEHOLDER naming convention for Agent ID -> User mapping for {agent_id}."
        )
        try:
            parts = agent_id.split("-")
            if len(parts) >= 3:
                role_part = parts[0]
                # Attempt to reconstruct UUID - this is highly unreliable if IDs aren't UUIDs
                uuid_part = "-".join(parts[2:])
                if role_part in ["homeowner", "contractor"]:
                    # Validate if it looks like a UUID (simple check)
                    if len(uuid_part) == 36 and uuid_part.count("-") == 4:
                        logger.info(
                            f"Simulated finding user {uuid_part} ({role_part}) based on agent ID convention."
                        )
                        return uuid_part, role_part
        except Exception as conv_e:
            logger.error(f"Error applying naming convention to {agent_id}: {conv_e}")

        logger.error(
            f"Failed to map Agent ID {agent_id} to User ID/Role using any method."
        )
        return None, None

    async def _handle_broadcast(
        self, project_id: str, sender_id: AgentId, content: Any
    ):
        """Handles broadcasting a message to relevant contractors for a project."""
        logger.info(f"Handling broadcast from {sender_id} for project {project_id}")
        if not self.db:
            logger.error("Cannot broadcast: Supabase client unavailable.")
            return

        try:
            # Find all contractors (user UUIDs) who have placed a bid
            # TODO: Refine query to include contractors who initiated contact (Rule 3)
            bids_res = (
                await self.db.table("bids")
                .select("contractor_id")
                .eq("project_id", project_id)
                .execute()
            )
            if not bids_res.data:
                logger.info(
                    f"No bidders found for project {project_id}. Nothing to broadcast."
                )
                return

            recipient_user_ids = list(
                set(bid["contractor_id"] for bid in bids_res.data)
            )  # Get unique contractor user UUIDs

            logger.info(
                f"Broadcasting to recipients (User IDs): {recipient_user_ids} for project {project_id}"
            )

            # Use asyncio.gather to send messages concurrently
            tasks = []
            for recipient_user_id in recipient_user_ids:
                # Map recipient_user_id (UUID) to Agent ID
                # TODO: Replace placeholder mapping with robust lookup
                recipient_agent_id = None
                # Attempt lookup via registry first
                for agent_id_key, details in AGENT_REGISTRY.items():
                    if (
                        details.get("user_id") == recipient_user_id
                        and details.get("role") == "contractor"
                    ):
                        recipient_agent_id = agent_id_key
                        break
                # Fallback to naming convention if not in registry
                if not recipient_agent_id:
                    recipient_agent_id = (
                        f"contractor-agent-{recipient_user_id}"  # Assuming convention
                    )
                    logger.warning(
                        f"Using naming convention to map user {recipient_user_id} to agent {recipient_agent_id}"
                    )

                if not recipient_agent_id:
                    logger.warning(
                        f"Could not determine agent ID for user {recipient_user_id}. Skipping broadcast."
                    )
                    continue

                tasks.append(
                    self._send_broadcast_to_one(
                        project_id=project_id,
                        sender_id=sender_id,
                        content=content,
                        recipient_user_id=recipient_user_id,
                        recipient_agent_id=recipient_agent_id,
                    )
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log any errors from sending
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    user_id_for_log = (
                        recipient_user_ids[i]
                        if i < len(recipient_user_ids)
                        else "unknown"
                    )
                    logger.error(
                        f"Error broadcasting to user {user_id_for_log}: {result}"
                    )

        except Exception as e:
            logger.error(
                f"Error during broadcast setup for project {project_id}: {e}",
                exc_info=True,
            )

    async def _send_broadcast_to_one(
        self,
        project_id: str,
        sender_id: AgentId,
        content: Any,
        recipient_user_id: str,
        recipient_agent_id: AgentId,
    ):
        """Helper to look up agent info and send a single broadcast message."""
        recipient_agent_info = await self._get_recipient_agent_info(recipient_agent_id)
        if recipient_agent_info:
            try:
                await a2a_client.send_message(
                    target_agent=recipient_agent_info,
                    task_id=f"broadcast_{project_id}",
                    role="SYSTEM",
                    content=content,
                    sender_agent_id=sender_id,
                    metadata={"broadcast": True, "project_id": project_id},
                )
                logger.info(
                    f"Broadcast message sent to {recipient_agent_id} for project {project_id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to send broadcast message to {recipient_agent_id} (User: {recipient_user_id}) for project {project_id}: {e}"
                )
                raise  # Re-raise exception to be caught by asyncio.gather
        else:
            logger.warning(
                f"Could not find agent info for recipient user {recipient_user_id}. Skipping broadcast."
            )

    async def _get_recipient_agent_info(
        self, agent_id: AgentId
    ) -> Optional[A2aAgentInfo]:
        """
        Retrieves agent details (especially endpoint) for forwarding.
        Uses a simple registry loaded from env var or defaults.
        """
        logger.debug(f"Looking up agent info for {agent_id}")
        # TODO: Replace with a robust service discovery mechanism for production.

        # 1. Check loaded registry from environment variable
        agent_details = AGENT_REGISTRY.get(agent_id)
        if agent_details and agent_details.get("endpoint"):
            logger.info(f"Found agent {agent_id} in registry (from env var).")
            return A2aAgentInfo(
                id=agent_id,
                name=agent_details.get("name", agent_id),
                endpoint=agent_details["endpoint"],
            )

        # 2. Fallback to default endpoints (useful for local dev)
        default_endpoint = DEFAULT_ENDPOINTS.get(agent_id)
        if default_endpoint:
            logger.warning(f"Agent {agent_id} not in registry, using default endpoint.")
            return A2aAgentInfo(
                id=agent_id,
                name=f"Agent {agent_id} (Default)",
                endpoint=default_endpoint,
            )

        # 3. Fallback: Check individual environment variables (less ideal)
        env_var_name = f"{agent_id.upper().replace('-', '_')}_ENDPOINT"
        endpoint_from_env = os.getenv(env_var_name)
        if endpoint_from_env:
            logger.warning(
                f"Agent {agent_id} not in registry or defaults, using specific env var {env_var_name}."
            )
            return A2aAgentInfo(
                id=agent_id, name=f"Agent {agent_id} (Env)", endpoint=endpoint_from_env
            )

        # 4. If not found anywhere
        logger.error(
            f"Could not determine endpoint for agent {agent_id} from registry, defaults, or specific env var."
        )
        return None

    async def _update_task_status(
        self,
        task_id: TaskId,
        status: TaskStatus,
        result: Optional[Dict] = None,
        error_message: Optional[str] = None,
    ):
        """Updates task status in the database."""
        log_message = f"Task {task_id}: Status changed to {status}."
        if result:
            log_message += f" Result: {result}"
        if error_message:
            log_message += f" Error: {error_message}"
        logger.info(log_message)

        if not self.db:
            logger.error(
                f"Cannot update task {task_id} status: DB client not available."
            )
            return

        update_data = {
            "status": status,
            "updated_at": datetime.datetime.utcnow().isoformat(),
        }
        if status in ["COMPLETED", "FAILED", "CANCELLED"]:
            update_data["completed_at"] = update_data["updated_at"]
        if result:
            try:
                update_data["result"] = json.dumps(result)
            except TypeError:
                logger.error(
                    f"Task {task_id}: Result dictionary is not JSON serializable."
                )
                update_data["result"] = json.dumps({"error": "Result not serializable"})
        if error_message:
            update_data["error_message"] = error_message

        try:
            # Use a2a_task_id as the unique identifier from the A2A protocol
            update_res = (
                await self.db.table("tasks")
                .update(update_data)
                .eq("a2a_task_id", task_id)
                .execute()
            )
            # Check if any rows were updated
            if update_res.data:
                logger.info(f"Successfully updated status for task {task_id} in DB.")
            else:
                logger.warning(
                    f"No task found with a2a_task_id '{task_id}' to update status."
                )
                # Consider inserting if not found, or handle as error depending on desired logic
        except Exception as e:
            logger.error(
                f"Failed to update status for task {task_id} in DB: {e}", exc_info=True
            )

    def get_agent_info(self) -> A2aAgentInfo:
        """Returns the configuration/details of this agent."""
        return self.agent_info


# --- Agent Instantiation ---
# messaging_agent_instance = MessagingAgent()
