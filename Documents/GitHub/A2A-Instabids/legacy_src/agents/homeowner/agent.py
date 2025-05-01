"""
Implementation for the Homeowner Agent.

Handles homeowner onboarding, project creation (photo-first optional flow),
competitive quote upload, and bid selection interactions. Orchestrates
calls to utility functions and ADK flows.
"""

import logging
from typing import Any, Dict, Optional, Union, List, Tuple, Callable
import uuid
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json
import asyncio
import datetime # Import datetime

# Google Cloud Vision client library
from google.cloud import vision

# ADK Components
from google.adk.agents import Agent as AdkAgent
from google.adk.flows import LLMFlow, FlowInput, FlowResult # Import necessary ADK types
from google.adk.models import Llm
from google.adk.models.google import Gemini # Import Gemini model
from google.adk.memory import Memory
from google.adk.memory.in_memory import InMemoryMemory # Import default memory

# Local A2A Types and Client
from ...a2a_types.core import Task, Message, Artifact, AgentId, TaskId, MessageId, Agent as A2aAgentInfo, ArtifactType, TaskStatus
from ...a2a_comm import client as a2a_client

# Local utilities and flows
from . import utils as homeowner_utils
from . import flows as homeowner_flows

# Import PersistentMemory
from ...memory.persistent_memory import PersistentMemory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

AGENT_ID: AgentId = "homeowner-agent-001"

# --- Agent Registry (Simple Placeholder - Copied from MessagingAgent for now) ---
# TODO: Centralize agent registry/discovery
AGENT_REGISTRY_JSON = os.getenv("AGENT_REGISTRY", '{}')
try:
    # Expecting format like: {"agent-id": {"name": "...", "endpoint": "...", "user_id": "user-uuid", "role": "homeowner|contractor"}, ...}
    AGENT_REGISTRY: Dict[AgentId, Dict[str, str]] = json.loads(AGENT_REGISTRY_JSON)
    logger.info(f"Loaded agent registry: {list(AGENT_REGISTRY.keys())}")
except json.JSONDecodeError:
    logger.error("Failed to parse AGENT_REGISTRY env var as JSON. Using default fallbacks.")
    AGENT_REGISTRY = {}

DEFAULT_ENDPOINTS = {
    "homeowner-agent-001": "http://localhost:8001",
    "contractor-agent-001": "http://localhost:8003",
    "bid-card-agent-001": "http://localhost:8002",
    "matching-agent-001": "http://localhost:8004",
    "messaging-agent-001": "http://localhost:8005",
    "outreach-agent-001": "http://localhost:8006",
}


class HomeownerAgent(AdkAgent):
    """
    InstaBids Agent responsible for homeowner interactions.
    Manages the project creation process, potentially starting with photos or quotes.
    """

    def __init__(
        self,
        agent_info: Optional[A2aAgentInfo] = None,
        supabase_client: Optional[Client] = None,
        vision_client: Optional[vision.ImageAnnotatorClient] = None,
        ocr_service: Optional[Any] = None,
        llm_service: Optional[Llm] = None,
        memory_service: Optional[Memory] = None, # Allow injecting memory
    ):
        """Initializes the HomeownerAgent."""
        agent_endpoint = os.getenv("HOMEOWNER_AGENT_ENDPOINT", DEFAULT_ENDPOINTS.get(AGENT_ID))
        self.agent_info = agent_info or A2aAgentInfo(
            id=AGENT_ID,
            name="Homeowner Agent",
            description="Assists homeowners with project creation and contractor selection.",
            endpoint=agent_endpoint,
            capabilities=["project_creation", "bid_review", "quote_upload"]
        )
        logger.info(f"Initializing HomeownerAgent (ID: {self.agent_info.id}) at endpoint {self.agent_info.endpoint}")

        # Initialize Supabase client
        self.db: Optional[Client] = None
        if supabase_client:
            self.db = supabase_client
            logger.info("Using injected Supabase client.")
        else:
            supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
            supabase_key: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
            if supabase_url and supabase_key:
                try:
                    self.db = create_client(supabase_url, supabase_key)
                    logger.info("Supabase client initialized from environment variables.")
                except Exception as e:
                    logger.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
            else:
                logger.warning("Supabase env vars not set. Database functionality disabled.")

        # Initialize Vision client
        self.vision_client: Optional[vision.ImageAnnotatorClient] = None
        if vision_client:
            self.vision_client = vision_client
            logger.info("Using injected Vision client.")
        else:
            try:
                # Assumes GOOGLE_APPLICATION_CREDENTIALS env var is set for auth
                self.vision_client = vision.ImageAnnotatorClient()
                logger.info("Google Cloud Vision client initialized.")
            except Exception as e:
                 logger.error(f"Failed to initialize Vision client: {e}. Photo analysis disabled.", exc_info=True)

        # Store other dependencies
        self.ocr_service = ocr_service or self.vision_client # Default OCR to vision client

        # Initialize LLM Service
        self.llm_service: Optional[Llm] = llm_service
        if not self.llm_service:
            try:
                # TODO: Configure model name from env var if needed
                # Assumes ADK handles auth (e.g., via GOOGLE_API_KEY env var or ADC)
                model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
                self.llm_service = Gemini(model_name=model_name)
                logger.info(f"Initialized default ADK Gemini LLM service ({model_name}).")
            except Exception as e:
                 logger.error(f"Failed to initialize default Gemini LLM service: {e}", exc_info=True)
                 # Don't raise error, allow agent to potentially function without LLM for some tasks
                 self.llm_service = None
        else:
             logger.info("Using injected LLM service.")

        if not self.ocr_service:
             logger.warning("OCR service not available. Quote analysis disabled.")

        # Initialize ADK Memory component
        self.memory_service: Optional[Memory] = memory_service
        if not self.memory_service:
             try:
                  # Extract user_id from agent_id if available for persistent memory
                  user_id = None
                  if agent_info and agent_info.id and agent_info.id.startswith("homeowner-agent-"):
                      parts = agent_info.id.split('-')
                      if len(parts) >= 3:
                          user_id = '-'.join(parts[2:])
                          try:
                              # Validate if it looks like a UUID
                              uuid.UUID(user_id)
                              logger.info(f"Extracted user ID from agent ID: {user_id}")
                          except ValueError:
                              logger.warning(f"Agent ID contains invalid UUID format: {agent_info.id}")
                              user_id = None
                              
                  # Use PersistentMemory if we have a user_id and database, otherwise fallback to InMemory
                  if user_id and self.db:
                      self.memory_service = PersistentMemory(self.db, user_id)
                      asyncio.create_task(self.memory_service.load())  # Start loading memory asynchronously
                      logger.info(f"Initialized PersistentMemory for user {user_id}")
                  else:
                      self.memory_service = InMemoryMemory() # Use default in-memory implementation
                      logger.info("Initialized default ADK InMemoryMemory service.")
             except Exception as e:
                  logger.error(f"Failed to initialize memory service: {e}", exc_info=True)
                  self.memory_service = None
        else:
             logger.info("Using injected ADK Memory service.")


        # Build and store the project creation flow
        self.project_creation_flow: Optional[LLMFlow] = None
        self.project_creation_flow_builder: Optional[Callable[[Llm, Optional[Memory]], LLMFlow]]
        self.project_creation_flow_builder = homeowner_flows.build_project_creation_flow

        if callable(self.project_creation_flow_builder) and self.llm_service:
             try:
                  # Pass memory service here when calling the builder
                  self.project_creation_flow = self.project_creation_flow_builder(self.llm_service, self.memory_service)
                  logger.info("Successfully built project creation flow.")
             except Exception as e:
                  logger.error(f"Error building project creation flow: {e}", exc_info=True)
                  self.project_creation_flow = None
        else:
             logger.error("Cannot build project creation flow: Builder function invalid or LLM service missing.")


        # Store active flows (keyed by TaskId, value is the LLMFlow instance state/context if needed)
        # Using a simple dict for now, might need more robust session management
        self._active_flow_sessions: Dict[TaskId, Dict] = {}
        
        # Flag to determine if we're using persistent memory
        self._is_using_persistent_memory = isinstance(self.memory_service, PersistentMemory)


    async def handle_create_task(self, task: Task) -> None:
        """Handles 'create_new_project' task."""
        logger.info(f"HomeownerAgent received task: {task.id} - '{task.description}'")
        await self._store_initial_task(task) # Store task in DB first
        await self._update_task_status(task.id, "IN_PROGRESS")

        initial_input_type = await self._determine_initial_input(task)
        homeowner_id = task.metadata.get("homeowner_user_id") if task.metadata else None
        if not homeowner_id:
             logger.error(f"Task {task.id}: Cannot determine homeowner_id. Using placeholder.")
             homeowner_id = str(uuid.uuid4()) # Critical Placeholder!

        project_context = {"homeowner_id": homeowner_id}
        
        # Load user context from memory if available
        user_context = await self._load_user_context(task)
        project_context.update(user_context)

        # --- Analyze Initial Input ---
        try:
            if initial_input_type == "photo":
                analysis_context = await homeowner_utils.analyze_photo(
                    self.vision_client, task.artifacts or [], project_context
                )
                project_context.update(analysis_context)
            elif initial_input_type == "quote":
                analysis_context = await homeowner_utils.analyze_quote(
                    self.ocr_service, self.llm_service, task.artifacts or []
                )
                project_context.update(analysis_context)
            elif initial_input_type == "describe":
                project_context['description'] = task.description
                
            # Record task creation in memory if using persistent memory
            if self._is_using_persistent_memory and isinstance(self.memory_service, PersistentMemory):
                await self.memory_service.add_interaction("task_creation", {
                    "task_id": task.id,
                    "input_type": initial_input_type,
                    "description": task.description,
                    "created_at": datetime.datetime.utcnow().isoformat()
                })
        except Exception as e:
             logger.error(f"Error during initial analysis for task {task.id}: {e}", exc_info=True)
             await self._update_task_status(task.id, "FAILED", error_message="Initial analysis failed")
             return

        # --- Mode Selection ---
        interaction_mode = "chat" # Placeholder

        # --- Gather Remaining Details ---
        if interaction_mode == "chat":
            await self._initiate_chat_flow(task.id, project_context, task.creator_agent_id)
        else:
            try:
                project_details = await self._gather_details_form(task.id, project_context)
                if project_details:
                    project_details["homeowner_id"] = project_context["homeowner_id"]
                    await self._finalize_project_creation(task.id, project_details)
                else:
                     logger.warning(f"Task {task.id}: Form gathering failed.")
                     await self._update_task_status(task.id, "FAILED", error_message="Form data gathering failed")
            except Exception as e:
                 logger.error(f"Error during form gathering for task {task.id}: {e}", exc_info=True)
                 await self._update_task_status(task.id, "FAILED", error_message="Error during form gathering")


    async def _determine_initial_input(self, task: Task) -> str:
        """Analyzes task to determine starting point."""
        # (Implementation from previous step - kept for brevity)
        logger.debug(f"Task {task.id}: Determining initial input. Artifacts: {task.artifacts}")
        if task.artifacts:
            if any(getattr(a, 'type', None) == ArtifactType.IMAGE for a in task.artifacts): return "photo"
            if any(getattr(a, 'type', None) == ArtifactType.FILE for a in task.artifacts): return "quote"
        if task.description and "upload quote" in task.description.lower(): return "quote"
        return "describe"


    async def _load_user_context(self, task: Task) -> Dict[str, Any]:
        """Load user context from memory if available."""
        user_id = task.metadata.get("user_id") if task.metadata else None
        if not user_id or not self.memory_service or not self._is_using_persistent_memory:
            return {}
            
        context = {}
        
        # Get preferences if memory is PersistentMemory
        if isinstance(self.memory_service, PersistentMemory):
            # Get preferences
            preferences = self.memory_service.get_all_preferences()
            if preferences:
                context["user_preferences"] = preferences
                
            # Get recent projects
            recent_projects = self.memory_service.get_recent_interactions("project_creation", limit=3)
            if recent_projects:
                context["recent_projects"] = recent_projects
                
            # Get communication style preference
            communication_style = self.memory_service.get_preference("communication_style")
            if communication_style:
                context["communication_style"] = communication_style
        
        logger.info(f"Loaded user context for {user_id}: {list(context.keys())}")
        return context


    async def _initiate_chat_flow(self, task_id: TaskId, initial_context: Dict, user_agent_id: AgentId):
        """Builds, stores, and starts the LLMFlow, sending the first prompt."""
        logger.info(f"Task {task_id}: Initiating chat flow with context: {initial_context}")
        if not self.project_creation_flow or not self.llm_service: # Check if flow was built
             logger.error("Cannot start chat flow: Flow instance or LLM service missing.")
             await self._update_task_status(task_id, "FAILED", error_message="Configuration error: Flow/LLM missing")
             return
        if task_id in self._active_flow_sessions:
             logger.warning(f"Task {task_id}: Flow session already active.")
             # TODO: Handle re-entry (e.g., resend last prompt from memory)
             return

        try:
            # Store initial context for this flow session
            self._active_flow_sessions[task_id] = {"flow_state": None, "gathered_data": initial_context}
            logger.info(f"Task {task_id}: Created and stored new flow session.")

            logger.info(f"Task {task_id}: Running initial step of LLMFlow.")
            # Pass initial context and potentially load memory state if resuming
            flow_input = FlowInput(initial_context=initial_context)
            # Use the pre-built flow instance
            result: FlowResult = await self.project_creation_flow.run(flow_input)

            # Update session state
            self._active_flow_sessions[task_id]["flow_state"] = result.state
            self._active_flow_sessions[task_id]["gathered_data"] = result.data

            first_prompt = result.response

            if first_prompt:
                 await self._send_response_message(task_id, user_agent_id, first_prompt)
                 logger.info(f"Task {task_id}: Initial prompt sent, awaiting user message.")
            elif result.is_done:
                 logger.info(f"Flow for task {task_id} completed on initiation.")
                 final_data = result.data or {}
                 final_data["homeowner_id"] = initial_context.get("homeowner_id")
                 await self._finalize_project_creation(task_id, final_data)
                 if task_id in self._active_flow_sessions: del self._active_flow_sessions[task_id] # Cleanup
            else:
                 logger.error(f"Task {task_id}: Flow failed to generate initial prompt and is not done. State: {result.state}")
                 if task_id in self._active_flow_sessions: del self._active_flow_sessions[task_id]
                 await self._update_task_status(task_id, "FAILED", error_message="Flow failed on initiation")

        except Exception as e:
            logger.error(f"Error during chat flow initiation for task {task_id}: {e}", exc_info=True)
            if task_id in self._active_flow_sessions: del self._active_flow_sessions[task_id]
            await self._update_task_status(task_id, "FAILED", error_message=f"Error initiating flow: {e}")


    async def _gather_details_form(self, task_id: TaskId, initial_context: Dict) -> Optional[Dict]:
        """Placeholder for structured/form-based detail gathering."""
        # (Implementation from previous step - kept for brevity)
        logger.info(f"Task {task_id}: Simulating form data gathering with context: {initial_context}")
        gathered_details = initial_context.copy()
        form_step_1_data = {"title": "Form Project Title", "description": "Details entered via form."}
        # ... (rest of simulation) ...
        gathered_details.update(form_step_1_data) # etc.
        if not gathered_details.get("description") or not gathered_details.get("location_description"): return None
        return gathered_details


    async def handle_message(self, message: Message) -> None:
        """Routes incoming user messages to the appropriate active LLMFlow instance."""
        logger.info(f"HomeownerAgent received message: {message.id} for task {message.task_id}")
        task_id = message.task_id
        flow_session = self._active_flow_sessions.get(task_id)

        if flow_session and self.project_creation_flow:
            logger.info(f"Routing message {message.id} content to active flow for task {task_id}")
            try:
                # Prepare input for the next turn, including current state from session
                flow_input = FlowInput(
                    user_message=str(message.content),
                    current_state=flow_session.get("flow_state"),
                    gathered_data=flow_session.get("gathered_data")
                )
                # Execute the next turn of the flow
                result: FlowResult = await self.project_creation_flow.run(flow_input)

                # Update session state
                flow_session["flow_state"] = result.state
                flow_session["gathered_data"] = result.data

                next_prompt = result.response
                flow_is_done = result.is_done
                final_data = result.data if flow_is_done else None
                
                # Record message interaction if using persistent memory
                if self._is_using_persistent_memory and isinstance(self.memory_service, PersistentMemory):
                    user_message_data = {
                        "task_id": task_id,
                        "message_id": message.id,
                        "content": str(message.content),
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    }
                    await self.memory_service.add_interaction("user_message", user_message_data)

                if flow_is_done:
                    logger.info(f"Flow for task {task_id} completed.")
                    if final_data and "homeowner_id" not in final_data:
                         logger.warning(f"Task {task_id}: homeowner_id missing from final flow data. Attempting recovery.")
                         final_data["homeowner_id"] = flow_session.get("gathered_data", {}).get("homeowner_id") # Get from session start
                    await self._finalize_project_creation(task_id, final_data)
                    if task_id in self._active_flow_sessions: del self._active_flow_sessions[task_id] # Cleanup
                elif next_prompt:
                    logger.info(f"Flow for task {task_id} generated next prompt.")
                    await self._send_response_message(task_id, message.sender_agent_id, next_prompt)
                    
                    # Record assistant response if using persistent memory
                    if self._is_using_persistent_memory and isinstance(self.memory_service, PersistentMemory):
                        assistant_message_data = {
                            "task_id": task_id,
                            "content": str(next_prompt),
                            "timestamp": datetime.datetime.utcnow().isoformat()
                        }
                        await self.memory_service.add_interaction("assistant_message", assistant_message_data)
                else:
                    logger.error(f"Flow for task {task_id} is stuck or failed internally without finishing. State: {result.state}")
                    if task_id in self._active_flow_sessions: del self._active_flow_sessions[task_id]
                    await self._update_task_status(task_id, "FAILED", error_message="Flow stalled unexpectedly")

            except Exception as e:
                logger.error(f"Error processing message {message.id} in flow for task {task_id}: {e}", exc_info=True)
                if task_id in self._active_flow_sessions: del self._active_flow_sessions[task_id]
                await self._update_task_status(task_id, "FAILED", error_message=f"Error processing message: {e}")
        else:
            logger.warning(f"No active LLMFlow session found for task {task_id} to handle message {message.id}")


    async def _finalize_project_creation(self, task_id: TaskId, final_data: Optional[Dict]):
        """Saves project and triggers next steps after flow completion."""
        if final_data:
             if "homeowner_id" not in final_data or not final_data["homeowner_id"]:
                  logger.error(f"Task {task_id}: Cannot finalize project, homeowner_id is missing in final data.")
                  await self._update_task_status(task_id, "FAILED", error_message="Internal error: Missing homeowner ID")
                  return

             project_id = await homeowner_utils.save_project_to_db(self.db, final_data)
             if project_id:
                  logger.info(f"Task {task_id}: Project saved from flow completion with ID {project_id}.")
                  
                  # Record project creation in persistent memory
                  if self._is_using_persistent_memory and isinstance(self.memory_service, PersistentMemory):
                      project_data = {
                          "project_id": project_id,
                          "title": final_data.get("title"),
                          "category": final_data.get("category"),
                          "project_type": final_data.get("project_type"),
                          "created_at": datetime.datetime.utcnow().isoformat()
                      }
                      await self.memory_service.add_interaction("project_created", project_data)
                      
                      # Update preferences based on project
                      if "project_type" in final_data:
                          await self.memory_service._update_preference(
                              "preferred_project_types", 
                              final_data["project_type"],
                              "project_creation"
                          )
                  
                  # Trigger bid card creation
                  await homeowner_utils.trigger_bid_card_creation(
                       self.agent_info.id, task_id, project_id, final_data
                  )
                  await self._update_task_status(task_id, "COMPLETED", result={"project_id": project_id})
             else:
                  logger.error(f"Task {task_id}: Failed to save project after flow completion.")
                  await self._update_task_status(task_id, "FAILED", error_message="Database save failed")
        else:
             logger.warning(f"Task {task_id}: Flow completed but no final data provided.")
             await self._update_task_status(task_id, "FAILED", error_message="Flow completed without data")


    async def _send_response_message(self, task_id: TaskId, recipient_agent_id: AgentId, prompt_content: Union[str, Dict]):
        """Sends the agent's response/next prompt back to the user via A2A."""
        # Handle dict prompts (with quick replies) vs simple strings
        if isinstance(prompt_content, dict):
             prompt_text = prompt_content.get("text", "...")
             # TODO: Handle quick_replies - need to decide how to pass these via A2A Message
             # Option 1: Add to metadata
             # Option 2: Define a structured content type for messages
             metadata = {"quick_replies": prompt_content.get("quick_replies")}
        else:
             prompt_text = str(prompt_content)
             metadata = None

        logger.info(f"Sending prompt for task {task_id} to {recipient_agent_id}: {prompt_text}")
        target_agent_info = await self._get_recipient_agent_info(recipient_agent_id)
        if target_agent_info:
            try:
                await a2a_client.send_message(
                    target_agent=target_agent_info,
                    task_id=task_id,
                    role="AGENT",
                    content=prompt_text, # Send only text for now
                    sender_agent_id=self.agent_info.id,
                    metadata=metadata # Pass quick replies in metadata
                )
                logger.info(f"Successfully sent response message for task {task_id}.")
            except Exception as e:
                 logger.error(f"Failed to send response message for task {task_id}: {e}", exc_info=True)
        else:
             logger.error(f"Cannot send response message for task {task_id}: Recipient agent info not found for {recipient_agent_id}.")


    async def _get_recipient_agent_info(self, agent_id: AgentId) -> Optional[A2aAgentInfo]:
        """Retrieves agent details (especially endpoint) for forwarding."""
        # (Implementation from previous step - kept for brevity)
        logger.debug(f"Looking up agent info for {agent_id}")
        agent_details = AGENT_REGISTRY.get(agent_id)
        if agent_details and agent_details.get("endpoint"):
            return A2aAgentInfo(id=agent_id, name=agent_details.get("name", agent_id), endpoint=agent_details["endpoint"])
        else:
            default_endpoint = DEFAULT_ENDPOINTS.get(agent_id)
            if default_endpoint: return A2aAgentInfo(id=agent_id, name=f"Agent {agent_id} (Default)", endpoint=default_endpoint)
            else:
                 env_var_name = f"{agent_id.upper().replace('-', '_')}_ENDPOINT"
                 endpoint_from_env = os.getenv(env_var_name)
                 if endpoint_from_env: return A2aAgentInfo(id=agent_id, name=f"Agent {agent_id} (Env)", endpoint=endpoint_from_env)
                 else:
                      logger.error(f"Could not determine endpoint for agent {agent_id}")
                      return None

    async def _store_initial_task(self, task: Task):
        """Stores the initial task details in the database."""
        if not self.db:
            logger.error(f"Cannot store initial task {task.id}: DB client not available.")
            return
        logger.info(f"Storing initial task {task.id} in database.")
        try:
            task_data = {
                "a2a_task_id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "creator_agent_id": task.creator_agent_id,
                "assignee_agent_id": task.assignee_agent_id,
                "parent_task_id": task.parent_task_id,
                "metadata": task.metadata if isinstance(task.metadata, dict) else None,
                "created_at": task.created_at.isoformat(),
                "updated_at": datetime.datetime.utcnow().isoformat()
            }
            task_data = {k: v for k, v in task_data.items() if v is not None}

            await self.db.table("tasks").insert(task_data).execute()
            logger.info(f"Successfully stored initial task {task.id}.")
        except Exception as e:
            # Check for unique violation error (specific code might vary by DB)
            if hasattr(e, 'code') and e.code == '23505': # Postgres unique violation code
                 logger.warning(f"Task {task.id} already exists in DB. Skipping initial store.")
            elif hasattr(e, 'details') and "duplicate key value violates unique constraint" in str(e.details).lower():
                 logger.warning(f"Task {task.id} already exists in DB (detected via details). Skipping initial store.")
            else:
                 logger.error(f"Failed to store initial task {task.id}: {e}", exc_info=True)


    async def _update_task_status(self, task_id: TaskId, status: TaskStatus, result: Optional[Dict] = None, error_message: Optional[str] = None):
        """Updates task status in the database."""
        log_message = f"Task {task_id}: Status changed to {status}."
        if result: log_message += f" Result: {result}"
        if error_message: log_message += f" Error: {error_message}"
        logger.info(log_message)

        if not self.db:
            logger.error(f"Cannot update task {task_id} status: DB client not available.")
            return

        update_data = {
            "status": status,
            "updated_at": datetime.datetime.utcnow().isoformat()
        }
        if status in ["COMPLETED", "FAILED", "CANCELLED"]:
            update_data["completed_at"] = update_data["updated_at"]
        if result:
            try:
                update_data["result"] = json.dumps(result)
            except TypeError:
                logger.error(f"Task {task_id}: Result dictionary is not JSON serializable.")
                update_data["result"] = json.dumps({"error": "Result not serializable"})
        if error_message:
            update_data["error_message"] = error_message

        try:
            await self.db.table("tasks").update(update_data).
