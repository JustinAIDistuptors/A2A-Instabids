"""
Implementation for the Homeowner Agent.

Handles homeowner onboarding, project creation (photo-first optional flow),
competitive quote upload, and bid selection interactions.
"""

import logging
from typing import Any, Dict, Optional, Union, List
import uuid # For generating placeholder IDs
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Assuming ADK and A2A types are accessible
# Adjust import paths based on final project structure
from google.adk.agents import Agent as AdkAgent # Alias to avoid name clash
# from google.adk.flows import SequentialFlow, LLMFlow # Example ADK flows
from ...a2a_types.core import Task, Message, Artifact, AgentId, TaskId, MessageId, Agent as A2aAgentInfo, ArtifactType
# Import A2A client to trigger other agents
from ...a2a_comm import client as a2a_client
# from google.adk.flows import SequentialFlow, LLMFlow # Example ADK flows
from ...a2a_types.core import Task, Message, Artifact, AgentId, TaskId, MessageId, Agent as A2aAgentInfo, ArtifactType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

AGENT_ID: AgentId = "homeowner-agent-001" # Example ID - Should be configurable

class HomeownerAgent(AdkAgent):
    """
    InstaBids Agent responsible for homeowner interactions.
    Manages the project creation process, potentially starting with photos or quotes.
    """

    def __init__(
        self,
        agent_info: Optional[A2aAgentInfo] = None,
        supabase_client: Optional[Client] = None, # Allow injecting client for testing
        # vision_service: Optional[Any] = None,
        # ocr_service: Optional[Any] = None,
        # llm_service: Optional[Any] = None,
    ):
        """
        Initializes the HomeownerAgent.

        Args:
            agent_info: Configuration details for this agent instance.
            supabase_client: Optional pre-configured Supabase client.
            # vision_service: Service for image analysis.
            # ocr_service: Service for document text extraction.
            # llm_service: Service for conversational AI and text analysis.
        """
        # Load agent configuration (ID, name, endpoint, etc.)
        agent_endpoint = os.getenv("HOMEOWNER_AGENT_ENDPOINT", "http://localhost:8001")
        self.agent_info = agent_info or A2aAgentInfo(
            id=AGENT_ID,
            name="Homeowner Agent",
            description="Assists homeowners with project creation and contractor selection.",
            endpoint=agent_endpoint,
            capabilities=["project_creation", "bid_review", "quote_upload"]
        )
        logger.info(f"Initializing HomeownerAgent (ID: {self.agent_info.id})")

        # Initialize Supabase client if not injected
        if supabase_client:
            self.db: Client = supabase_client
        else:
            supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
            supabase_key: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
            if not supabase_url or not supabase_key:
                logger.error("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables.")
                # Depending on desired behavior, could raise error or disable DB features
                self.db = None # Indicate DB is unavailable
            else:
                try:
                    self.db: Client = create_client(supabase_url, supabase_key)
                    logger.info("Supabase client initialized successfully.")
                except Exception as e:
                    logger.error(f"Failed to initialize Supabase client: {e}")
                    self.db = None

        # Store other injected dependencies
        # self.vision = vision_service
        # self.ocr = ocr_service
        # self.llm = llm_service

        # TODO: Initialize ADK flows or other internal state if needed
        # super().__init__(...) # Call parent initializer if needed

    async def handle_create_task(self, task: Task) -> None:
        """
        Handles an incoming task, typically 'create_new_project'.
        This orchestrates the project creation flow based on initial input.
        """
        logger.info(f"HomeownerAgent received task: {task.id} - '{task.description}'")
        # TODO: Update task status to IN_PROGRESS via A2A client or persistence layer

        # Determine initial input type based on task description or artifacts
        initial_input_type = await self._determine_initial_input(task)
        project_context = {}

        if initial_input_type == "photo":
            logger.info(f"Task {task.id}: Starting photo-first flow.")
            # TODO: Handle photo upload/retrieval from task artifacts
            # TODO: Call vision analysis service
            # project_context = await self._analyze_photo(task.artifacts) # Placeholder
            print("TODO: Implement photo analysis")
            pass
        elif initial_input_type == "quote":
            logger.info(f"Task {task.id}: Starting quote upload flow.")
            # TODO: Handle quote document upload/retrieval
            # TODO: Call OCR/extraction service
            # TODO: Redact price information
            # project_context = await self._analyze_quote(task.artifacts) # Placeholder
            print("TODO: Implement quote analysis")
            pass
        elif initial_input_type == "describe":
            logger.info(f"Task {task.id}: Starting description-first flow.")
            # Context might come directly from task description
            project_context['description'] = task.description
            pass
        else: # Includes skipped photo/quote
             logger.info(f"Task {task.id}: No initial photo/quote, starting description flow.")
             # Proceed directly to gathering details
             pass

        # --- Mode Selection ---
        # TODO: Interact with user (via appropriate channel) to select Chat or Form mode
        interaction_mode = "chat" # Placeholder - should be determined by user interaction
        logger.info(f"Task {task.id}: Proceeding with {interaction_mode} mode.")

        # --- Gather Remaining Details ---
        if interaction_mode == "chat":
            project_details = await self._gather_details_chat(task.id, project_context)
        else: # form mode
            project_details = await self._gather_details_form(task.id, project_context)

        # --- Save Project ---
        if project_details:
            project_id = await self._save_project_to_db(project_details)
            if project_id:
                logger.info(f"Task {task.id}: Project saved successfully with ID {project_id}.")
                # --- Trigger Bid Card Agent ---
                await self._trigger_bid_card_creation(task.id, project_id, project_details)
                # TODO: Update task status to COMPLETED
                # TODO: Send confirmation back to the user/originating agent
            else:
                logger.error(f"Task {task.id}: Failed to save project to database.")
                # TODO: Update task status to FAILED and notify user/originator
        else:
             logger.warning(f"Task {task.id}: Failed to gather sufficient project details.")
             # TODO: Update task status to FAILED or handle incomplete flow

    async def _determine_initial_input(self, task: Task) -> str:
        """Placeholder: Analyzes task to see if photo/quote artifact is present."""
        # TODO: Check task.artifacts for photo or document types
        # Based on user interaction model, this might also check task.description
        # for keywords like "upload quote" or rely on a specific task type.
        print("TODO: Implement logic to determine initial input type (photo/quote/describe/skip)")
        # Example logic:
        # if any(artifact.type == ArtifactType.IMAGE for artifact in task.artifacts): return "photo"
        # if any(artifact.type == ArtifactType.FILE for artifact in task.artifacts): return "quote" # Needs refinement
        return "describe" # Default if nothing specific found

    async def _gather_details_chat(self, task_id: TaskId, initial_context: Dict) -> Optional[Dict]:
        """Placeholder for conversational detail gathering using LLM/ADK Flow."""
        logger.info(f"Task {task_id}: Starting chat flow with context: {initial_context}")
        # TODO: Implement conversational flow (e.g., using ADK LLMFlow)
        # - Use initial_context to guide questions.
        # - Ask for: Title, Description (refine if needed), Category, Project Type, Location (zip), Timeline/Urgency.
        # - Ask for Group Bidding preference.
        # - Prompt for photos if not provided initially or allow adding more.
        # - Handle state, context, user responses.
        # - Return structured project details dict or None if failed.

        # --- ADK LLMFlow Conceptual Outline ---
        # This method would likely initialize and run an ADK LLMFlow.
        # The flow would manage the conversation state and transitions.

        # 1. Define Flow States (Examples):
        #    - START: Initial state, use initial_context.
        #    - GATHER_DESCRIPTION: If description is missing or needs clarification.
        #    - GATHER_PROJECT_TYPE: Ask for project type.
        #    - GATHER_CATEGORY: Ask for category based on type.
        #    - GATHER_LOCATION: Ask for zip code.
        #    - GATHER_TIMELINE: Ask for timeframe.
        #    - CONFIRM_GROUP_BIDDING: Ask preference.
        #    - HANDLE_PHOTOS: Ask about adding photos.
        #    - CONFIRM_DETAILS: Show summary and ask for confirmation.
        #    - DONE: All details gathered.
        #    - FAILED: User abandoned or essential info missing.

        # 2. Define State Transitions:
        #    - Based on LLM analysis of user input or specific answers.
        #    - Example: From GATHER_DESCRIPTION, if LLM extracts enough info,
        #      transition to GATHER_PROJECT_TYPE, else stay in GATHER_DESCRIPTION.

        # 3. Define Prompts for each state:
        #    - Include context (e.g., photo analysis results, previously gathered details).
        #    - Instruct the LLM on what information to gather next.
        #    - Example Prompt (GATHER_LOCATION):
        #      "Context: Project Description='{description}', Category='{category}'.
        #      User Input: '{user_message}'.
        #      Task: Ask the user for the zip code where the project is located.
        #      If the user provides it, extract the zip code.
        #      Output Format: {'zip_code': 'extracted_zip', 'next_state': 'GATHER_TIMELINE'}"

        # 4. Initialize and Run Flow:
        #    llm_flow = LLMFlow(
        #        llm=self.llm, # Requires configured LLM client
        #        prompt_template=..., # Template incorporating state logic
        #        initial_state="START",
        #        final_states=["DONE", "FAILED"],
        #        state_mapping=... # Logic to map LLM output to state transitions/data updates
        #    )
        #    result_state, gathered_data = await llm_flow.run(
        #        initial_context=initial_context,
        #        # Need mechanism to feed user messages from handle_message into the flow
        #    )

        # 5. Process Flow Result:
        #    if result_state == "DONE":
        #        logger.info(f"ADK Flow completed. Gathered details: {gathered_data}")
        #        return gathered_data
        #    else:
        #        logger.warning(f"Task {task_id}: ADK Flow ended in state {result_state}.")
        #        return None

        # --- Fallback Simulation (until ADK Flow is implemented) ---
        print("TODO: Implement chat-based detail gathering using ADK LLMFlow.")
        logger.info(f"Task {task_id}: Using fallback simulation for chat gathering.")
        gathered_details = initial_context.copy()
        gathered_details.update({ # Simulate gathering some data
            "title": gathered_details.get("title", "Simulated Project Title"),
            "description": gathered_details.get("description", "Simulated project description."),
            "category": gathered_details.get("category", "Simulated Category"),
            "project_type": gathered_details.get("project_type", "one-time"),
            "location_description": gathered_details.get("location_description", "90210"),
            "timeline": gathered_details.get("timeline", "within_month"),
            "allow_group_bidding": gathered_details.get("allow_group_bidding", True),
            "photo_paths": gathered_details.get("photo_paths", ["simulated/photo.jpg"])
        })
        logger.info(f"Simulated chat gathered details: {gathered_details}")
        if not gathered_details.get("description") or not gathered_details.get("location_description"):
             logger.warning(f"Task {task_id}: Missing essential details after simulated chat.")
             return None
        return gathered_details


    async def _gather_details_form(self, task_id: TaskId, initial_context: Dict) -> Optional[Dict]:
        """Placeholder for structured/form-based detail gathering."""
        logger.info(f"Task {task_id}: Starting form flow with context: {initial_context}")
        # TODO: Implement sequential questioning or form-filling logic.
        # - Pre-fill based on initial_context.
        # - Ask for same details as chat flow.
        # - Handle user input validation.
        # - Return structured project details dict or None if failed.
        print("TODO: Implement form-based detail gathering")
         # Placeholder result (similar structure to chat):
        gathered_details = initial_context
        gathered_details.update({
            "title": "Placeholder Title from Form",
            "description": initial_context.get("description", "Placeholder description from form"),
            "category": "Placeholder Category",
            "project_type": "one-time",
            "location_description": "90210",
            "timeline": "within_month",
            "allow_group_bidding": False,
            "photo_paths": []
        })
        return gathered_details

    async def _save_project_to_db(self, details: Dict) -> Optional[str]:
        """Saves the gathered project details to the Supabase database."""
        if not self.db:
            logger.error("Supabase client not initialized. Cannot save project.")
            return None

        logger.info(f"Attempting to save project: {details.get('title')}")

        # --- Prepare Project Data ---
        project_data = {
            # Assuming the agent context knows the homeowner_id, needs to be passed/retrieved
            "homeowner_id": details.get("homeowner_id", str(uuid.uuid4())), # Placeholder - MUST BE REPLACED
            "title": details.get("title", "Untitled Project"),
            "description": details.get("description"),
            "category": details.get("category"),
            "location_description": details.get("location_description"),
            "status": "open", # Default status for new projects
            "metadata": {
                # Store less structured or evolving fields here
                "project_type": details.get("project_type"),
                "timeline": details.get("timeline"),
                "allow_group_bidding": details.get("allow_group_bidding", False),
                # Add other relevant details from the gathering process
            }
        }
        # Remove None values to avoid inserting NULLs where default might be better
        project_data = {k: v for k, v in project_data.items() if v is not None}
        project_metadata = project_data.get("metadata", {})
        project_metadata = {k: v for k, v in project_metadata.items() if v is not None}
        project_data["metadata"] = project_metadata if project_metadata else None


        # --- Prepare Photo Data ---
        photo_paths = details.get("photo_paths", []) # Expecting a list of storage paths

        try:
            # --- Insert Project ---
            insert_res = await self.db.table("projects").insert(project_data).execute()
            logger.debug(f"Supabase project insert response: {insert_res}")

            if not insert_res.data:
                logger.error(f"Failed to insert project into Supabase. Response: {insert_res}")
                return None

            project_id = insert_res.data[0]['id']
            logger.info(f"Project {project_id} inserted successfully.")

            # --- Insert Photos (if any) ---
            if photo_paths and project_id:
                photo_insert_data = [
                    {"project_id": project_id, "storage_path": path}
                    for path in photo_paths if isinstance(path, str) # Basic validation
                ]
                if photo_insert_data:
                    photo_res = await self.db.table("project_photos").insert(photo_insert_data).execute()
                    logger.debug(f"Supabase photo insert response: {photo_res}")
                    if not photo_res.data:
                         # Log error but don't necessarily fail the whole process? Or should we?
                         logger.error(f"Failed to insert some/all photos for project {project_id}. Response: {photo_res}")
                    else:
                         logger.info(f"Inserted {len(photo_res.data)} photos for project {project_id}.")

            return project_id

        except Exception as e:
            logger.error(f"Error saving project to Supabase: {e}", exc_info=True)
            # Consider more specific error handling (e.g., duplicate errors, connection errors)
            return None


    async def _trigger_bid_card_creation(self, original_task_id: TaskId, project_id: str, project_details: Dict):
        """Creates a task for the BidCardAgent to process the newly created project."""
        logger.info(f"Triggering Bid Card creation for project {project_id}")

        # TODO: Retrieve BidCardAgent details dynamically (e.g., from config or service discovery)
        # For now, using placeholder/environment variables
        bid_card_agent_id = os.getenv("BID_CARD_AGENT_ID", "bid-card-agent-001")
        bid_card_agent_endpoint = os.getenv("BID_CARD_AGENT_ENDPOINT", "http://localhost:8002")

        if not bid_card_agent_endpoint:
            logger.error("Bid Card Agent endpoint not configured. Cannot trigger task.")
            return

        target_agent_info = A2aAgentInfo(
            id=bid_card_agent_id,
            name="Bid Card Agent", # Name/desc might not be strictly needed by client
            endpoint=bid_card_agent_endpoint
        )

        task_description = f"Generate standardized Bid Card artifact for project {project_id}"
        task_metadata = {
            "project_id": project_id,
            "original_task_id": original_task_id,
            # Pass other relevant details if needed, or rely on BidCardAgent fetching project data
            "project_title": project_details.get("title"),
            "project_category": project_details.get("category"),
        }

        try:
            created_task = await a2a_client.create_task(
                target_agent=target_agent_info,
                description=task_description,
                metadata=task_metadata
                # Pass artifacts if needed (e.g., initial photo analysis results)
                # artifacts=...
            )
            if created_task:
                logger.info(f"Successfully created task {created_task.id} for BidCardAgent.")
            else:
                logger.error(f"Failed to create task for BidCardAgent for project {project_id}.")
                # TODO: Handle failure (e.g., retry, mark project status as needing attention)

        except Exception as e:
            logger.error(f"Error calling A2A client to create BidCardAgent task: {e}", exc_info=True)
            # TODO: Handle failure


    async def handle_message(self, message: Message) -> None:
        """
        Handles incoming messages during the project creation flow (if using chat mode).
        """
        logger.info(f"HomeownerAgent received message: {message.id} for task {message.task_id}")
        # TODO: Integrate this with the active conversational flow (e.g., ADK LLMFlow)
        # The flow itself would likely handle incoming messages to advance the conversation state.
        print(f"TODO: Implement message handling logic for task {message.task_id}")


    def get_agent_info(self) -> A2aAgentInfo:
        """Returns the configuration/details of this agent."""
        return self.agent_info

# --- Agent Instantiation ---
# This might live elsewhere (e.g., in the main server startup, requiring dependency injection)
# homeowner_agent_instance = HomeownerAgent(supabase_client=...)
