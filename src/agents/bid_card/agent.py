"""
Placeholder implementation for the Bid Card Agent.

This agent standardizes project requests into structured "Bid Card" artifacts.
"""

import logging
from typing import Any, Dict, Optional, List
import os
import uuid # Import uuid
from dotenv import load_dotenv
from supabase import create_client, Client

# Assuming ADK and A2A types are accessible
# Adjust import paths based on final project structure
from google.adk.agents import Agent as AdkAgent
from ...a2a_types.core import Task, Message, Artifact, AgentId, TaskId, MessageId, Agent as A2aAgentInfo, ArtifactType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

AGENT_ID: AgentId = "bid-card-agent-001" # Example ID - Should be configurable

class BidCardAgent(AdkAgent):
    """
    InstaBids Agent responsible for creating standardized Bid Card artifacts.
    """

    def __init__(
        self,
        agent_info: Optional[A2aAgentInfo] = None,
        supabase_client: Optional[Client] = None, # Allow injecting client for testing
    ):
        """Initializes the BidCardAgent."""
        agent_endpoint = os.getenv("BID_CARD_AGENT_ENDPOINT", "http://localhost:8002")
        self.agent_info = agent_info or A2aAgentInfo(
            id=AGENT_ID,
            name="Bid Card Agent",
            description="Transforms project details into standardized Bid Card artifacts.",
            endpoint=agent_endpoint,
            capabilities=["bid_card_creation"]
        )
        logger.info(f"Initializing BidCardAgent (ID: {self.agent_info.id})")

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
        """
        Handles the task to create a Bid Card artifact for a given project.
        Fetches project details from Supabase and structures the Bid Card data.
        """
        logger.info(f"BidCardAgent received task: {task.id} - '{task.description}'")
        # TODO: Update task status to IN_PROGRESS

        if not self.db:
            logger.error(f"Task {task.id}: Supabase client not available. Cannot process.")
            # TODO: Update task status to FAILED
            return

        # 1. Extract project_id from task metadata
        project_id = task.metadata.get("project_id") if task.metadata else None
        if not project_id:
            logger.error(f"Task {task.id}: Missing 'project_id' in task metadata.")
            # TODO: Update task status to FAILED
            return

        logger.info(f"Task {task.id}: Processing project {project_id}")

        try:
            # 2. Fetch project details from Supabase
            project_res = await self.db.table("projects").select("*").eq("id", project_id).maybe_single().execute()
            logger.debug(f"Task {task.id}: Supabase project fetch response: {project_res}")

            if not project_res.data:
                logger.error(f"Task {task.id}: Project {project_id} not found in database.")
                # TODO: Update task status to FAILED
                return

            project_data = project_res.data

            # 3. Fetch associated photos
            photo_res = await self.db.table("project_photos").select("storage_path, caption").eq("project_id", project_id).execute()
            logger.debug(f"Task {task.id}: Supabase photos fetch response: {photo_res}")
            photo_data = photo_res.data or []

            # 4. Structure the Bid Card data
            # Define the structure clearly. Include essential, non-sensitive info.
            bid_card_content = {
                "project_id": project_data.get("id"),
                "title": project_data.get("title"),
                "description": project_data.get("description"),
                "category": project_data.get("category"),
                "location_description": project_data.get("location_description"), # e.g., zip code
                "project_type": project_data.get("metadata", {}).get("project_type"),
                "timeline": project_data.get("metadata", {}).get("timeline"),
                "allow_group_bidding": project_data.get("metadata", {}).get("allow_group_bidding"),
                "photos": [
                    {"path": p.get("storage_path"), "caption": p.get("caption")}
                    for p in photo_data
                ],
                "created_at": str(project_data.get("created_at")), # Convert to string for JSON
                # Add other relevant fields, EXCLUDING homeowner PII
            }
            # Clean None values from the final dict if desired
            bid_card_content = {k: v for k, v in bid_card_content.items() if v is not None}

            logger.info(f"Task {task.id}: Successfully structured Bid Card content for project {project_id}.")
            # logger.debug(f"Bid Card Content: {bid_card_content}") # Be careful logging potentially large data

            # 5. Create A2A Artifact (Simulated)
            # In a real implementation, this would involve:
            # - Generating a unique artifact ID.
            # - Deciding on storage: Store JSON directly in artifact content,
            #   or save JSON to Supabase Storage/other store and put URI in artifact.
            # - Using an A2A mechanism (e.g., calling a central task manager or artifact service)
            #   to register the artifact and associate it with the task.
            artifact_id = f"art_{uuid.uuid4()}" # Placeholder ID
            logger.info(f"Task {task.id}: (Simulated) Created Bid Card artifact {artifact_id}")
            print(f"TODO: Implement actual A2A Artifact creation for task {task.id}, artifact {artifact_id}")


            # 6. Update task status to COMPLETED (Simulated)
            # In a real implementation, this would involve:
            # - Calling the A2A server/task manager to update the task status.
            # - Potentially sending a notification message back to the task creator (HomeownerAgent).
            logger.info(f"Task {task.id}: (Simulated) Marking task as COMPLETED.")
            print(f"TODO: Implement actual A2A Task status update for task {task.id}")
            # Example result structure:
            task_result = {"bid_card_artifact_id": artifact_id}
            print(f"Task {task.id} result (simulated): {task_result}")


        except Exception as e:
            logger.error(f"Task {task.id}: Error processing Bid Card creation for project {project_id}: {e}", exc_info=True)
            # TODO: Update task status to FAILED


    async def handle_message(self, message: Message) -> None:
        """Handles incoming messages (if applicable for this agent)."""
        logger.info(f"BidCardAgent received message: {message.id} for task {message.task_id}")
        # This agent might not need complex message handling if it only processes tasks.
        print(f"TODO: Implement message handling logic if needed for message {message.id}")

    def get_agent_info(self) -> A2aAgentInfo:
        """Returns the configuration/details of this agent."""
        return self.agent_info

# --- Agent Instantiation ---
# bid_card_agent_instance = BidCardAgent()
