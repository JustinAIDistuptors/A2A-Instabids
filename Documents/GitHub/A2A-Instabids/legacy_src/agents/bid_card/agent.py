"""What?? No, I didn't. Yes, you said, no, I didn't. If I tried this too much stuff on this, that's what you said. So you can try, but But. no eating in my bed or no, you're curious and. No. They're not. You were not pushing anything out of the way. You come over here nicely. Just sat there. Not yours You see this? You see the Mets. Ohh you wanna sleep with me. You must have put it all to the side, broke down. No, I'm not doing that. Leaving all my stuff up here. I need to do some work up here at least you can go to. Keep my upper head. bed. Yeah. That one or that one. Ohh my god. Just leaving in my bed. Well, you're lucky you can watch Daddy all the time. I'm not gonna be on a look at this three. Do it mine. I like it. OK, I'll put that. Tell me not gonna say something now. You're not treating myself much.. So I have the lunch.. I thought I heard. and. yes, OK. my fan. 000 000 ha ha ha ha ha ha. Oh my god. They're trying to scare me. Uh-huh.. I don't like. I said Elijah, don't stop. He didn't hear, here. I don't know what Elijah.'s. Come on.. Sheriff underwear. Yes. No. you're so dirty. Like all more people. are you? That would be good. That would be good if it's all. Everything that you need the dog.. No right. Yeah, yeah. Pencil that works so I say that. and then. That's why you don't wish. You just said that you loved her. You love to being proud of your snake. You shouldn't stand big on. Heart to get in trouble, so you don't like her. Let's go. I bet. No. Then I'll just destroy orders stuff in their creation. I'm helping me to you. I want clean up my toaster. I'm ready. I'm just quiet. talking. No touching.. Calculator doesn't work. Well, I could touch daddy stuff. What are you doing? What are you doing? What are you doing? What are you doing? This is on Daddy's chair. Why did? away.. Be naked. From duty, Elijah, because then. so the spell. the spell. Are you a witch? Nobody.. How to spell how a spell you said spell? What's that? What's that? Spell. Oh. hoodie.. Just joking. Where's the tongue? Over to junior. I saw something. The dagger. The dagger close up knife that's like this big is it?? You go like this and it's like a really little 9th and you hold it like this. Real yeah, daggers. Actually smoke perfectly. I. I. Yeah. Thank you. Thank you guys.. I bet you're going to get.. No, no, no, no. I. Every question of the person. from my momma. What did you tell Mama like that? Headset, head, head, head, head, head, head, head, head, head, head, head, head. All. I. Pehla Pehla Pehla. Can't keep dancing. That's the other thing.. Magazine magazine. two chocolate milk. Don't tell me. Don't take the sleeping. Happy birthday. Don't go on it. It's stupid.. It's time for a time. Let's go. Let's go. I'm about to leave. I'm not looking my ears. Let me. I want to read your birthday, but I'll tell you. Sharp is covered, except for a snap. I want to sneak. Oh, yeah. This is the paper that we were on. Stop. Stop. Stop. Wait. Stop. Let's all fish. where we should go. Yeah. 3. saving. So they put pop in a bag because they're going to be anything. We're taking over. I'm gonna be. Let me ask you a first pop. No, I'm putting in my bag. I'm lying you look at me. Go from my cambies. Both. One tank top brawl. I am getting right. No, no, there's nothing. There's no clothes for you. This one. No. no. The other blue bag. Please stop. You need to stop. What if they stop? or take the blue bat? I.'s. He couldn't get me. OK. Daddy. What? My mom. my, I'm going to be home. There... Tell me a joke.. Yes, the crispy. Like one of the things I'm going to buy another snake. I would do it on your last name here. Goodbye.
Implementation for the Bid Card Agent.

This agent standardizes project requests into structured "Bid Card" artifacts
and stores them in the database.
"""

import logging
from typing import Any, Dict, Optional, List, Tuple
import os
import uuid  # Import uuid
from dotenv import load_dotenv
from supabase import create_client, Client
import json
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
    ArtifactType,
    TaskStatus,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

AGENT_ID: AgentId = "bid-card-agent-001"  # Example ID - Should be configurable

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


class BidCardAgent(AdkAgent):
    """
    InstaBids Agent responsible for creating standardized Bid Card artifacts.
    """

    def __init__(
        self,
        agent_info: Optional[A2aAgentInfo] = None,
        supabase_client: Optional[Client] = None,  # Allow injecting client for testing
    ):
        """Initializes the BidCardAgent."""
        agent_endpoint = os.getenv(
            "BID_CARD_AGENT_ENDPOINT", DEFAULT_ENDPOINTS.get(AGENT_ID)
        )
        self.agent_info = agent_info or A2aAgentInfo(
            id=AGENT_ID,
            name="Bid Card Agent",
            description="Transforms project details into standardized Bid Card artifacts.",
            endpoint=agent_endpoint,
            capabilities=["bid_card_creation"],
        )
        logger.info(f"Initializing BidCardAgent (ID: {self.agent_info.id})")

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
        Handles the task to create a Bid Card artifact for a given project.
        Fetches project details from Supabase and structures the Bid Card data.
        """
        logger.info(f"BidCardAgent received task: {task.id} - '{task.description}'")
        await self._update_task_status(task.id, "IN_PROGRESS")

        if not self.db:
            error_msg = "Supabase client not available. Cannot process."
            logger.error(f"Task {task.id}: {error_msg}")
            await self._update_task_status(task.id, "FAILED", error_message=error_msg)
            return

        # 1. Extract project_id from task metadata
        project_id = task.metadata.get("project_id") if task.metadata else None
        if not project_id:
            error_msg = "Missing 'project_id' in task metadata."
            logger.error(f"Task {task.id}: {error_msg}")
            await self._update_task_status(task.id, "FAILED", error_message=error_msg)
            return

        logger.info(f"Task {task.id}: Processing project {project_id}")

        try:
            # 2. Fetch project details from Supabase
            project_res = (
                await self.db.table("projects")
                .select("*")
                .eq("id", project_id)
                .maybe_single()
                .execute()
            )
            logger.debug(
                f"Task {task.id}: Supabase project fetch response: {project_res}"
            )

            if not project_res.data:
                error_msg = f"Project {project_id} not found in database."
                logger.error(f"Task {task.id}: {error_msg}")
                await self._update_task_status(
                    task.id, "FAILED", error_message=error_msg
                )
                return

            project_data = project_res.data

            # 3. Fetch associated photos
            photo_res = (
                await self.db.table("project_photos")
                .select("storage_path, caption, photo_type")
                .eq("project_id", project_id)
                .execute()
            )
            logger.debug(f"Task {task.id}: Supabase photos fetch response: {photo_res}")
            photo_data = photo_res.data or []

            # 4. Structure the Bid Card data
            bid_card_content = {
                "project_id": project_data.get("id"),
                "title": project_data.get("title"),
                "description": project_data.get("description"),
                "category": project_data.get("category"),
                "location_description": project_data.get("location_description"),
                "project_type": project_data.get("metadata", {}).get("project_type"),
                "timeline": project_data.get("metadata", {}).get("timeline"),
                "allow_group_bidding": project_data.get("metadata", {}).get(
                    "allow_group_bidding"
                ),
                "desired_outcome": project_data.get(
                    "desired_outcome_description"
                ),  # Added
                "current_photos": [  # Separate photo types
                    {"path": p.get("storage_path"), "caption": p.get("caption")}
                    for p in photo_data
                    if p.get("photo_type") == "current"
                ],
                "inspiration_photos": [
                    {"path": p.get("storage_path"), "caption": p.get("caption")}
                    for p in photo_data
                    if p.get("photo_type") == "inspiration"
                ],
                "created_at": str(project_data.get("created_at")),
            }
            bid_card_content = {
                k: v for k, v in bid_card_content.items() if v is not None
            }

            logger.info(
                f"Task {task.id}: Successfully structured Bid Card content for project {project_id}."
            )

            # 5. Create and store A2A Artifact
            artifact_id = await self._create_bid_card_artifact(
                task.id, bid_card_content
            )

            if artifact_id:
                # 6. Update task status to COMPLETED
                task_result = {"bid_card_artifact_id": artifact_id}
                await self._update_task_status(task.id, "COMPLETED", result=task_result)
                logger.info(
                    f"Task {task.id} completed successfully. Bid Card Artifact ID: {artifact_id}"
                )
                # 7. TODO: Optionally trigger MatchingAgent task here
            else:
                error_msg = "Failed to create or store Bid Card artifact."
                logger.error(f"Task {task.id}: {error_msg}")
                await self._update_task_status(
                    task.id, "FAILED", error_message=error_msg
                )

        except Exception as e:
            error_msg = (
                f"Error processing Bid Card creation for project {project_id}: {e}"
            )
            logger.error(f"Task {task.id}: {error_msg}", exc_info=True)
            await self._update_task_status(task.id, "FAILED", error_message=error_msg)

    async def _create_bid_card_artifact(
        self, task_id: TaskId, content: Dict
    ) -> Optional[str]:
        """Creates and stores the Bid Card artifact in the database."""
        if not self.db:
            logger.error("Cannot create artifact: DB client unavailable.")
            return None

        artifact_id = f"art_bidcard_{uuid.uuid4()}"  # Generate unique ID
        logger.info(f"Creating Bid Card artifact {artifact_id} for task {task_id}")

        try:
            artifact_data = {
                "a2a_artifact_id": artifact_id,
                "a2a_task_id": task_id,
                "creator_agent_id": self.agent_info.id,
                "artifact_type": ArtifactType.BID_CARD,  # Use the defined literal
                "content": json.dumps(content),  # Store content as JSON string
                "description": f"Bid Card for project {content.get('project_id')}",
                "created_at": datetime.datetime.utcnow().isoformat(),
                # "uri": None # Could store JSON in GCS/S3 and put URI here if content is large
            }
            artifact_data = {k: v for k, v in artifact_data.items() if v is not None}

            insert_res = (
                await self.db.table("artifacts").insert(artifact_data).execute()
            )

            if insert_res.data:
                logger.info(f"Successfully stored artifact {artifact_id} in DB.")
                return artifact_id
            else:
                error_detail = getattr(insert_res, "error", None) or getattr(
                    insert_res, "message", "Unknown error"
                )
                logger.error(
                    f"Failed to insert artifact {artifact_id} into Supabase. Detail: {error_detail}"
                )
                return None

        except Exception as e:
            logger.error(f"Error storing artifact {artifact_id}: {e}", exc_info=True)
            return None

    async def handle_message(self, message: Message) -> None:
        """Handles incoming messages (if applicable for this agent)."""
        logger.info(
            f"BidCardAgent received message: {message.id} for task {message.task_id}"
        )
        # This agent might not need complex message handling if it only processes tasks.
        print(
            f"TODO: Implement message handling logic if needed for message {message.id}"
        )

    async def _update_task_status(
        self,
        task_id: TaskId,
        status: TaskStatus,
        result: Optional[Dict] = None,
        error_message: Optional[str] = None,
    ):
        """Updates task status in the database."""
        # (Implementation copied - TODO: Centralize this utility)
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
# bid_card_agent_instance = BidCardAgent()
