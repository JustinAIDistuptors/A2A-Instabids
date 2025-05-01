"""
Implementation for the Outreach Agent.

Handles sending notifications or initiating contact via external channels
like email, SMS, or potentially submitting web forms based on tasks.
"""

import logging
from typing import Any, Dict, Optional, List
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json
import asyncio
import datetime

# Assuming ADK and A2A types are accessible
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

# Import A2A client if needed (e.g., to report back task status)
# from ...a2a_comm import client as a2a_client

# TODO: Import actual clients for email (e.g., smtplib, sendgrid), SMS (e.g., twilio), web scraping/forms (e.g., requests, playwright)

logger = logging.getLogger(__name__)
load_dotenv()

AGENT_ID: AgentId = "outreach-agent-001"  # Example ID - Should be configurable

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


class OutreachAgent(AdkAgent):
    """
    InstaBids Agent responsible for external outreach (email, SMS, web forms).
    """

    def __init__(
        self,
        agent_info: Optional[A2aAgentInfo] = None,
        supabase_client: Optional[
            Client
        ] = None,  # For fetching contact details if needed
        # TODO: Inject clients for email, SMS, web form services
        # email_client: Optional[Any] = None,
        # sms_client: Optional[Any] = None,
        # web_client: Optional[Any] = None,
    ):
        """Initializes the OutreachAgent."""
        agent_endpoint = os.getenv(
            "OUTREACH_AGENT_ENDPOINT", DEFAULT_ENDPOINTS.get(AGENT_ID)
        )
        self.agent_info = agent_info or A2aAgentInfo(
            id=AGENT_ID,
            name="Outreach Agent",
            description="Handles external communications like email and SMS.",
            endpoint=agent_endpoint,
            capabilities=["send_email", "send_sms", "submit_web_form"],
        )
        logger.info(f"Initializing OutreachAgent (ID: {self.agent_info.id})")

        # Initialize Supabase client if not injected (might need to fetch contact info)
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

        # TODO: Store injected service clients
        # self.email_client = email_client
        # self.sms_client = sms_client
        # self.web_client = web_client

    async def handle_create_task(self, task: Task) -> None:
        """Handles tasks like 'send_email', 'send_sms', 'submit_form'."""
        logger.info(f"OutreachAgent received task: {task.id} - '{task.description}'")
        await self._update_task_status(task.id, "IN_PROGRESS")

        action = task.metadata.get("action") if task.metadata else None
        params = task.metadata.get("params") if task.metadata else {}
        success = False
        result_data = None
        error_msg = None

        try:
            if action == "send_email":
                success, result_data = await self.send_email(**params)
            elif action == "send_sms":
                success, result_data = await self.send_sms(**params)
            elif action == "submit_web_form":
                success, result_data = await self.submit_web_form(**params)
            else:
                error_msg = f"Unsupported action '{action}' for OutreachAgent."
                logger.error(f"Task {task.id}: {error_msg}")

            if success:
                await self._update_task_status(task.id, "COMPLETED", result=result_data)
            else:
                # Use error message from function if provided, else use generic
                error_msg = (
                    result_data.get("error", error_msg or "Outreach action failed.")
                    if isinstance(result_data, dict)
                    else error_msg
                )
                await self._update_task_status(
                    task.id, "FAILED", error_message=error_msg
                )

        except Exception as e:
            error_msg = f"Error executing outreach action '{action}': {e}"
            logger.error(f"Task {task.id}: {error_msg}", exc_info=True)
            await self._update_task_status(task.id, "FAILED", error_message=error_msg)

    async def send_email(
        self, to_address: str, subject: str, body: str, **kwargs
    ) -> Tuple[bool, Optional[Dict]]:
        """Placeholder: Simulates sending an email."""
        logger.info(
            f"Simulating sending email to {to_address} with subject '{subject}'"
        )
        # TODO: Implement actual email sending logic using self.email_client
        print(f"--- EMAIL ---")
        print(f"To: {to_address}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        print(f"-------------")
        await asyncio.sleep(0.5)  # Simulate network delay
        # Return success status and optional result data (e.g., message ID from provider)
        return True, {"status": "simulated_email_sent"}

    async def send_sms(
        self, to_number: str, message_body: str, **kwargs
    ) -> Tuple[bool, Optional[Dict]]:
        """Placeholder: Simulates sending an SMS."""
        logger.info(f"Simulating sending SMS to {to_number}: '{message_body[:50]}...'")
        # TODO: Implement actual SMS sending logic using self.sms_client (e.g., Twilio)
        print(f"--- SMS ---")
        print(f"To: {to_number}")
        print(f"Body: {message_body}")
        print(f"---------")
        await asyncio.sleep(0.5)  # Simulate network delay
        return True, {"status": "simulated_sms_sent"}

    async def submit_web_form(
        self, form_url: str, form_data: Dict[str, str], **kwargs
    ) -> Tuple[bool, Optional[Dict]]:
        """Placeholder: Simulates submitting data to a web form."""
        logger.info(f"Simulating submitting form to {form_url} with data: {form_data}")
        # TODO: Implement actual web form submission logic using self.web_client (e.g., requests, playwright)
        # This is complex and needs careful handling of sessions, CSRF tokens, etc.
        print(f"--- WEB FORM ---")
        print(f"URL: {form_url}")
        print(f"Data: {form_data}")
        print(f"--------------")
        await asyncio.sleep(1)  # Simulate network delay and processing
        return True, {"status": "simulated_form_submitted"}

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
# outreach_agent_instance = OutreachAgent()
