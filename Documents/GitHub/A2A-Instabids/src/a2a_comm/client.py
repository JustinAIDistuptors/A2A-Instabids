"""
A2A Protocol Client Implementation.

Provides functions to interact with A2A compliant agent endpoints.
Based on patterns in knowledge-bases/A2A/samples/python/common/client/
"""

import httpx
from typing import Optional, List, Union  # Added Union
import logging
import uuid

# Assuming core types are defined in a sibling directory
# Adjust import path as necessary based on final project structure
from ..a2a_types.core import (
    Agent,
    Task,
    Message,
    Artifact,
    AgentId,
    TaskId,
    CreateTaskRequest,
    CreateTaskResponse,
    CreateMessageRequest,
    CreateMessageResponse,
    # Import other request/response types as needed
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Consider making the client configurable (e.g., timeout, base URLs)
# For now, using default httpx settings


async def _make_request(
    method: str, url: str, json_data: Optional[dict] = None, expected_status: int = 200
) -> dict:
    """Helper function to make async HTTP requests."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(method, url, json=json_data)
            response.raise_for_status()  # Raise HTTPStatusError for bad responses (4xx or 5xx)
            if response.status_code != expected_status:
                logger.warning(
                    f"Expected status {expected_status} but got {response.status_code} from {url}"
                )
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            )
            # Re-raise or handle specific errors as needed
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            # Re-raise or handle specific errors as needed
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise


async def create_task(
    target_agent: Agent,
    description: str,
    title: Optional[str] = None,
    artifacts: Optional[List[Artifact]] = None,
    metadata: Optional[dict] = None,
    # Assuming the client knows the 'creator' agent ID or it's passed implicitly
    # creator_agent_id: AgentId # This might be needed depending on auth/context
) -> Optional[Task]:
    """Sends a request to create a new task on a target agent."""
    endpoint = (
        f"{str(target_agent.endpoint).rstrip('/')}/tasks"  # Standard RESTful endpoint
    )
    request_data = CreateTaskRequest(
        title=title,
        description=description,
        assignee_agent_id=target_agent.id,  # Assignee is the target
        artifacts=artifacts,
        metadata=metadata,
    )
    try:
        response_json = await _make_request(
            "POST",
            endpoint,
            json_data=request_data.model_dump(exclude_none=True),
            expected_status=201,  # Typically 201 Created for new resources
        )
        response_obj = CreateTaskResponse(**response_json)
        logger.info(f"Task created successfully: {response_obj.task.id}")
        return response_obj.task
    except Exception as e:
        logger.error(f"Failed to create task on agent {target_agent.id}: {e}")
        return None


async def send_message(
    target_agent: Agent,
    task_id: TaskId,
    role: str,  # Use MessageRole literal eventually
    content: Union[str, dict],
    sender_agent_id: AgentId,  # Explicitly require sender ID
    artifacts: Optional[List[ArtifactId]] = None,
    session_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Optional[Message]:
    """Sends a message to a target agent related to a specific task."""
    # Endpoint might be nested under tasks or be top-level depending on API design
    # Assuming /tasks/{task_id}/messages for now
    endpoint = f"{str(target_agent.endpoint).rstrip('/')}/tasks/{task_id}/messages"
    request_data = CreateMessageRequest(
        task_id=task_id,
        session_id=session_id,
        role=role,
        content=content,
        recipient_agent_id=target_agent.id,  # Recipient is the target
        sender_agent_id=sender_agent_id,  # Pass sender explicitly
        artifacts=artifacts,
        metadata=metadata,
    )
    try:
        response_json = await _make_request(
            "POST",
            endpoint,
            json_data=request_data.model_dump(exclude_none=True),
            expected_status=201,
        )
        response_obj = CreateMessageResponse(**response_json)
        logger.info(f"Message sent successfully: {response_obj.message.id}")
        return response_obj.message
    except Exception as e:
        logger.error(
            f"Failed to send message to agent {target_agent.id} for task {task_id}: {e}"
        )
        return None


# --- Add other client functions as needed ---
# async def get_task(target_agent: Agent, task_id: TaskId) -> Optional[Task]: ...
# async def update_task_status(target_agent: Agent, task_id: TaskId, status: TaskStatus) -> Optional[Task]: ...
# async def add_artifact(target_agent: Agent, task_id: TaskId, artifact: Artifact) -> Optional[Artifact]: ...
# async def get_agent_info(target_agent: Agent) -> Optional[Agent]: ...
