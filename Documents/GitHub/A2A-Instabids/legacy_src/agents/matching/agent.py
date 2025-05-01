"""
Placeholder implementation for the Matching Agent.

This agent connects relevant projects (Bid Cards) with suitable contractors.
"""

import logging
from typing import Any, Dict, Optional, List
import os
import uuid  # Import uuid
from dotenv import load_dotenv
from supabase import create_client, Client

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
    ArtifactType,
    TaskStatus,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

AGENT_ID: AgentId = "matching-agent-001"  # Example ID - Should be configurable

# --- Agent Registry (Simple Placeholder) ---
# TODO: Centralize agent registry/discovery
AGENT_REGISTRY_JSON = os.getenv("AGENT_REGISTRY", "{}")
try:
    AGENT_REGISTRY: Dict[AgentId, Dict[str, str]] = json.loads(AGENT_REGISTRY_JSON)
    logger.info(f"Loaded agent registry: {list(AGENT_REGISTRY.keys())}")
except json.JSONDecodeError:
    logger.error(
        "Failed to parse AGENT_REGISTRY env var as JSON. Using default fallbacks."
    )
    AGENT_REGISTRY = {}

DEFAULT_ENDPOINTS = {
    "homeowner-agent-001": "http://localhost:8001",
    "contractor-agent-001": "http://localhost:8003",
    "bid-card-agent-001": "http://localhost:8002",
    "matching-agent-001": "http://localhost:8004",
    "messaging-agent-001": "http://localhost:8005",
    "outreach-agent-001": "http://localhost:8006",
}


class MatchingAgent(AdkAgent):
    """
    InstaBids Agent responsible for matching projects with contractors.
    """

    def __init__(
        self,
        agent_info: Optional[A2aAgentInfo] = None,
        supabase_client: Optional[Client] = None,  # Allow injecting client for testing
    ):
        """Initializes the MatchingAgent."""
        agent_endpoint = os.getenv(
            "MATCHING_AGENT_ENDPOINT", DEFAULT_ENDPOINTS.get(AGENT_ID)
        )
        self.agent_info = agent_info or A2aAgentInfo(
            id=AGENT_ID,
            name="Matching Agent",
            description="Matches projects (Bid Cards) with qualified contractors.",
            endpoint=agent_endpoint,
            capabilities=["project_matching", "contractor_filtering"],
        )
        logger.info(f"Initializing MatchingAgent (ID: {self.agent_info.id})")

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
        """
        Handles tasks like finding contractors for a project or projects for a contractor.
        """
        logger.info(f"MatchingAgent received task: {task.id} - '{task.description}'")
        await self._update_task_status(task.id, "IN_PROGRESS")  # Use helper

        if not self.db:
            error_msg = "Supabase client not available. Cannot process matching task."
            logger.error(f"Task {task.id}: {error_msg}")
            await self._update_task_status(task.id, "FAILED", error_message=error_msg)
            return

        # 1. Determine task type from description or metadata
        task_type = task.metadata.get("match_type") if task.metadata else None
        if not task_type:
            if "find contractors" in task.description.lower():
                task_type = "find_contractors"
            elif "find projects" in task.description.lower():
                task_type = "find_projects"
            else:
                error_msg = "Could not determine match type."
                logger.error(f"Task {task.id}: {error_msg}")
                await self._update_task_status(
                    task.id, "FAILED", error_message=error_msg
                )
                return

        results = None
        error_msg = None
        try:
            if task_type == "find_contractors":
                project_id = task.metadata.get("project_id") if task.metadata else None
                if not project_id:
                    error_msg = "Missing project_id for find_contractors task."
                    logger.error(f"Task {task.id}: {error_msg}")
                else:
                    logger.info(
                        f"Task {task.id}: Finding contractors for project {project_id}"
                    )
                    results = await self.find_contractors_for_project(project_id)

            elif task_type == "find_projects":
                contractor_id = (
                    task.metadata.get("contractor_id") if task.metadata else None
                )
                if not contractor_id:
                    error_msg = "Missing contractor_id for find_projects task."
                    logger.error(f"Task {task.id}: {error_msg}")
                else:
                    logger.info(
                        f"Task {task.id}: Finding projects for contractor {contractor_id}"
                    )
                    results = await self.find_projects_for_contractor(
                        contractor_id, task.metadata
                    )

            else:
                error_msg = f"Unknown match type '{task_type}'."
                logger.warning(f"Task {task.id}: {error_msg}")

            # 4. Update task status with results or error
            if error_msg:
                await self._update_task_status(
                    task.id, "FAILED", error_message=error_msg
                )
            elif results is not None:
                logger.info(
                    f"Task {task.id}: Matching process completed. Results count: {len(results)}"
                )
                # TODO: Create result artifact if results are large or complex
                await self._update_task_status(
                    task.id, "COMPLETED", result={"matches": results}
                )
            else:
                logger.warning(f"Task {task.id}: Matching process yielded no results.")
                await self._update_task_status(
                    task.id, "COMPLETED", result={"matches": []}
                )

        except Exception as e:
            error_msg = f"Error during matching process: {e}"
            logger.error(f"Task {task.id}: {error_msg}", exc_info=True)
            await self._update_task_status(task.id, "FAILED", error_message=error_msg)

    async def handle_message(self, message: Message) -> None:
        """Handles incoming messages (if applicable)."""
        logger.info(
            f"MatchingAgent received message: {message.id} for task {message.task_id}"
        )
        # Might receive updates about contractor availability or new projects.
        print(
            f"TODO: Implement message handling logic if needed for message {message.id}"
        )

    # --- Implemented Matching Logic Methods ---

    async def find_contractors_for_project(
        self, project_id: str
    ) -> Optional[List[AgentId]]:
        """Finds suitable contractor Agent IDs for a given project ID."""
        logger.info(f"Finding contractors for project {project_id}...")
        if not self.db:
            return None

        try:
            # 1. Fetch project details (category, location_description)
            project_res = (
                await self.db.table("projects")
                .select("category, location_description")
                .eq("id", project_id)
                .maybe_single()
                .execute()
            )
            if not project_res.data:
                logger.error(f"Project {project_id} not found for matching.")
                return None
            project_category = project_res.data.get("category")
            project_location = project_res.data.get(
                "location_description"
            )  # Assuming zip code for now

            if not project_category or not project_location:
                logger.warning(
                    f"Project {project_id} missing category or location for matching."
                )
                return []  # Return empty list if essential criteria missing

            # 2. Fetch contractor profiles matching criteria
            # Basic matching: category array contains project category AND location matches (simple zip match for now)
            # TODO: Implement more sophisticated location matching (service area polygons)
            # TODO: Implement vector search for description/profile matching
            # TODO: Add filtering based on availability, ratings etc.
            # TODO: Map contractor user UUIDs back to Agent IDs
            query = self.db.table("contractor_profiles").select(
                "id"
            )  # Select user ID (which maps to agent ID for now)
            query = query.contains(
                "service_categories", [project_category]
            )  # Check if category is in the array
            # Simple zip code match - needs improvement for service areas
            query = query.eq(
                "service_area_description", project_location
            )  # Placeholder for area matching

            contractor_res = await query.execute()

            if not contractor_res.data:
                logger.info(
                    f"No contractors found matching criteria for project {project_id}."
                )
                return []

            # Map contractor user UUIDs to Agent IDs (using placeholder convention)
            # CRITICAL TODO: Replace this with robust mapping (e.g., from AGENT_REGISTRY or DB)
            matching_agent_ids = [
                f"contractor-agent-{profile['id']}" for profile in contractor_res.data
            ]
            logger.info(
                f"Found {len(matching_agent_ids)} potential contractors for project {project_id}."
            )
            return matching_agent_ids

        except Exception as e:
            logger.error(
                f"Error finding contractors for project {project_id}: {e}",
                exc_info=True,
            )
            return None

    async def find_projects_for_contractor(
        self, contractor_id: str, criteria: Optional[Dict] = None
    ) -> Optional[List[str]]:
        """Finds suitable project IDs for a given contractor Agent ID."""
        logger.info(
            f"Finding projects for contractor {contractor_id} with criteria: {criteria}"
        )
        if not self.db:
            return None

        try:
            # 1. Map contractor Agent ID to User UUID
            # CRITICAL TODO: Replace placeholder mapping
            contractor_user_id = None
            agent_details = AGENT_REGISTRY.get(contractor_id)
            if agent_details and agent_details.get("user_id"):
                contractor_user_id = agent_details["user_id"]
            else:
                # Attempt reverse convention (less reliable)
                try:
                    uuid_part = contractor_id.split("contractor-agent-")[-1]
                    uuid.UUID(uuid_part)  # Validate format
                    contractor_user_id = uuid_part
                    logger.warning(
                        f"Using naming convention to map agent {contractor_id} to user {contractor_user_id}"
                    )
                except:
                    logger.error(f"Could not map agent {contractor_id} to user UUID.")
                    return None

            # 2. Fetch contractor profile (categories, location)
            profile_res = (
                await self.db.table("contractor_profiles")
                .select("service_categories, service_area_description")
                .eq("id", contractor_user_id)
                .maybe_single()
                .execute()
            )
            if not profile_res.data:
                logger.error(
                    f"Contractor profile not found for user {contractor_user_id} (Agent: {contractor_id})."
                )
                return None
            contractor_categories = profile_res.data.get("service_categories", [])
            contractor_location = profile_res.data.get(
                "service_area_description"
            )  # Zip code

            if not contractor_categories or not contractor_location:
                logger.warning(
                    f"Contractor {contractor_id} missing categories or location."
                )
                return []

            # 3. Fetch open projects matching criteria
            query = self.db.table("projects").select("id")
            query = query.eq("status", "open")
            query = query.contained_by(
                "category", contractor_categories
            )  # Project category must be one the contractor handles
            query = query.eq(
                "location_description", contractor_location
            )  # Simple zip match

            # TODO: Add criteria from task metadata if provided (e.g., specific project type)
            # if criteria and criteria.get("project_type"):
            #     query = query.eq("metadata->>project_type", criteria["project_type"])

            project_res = await query.execute()

            if not project_res.data:
                logger.info(
                    f"No matching open projects found for contractor {contractor_id}."
                )
                return []

            matching_project_ids = [project["id"] for project in project_res.data]
            logger.info(
                f"Found {len(matching_project_ids)} potential projects for contractor {contractor_id}."
            )
            # TODO: Return Bid Card Artifact IDs instead? Requires linking projects to bid cards.
            return matching_project_ids

        except Exception as e:
            logger.error(
                f"Error finding projects for contractor {contractor_id}: {e}",
                exc_info=True,
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
        # (Implementation copied from HomeownerAgent - TODO: Centralize this utility)
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
            update_res = (
                await self.db.table("tasks")
                .update(update_data)
                .eq("a2a_task_id", task_id)
                .execute()
            )
            if update_res.data:
                logger.info(f"Successfully updated status for task {task_id} in DB.")
            else:
                logger.warning(
                    f"No task found with a2a_task_id '{task_id}' to update status."
                )
        except Exception as e:
            logger.error(
                f"Failed to update status for task {task_id} in DB: {e}", exc_info=True
            )

    def get_agent_info(self) -> A2aAgentInfo:
        """Returns the configuration/details of this agent."""
        return self.agent_info


# --- Agent Instantiation ---
# matching_agent_instance = MatchingAgent()
