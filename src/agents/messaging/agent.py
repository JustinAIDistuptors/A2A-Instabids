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
import uuid # Import uuid

# Assuming ADK and A2A types are accessible
# Adjust import paths based on final project structure
from google.adk.agents import Agent as AdkAgent
from ...a2a_types.core import Task, Message, Artifact, AgentId, TaskId, MessageId, Agent as A2aAgentInfo
# Import A2A client functions if this agent needs to forward messages
from ...a2a_comm import client as a2a_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

AGENT_ID: AgentId = "messaging-agent-001" # Example ID - Should be configurable

class MessagingAgent(AdkAgent):
    """
    InstaBids Agent responsible for filtering and routing messages.
    """

    def __init__(
        self,
        agent_info: Optional[A2aAgentInfo] = None,
        supabase_client: Optional[Client] = None, # Allow injecting client for testing
    ):
        """Initializes the MessagingAgent."""
        agent_endpoint = os.getenv("MESSAGING_AGENT_ENDPOINT", "http://localhost:8005")
        self.agent_info = agent_info or A2aAgentInfo(
            id=AGENT_ID,
            name="Messaging Agent",
            description="Filters and routes messages between homeowners and contractors.",
            endpoint=agent_endpoint,
            capabilities=["message_filtering", "message_routing"]
        )
        logger.info(f"Initializing MessagingAgent (ID: {self.agent_info.id})")

        # Initialize Supabase client if not injected
        if supabase_client:
            self.db: Client = supabase_client
        else:
            supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
            supabase_key: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
            if not supabase_url or not supabase_key:
                logger.error("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables.")
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

        # TODO: Implement task handling logic
        # Example: Handle broadcast task
        if task.metadata and task.metadata.get("action") == "broadcast":
            project_id = task.metadata.get("project_id")
            broadcast_content = task.metadata.get("content")
            sender_id = task.creator_agent_id # Agent initiating the broadcast

            if project_id and broadcast_content and sender_id:
                logger.info(f"Task {task.id}: Processing broadcast for project {project_id}")
                await self._handle_broadcast(project_id, sender_id, broadcast_content)
            else:
                logger.error(f"Task {task.id}: Missing data for broadcast task.")
                # TODO: Update task status to FAILED
        else:
            print(f"TODO: Implement general task handling logic for task {task.id}")


    async def handle_message(self, message: Message) -> None:
        """
        Handles incoming messages, applies filtering rules, and forwards if allowed.
        This is the core function of this agent.
        """
        logger.info(f"MessagingAgent received message: {message.id} for task {message.task_id} from {message.sender_agent_id} to {message.recipient_agent_id}")

        # TODO: Handle potential message attachments (photos, documents) referenced in message.artifacts or metadata.
        # The upload/moderation happens *before* the message is sent here. This agent just routes the message
        # containing the reference (e.g., storage path).

        if not self.db:
            logger.error(f"Message {message.id}: Supabase client not available. Cannot process.")
            # Optionally notify sender of system error
            return

        # 1. Determine the actual intended recipient
        # Assumes message.recipient_agent_id holds the final intended recipient.
        # If messages are always sent *to* the MessagingAgent first, logic here would look up the intended recipient.
        final_recipient_agent_id = message.recipient_agent_id
        logger.debug(f"Message {message.id}: Identified final recipient as {final_recipient_agent_id}")

        # 2. Check filtering rules based on context (e.g., project/bid status)
        # Requires project_id, which might be in task_id or message metadata
        # TODO: Robustly determine project_id from message/task context
        project_id = message.metadata.get("project_id") if message.metadata else None
        if not project_id:
             # Attempt to get from task DB if task_id is available and maps to a project
             logger.warning(f"Message {message.id}: Missing project_id context. Filtering may be limited.")
             # For now, proceed with limited filtering or default allow/deny

        allowed, reason = await self._should_allow_message(project_id, message.sender_agent_id, final_recipient_agent_id)

        if allowed:
            # 3. TODO: Apply content redaction if necessary (based on rules and bid status)
            modified_content = message.content # Placeholder
            print(f"TODO: Implement content redaction for message {message.id}")

            # 4. TODO: Apply pseudonymity if necessary (e.g., show "Contractor A" to homeowner)
            # This might involve modifying the sender_agent_id or adding display info to metadata
            # before forwarding, depending on the recipient.
            print(f"TODO: Implement pseudonymity logic for message {message.id}")


            # 5. Get recipient agent details (endpoint) for forwarding
            recipient_agent_info = await self._get_recipient_agent_info(final_recipient_agent_id)

            if recipient_agent_info:
                # 6. Forward the message using the A2A client
                logger.info(f"Message {message.id}: Forwarding to {final_recipient_agent_id}")
                try:
                    # Ensure the message being sent reflects any modifications (content, sender alias)
                    # For now, sending original message details + modified content
                    forward_success = await a2a_client.send_message(
                        target_agent=recipient_agent_info,
                        task_id=message.task_id,
                        role=message.role,
                        content=modified_content, # Send potentially redacted content
                        sender_agent_id=message.sender_agent_id, # Keep original sender for routing logic
                        session_id=message.session_id,
                        artifacts=message.artifacts,
                        metadata=message.metadata # TODO: Add pseudonymity info if needed by recipient UI
                    )
                    if not forward_success:
                         logger.error(f"Message {message.id}: Failed to forward message via A2A client.")
                         # TODO: Handle forwarding failure (e.g., notify sender)

                except Exception as e:
                     logger.error(f"Message {message.id}: Error forwarding message: {e}", exc_info=True)
                     # TODO: Handle forwarding exception

            else:
                logger.error(f"Message {message.id}: Could not find recipient agent details for {final_recipient_agent_id}. Cannot forward.")
                # TODO: Handle recipient not found

        else:
            # 7. Message blocked by filtering rules
            logger.warning(f"Message {message.id}: Blocked. Reason: {reason}")
            # TODO: Optionally notify the sender that the message was blocked/filtered.


    async def _should_allow_message(self, project_id: Optional[str], sender_id: AgentId, recipient_id: AgentId) -> Tuple[bool, str]:
        """Checks if communication is allowed based on project/bid status."""
        logger.debug(f"Checking filter rules for project {project_id}, sender {sender_id}, recipient {recipient_id}")

        if not project_id:
            # Cannot apply project-specific rules without project_id
            return False, "Blocked: Missing project context"

        if not self.db:
            return False, "Blocked: Database connection unavailable"

        try:
            # TODO: Determine if sender/recipient are homeowner or contractor based on Agent ID mapping or type
            # This requires a robust way to map AgentId to user_type or a specific user record.
            sender_is_contractor = "contractor-agent" in sender_id # Placeholder logic
            recipient_is_contractor = "contractor-agent" in recipient_id # Placeholder logic
            homeowner_agent_id = None
            contractor_agent_id = None # This is the AgentId
            contractor_user_id = None # This is the UUID from the 'users' table

            if sender_is_contractor and not recipient_is_contractor:
                contractor_agent_id = sender_id
                homeowner_agent_id = recipient_id
                # TODO: Map contractor_agent_id to contractor_user_id (UUID)
                # This mapping is CRITICAL and needs a proper implementation (e.g., DB lookup, naming convention)
                # Example placeholder - replace with actual mapping logic
                # user_res = await self.db.table("users").select("id").eq("agent_id_mapping", contractor_agent_id).maybe_single().execute()
                # if user_res.data: contractor_user_id = user_res.data['id']
                logger.warning("Placeholder mapping used for contractor AgentID to UserID")
                contractor_user_id = contractor_agent_id # TEMPORARY WRONG MAPPING
            elif not sender_is_contractor and recipient_is_contractor:
                homeowner_agent_id = sender_id
                contractor_agent_id = recipient_id
                # TODO: Map contractor_agent_id to contractor_user_id (UUID)
                logger.warning("Placeholder mapping used for contractor AgentID to UserID")
                contractor_user_id = contractor_agent_id # TEMPORARY WRONG MAPPING
            elif sender_is_contractor and recipient_is_contractor:
                return False, "Blocked: Contractor-to-contractor messaging not supported"
            else: # Homeowner-to-homeowner
                 return False, "Blocked: Homeowner-to-homeowner messaging not supported"

            if not homeowner_agent_id or not contractor_user_id: # Check user_id now
                 logger.warning(f"Could not map agent IDs to user roles/UUIDs for project {project_id}")
                 return False, "Blocked: Could not identify homeowner/contractor roles or map AgentID to UserID"


            # Fetch relevant bid(s) between this contractor and project
            # Corrected query chaining for clarity and syntax robustness
            query = self.db.table("bids").select("status")
            query = query.eq("project_id", project_id)
            query = query.eq("contractor_id", contractor_user_id) # Use the contractor's user UUID
            bid_res = await query.execute()

            bids = bid_res.data or []
            has_accepted_bid = any(bid.get("status") == "accepted" for bid in bids)
            has_pending_bid = any(bid.get("status") == "pending" for bid in bids)

            # Rule 1: Communication always allowed if bid is accepted
            if has_accepted_bid:
                return True, "Allowed: Bid accepted"

            # Rule 2: Communication allowed if bid is pending
            if has_pending_bid:
                # TODO: Add logic here or in handle_message to redact contact info
                return True, "Allowed: Bid pending (redaction may apply)"

            # Rule 3: Allow initial contact from contractor *before* bid placement
            # Requires tracking initial contact - how?
            # Option A: Check if *any* message exists between them for this project (requires message DB lookup)
            # Option B: A separate 'project_interactions' table entry is created on first contact intent.
            # Let's simulate Option A (less efficient but simpler for now):
            # TODO: Implement check for existing messages between sender/recipient for this project_id
            has_prior_contact = False # Placeholder
            print(f"TODO: Check for prior contact between {sender_id} and {recipient_id} for project {project_id}")
            if sender_is_contractor and has_prior_contact:
                 return True, "Allowed: Follow-up contact"
            if sender_is_contractor and not has_pending_bid and not has_prior_contact:
                 # Allow the *first* message from contractor to homeowner pre-bid
                 # This assumes the message context indicates it's the first one. Risky.
                 # A dedicated "initiate contact" action might be better.
                 # For now, let's allow if no bids exist yet from this contractor.
                 if not bids:
                     return True, "Allowed: Initial pre-bid contact"


            # Default Deny
            return False, "Blocked: No accepted/pending bid or prior contact"

        except Exception as e:
            logger.error(f"Error checking message permissions for project {project_id}: {e}", exc_info=True)
            return False, "Blocked: Error checking permissions"


    async def _handle_broadcast(self, project_id: str, sender_id: AgentId, content: Any):
        """Handles broadcasting a message to relevant contractors for a project."""
        logger.info(f"Handling broadcast from {sender_id} for project {project_id}")
        if not self.db:
            logger.error("Cannot broadcast: Supabase client unavailable.")
            return

        try:
            # Find all contractors (user UUIDs) who have placed a bid or initiated contact
            # TODO: Refine query to include contractors who initiated contact (Rule 3)
            bids_res = await self.db.table("bids").select("contractor_id").eq("project_id", project_id).execute()
            if not bids_res.data:
                logger.info(f"No bidders found for project {project_id}. Nothing to broadcast.")
                return

            recipient_user_ids = list(set(bid["contractor_id"] for bid in bids_res.data)) # Get unique contractor user UUIDs

            logger.info(f"Broadcasting to recipients (User IDs): {recipient_user_ids} for project {project_id}")

            for recipient_user_id in recipient_user_ids:
                 # TODO: Map recipient_user_id (UUID) to Agent ID and get AgentInfo
                 # This mapping is crucial and needs a defined strategy.
                 # Placeholder: Assume a convention or lookup table exists.
                 recipient_agent_id = f"contractor-agent-{str(recipient_user_id)[:8]}" # Highly simplified placeholder mapping
                 recipient_agent_info = await self._get_recipient_agent_info(recipient_agent_id)

                 if recipient_agent_info:
                     try:
                         # Send individual message via A2A client
                         await a2a_client.send_message(
                             target_agent=recipient_agent_info,
                             task_id=f"broadcast_{project_id}", # Use a relevant task ID or None
                             role="SYSTEM", # Or sender's role? Indicate it's a broadcast.
                             content=content,
                             sender_agent_id=sender_id, # Original sender (e.g., HomeownerAgent)
                             metadata={"broadcast": True, "project_id": project_id}
                         )
                     except Exception as e:
                         logger.error(f"Failed to send broadcast message to {recipient_agent_id} (User: {recipient_user_id}) for project {project_id}: {e}")
                 else:
                     logger.warning(f"Could not find agent info for recipient user {recipient_user_id}. Skipping broadcast.")

        except Exception as e:
            logger.error(f"Error during broadcast for project {project_id}: {e}", exc_info=True)


    async def _get_recipient_agent_info(self, agent_id: AgentId) -> Optional[A2aAgentInfo]:
        """Placeholder: Retrieves agent details (especially endpoint) for forwarding."""
        logger.debug(f"Looking up agent info for {agent_id}")
        # TODO: Implement agent lookup mechanism
        # - Could be a simple config lookup, environment variables, or a dedicated service discovery mechanism.
        # - For dedicated user agents, might need to map user ID to agent instance/endpoint.
        print(f"TODO: Implement agent info lookup for {agent_id}")
        # Placeholder: Assume endpoint is based on agent ID convention or env var
        # Convert agent ID to uppercase and replace hyphens for typical env var format
        env_var_name = f"{agent_id.upper().replace('-', '_')}_ENDPOINT"
        endpoint = os.getenv(env_var_name)
        if endpoint:
            return A2aAgentInfo(id=agent_id, name=f"Agent {agent_id}", endpoint=endpoint) # Minimal info needed
        else:
            # Fallback for known agents if env var not set
            if agent_id == "homeowner-agent-001":
                 return A2aAgentInfo(id=agent_id, name="Homeowner Agent", endpoint="http://localhost:8001")
            if agent_id == "contractor-agent-001":
                 return A2aAgentInfo(id=agent_id, name="Contractor Agent", endpoint="http://localhost:8003")
            # Add other known agents (BidCard, Matching) if they need to receive messages directly
            logger.warning(f"Could not determine endpoint for agent {agent_id} from env var {env_var_name} or fallbacks.")
            return None


    def get_agent_info(self) -> A2aAgentInfo:
        """Returns the configuration/details of this agent."""
        return self.agent_info

# --- Agent Instantiation ---
# messaging_agent_instance = MessagingAgent()
