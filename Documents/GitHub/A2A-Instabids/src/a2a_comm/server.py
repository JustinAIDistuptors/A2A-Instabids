"""
A2A Protocol Server Implementation (using FastAPI).

Provides endpoints for agents to receive A2A requests.
Based on patterns in:
- knowledge-bases/A2A/samples/python/common/server/
- knowledge-bases/adk-python/tests/unittests/fast_api/
"""

from fastapi import FastAPI, HTTPException, status, Body, Path, Depends
from fastapi.security import APIKeyHeader
from typing import Dict, Any
import logging
import uvicorn  # For running the server locally if needed
import datetime
import uuid  # For generating IDs

# Adjust import path as necessary based on final project structure
from ..a2a_types.core import (
    Agent,
    Task,
    Message,
    Artifact,
    AgentId,
    TaskId,
    MessageId,
    ArtifactId,
    CreateTaskRequest,
    CreateTaskResponse,
    CreateMessageRequest,
    CreateMessageResponse,
    TaskStatus,
    MessageRole,
    ArtifactType,
    # Import other request/response types as needed
)

# Adjust import path for client
import os
from dotenv import load_dotenv
from . import client as a2a_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# --- Authentication Setup ---
API_KEY_NAME = "X-API-Key"  # Standard header name for API keys
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)
# Placeholder for valid API keys - load from env or secure config in real app
VALID_API_KEYS = {
    os.getenv("A2A_SERVER_API_KEY", "test-api-key")
}  # Example: Load from env


async def verify_api_key(key: str = Depends(api_key_header)):
    """Dependency to verify the API key provided in the header."""
    if key not in VALID_API_KEYS:
        logger.warning(f"Invalid API Key received: {key}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    logger.debug("API Key verified successfully.")
    return key  # Return key if valid, can be used if needed


app = FastAPI(
    title="A2A Agent Server",
    description="Handles incoming A2A protocol requests for an agent.",
    version="0.1.0",
)

# --- In-memory storage (for demonstration/testing - replace with persistent storage) ---
# This should eventually interact with agent logic and persistence layers (e.g., Supabase)
TASKS_DB: Dict[TaskId, Task] = {}
MESSAGES_DB: Dict[MessageId, Message] = {}
ARTIFACTS_DB: Dict[ArtifactId, Artifact] = {}

# --- Placeholder Agent Info (replace with actual agent loading/configuration) ---
# This server represents ONE agent. Its details should be loaded dynamically.
THIS_AGENT_ID: AgentId = "placeholder-agent-001"
THIS_AGENT_ENDPOINT = "http://localhost:8000"  # Example endpoint

# --- Helper Functions ---


def get_this_agent() -> Agent:
    """Returns the details of the agent this server represents."""
    # In a real scenario, load this from config or a service
    return Agent(
        id=THIS_AGENT_ID,
        name="Placeholder Agent",
        description="A sample agent server.",
        endpoint=THIS_AGENT_ENDPOINT,
        capabilities=["basic_tasking", "basic_messaging"],
    )


# --- API Endpoints ---


@app.get("/", summary="Agent Information", response_model=Agent)
async def get_agent_info():
    """Returns information about the agent served by this endpoint."""
    logger.info("Request received for agent information.")
    return get_this_agent()


@app.post(
    "/tasks",
    summary="Create Task",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateTaskResponse,
    dependencies=[Depends(verify_api_key)],  # Apply authentication
)
async def handle_create_task(
    request: CreateTaskRequest = Body(...),
    # api_key: str = Depends(verify_api_key) # Can get key here if needed
    # In a real app, you'd likely get the creator_agent_id from auth headers/context
):
    """Handles a request to create a new task for this agent."""
    logger.info(f"Received request to create task: {request.title or 'Untitled'}")

    # Basic validation
    if request.assignee_agent_id != THIS_AGENT_ID:
        logger.error(
            f"Task creation request assigned to wrong agent: {request.assignee_agent_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This agent ({THIS_AGENT_ID}) cannot accept tasks assigned to {request.assignee_agent_id}.",
        )

    # --- Placeholder Logic ---
    # 1. Generate Task ID
    task_id = f"task_{uuid.uuid4()}"
    now = datetime.datetime.utcnow()

    # 2. Create Task object
    new_task = Task(
        id=task_id,
        title=request.title,
        description=request.description,
        status="PENDING",
        creator_agent_id="unknown_creator",  # Replace with actual creator ID from auth/context
        assignee_agent_id=THIS_AGENT_ID,
        parent_task_id=request.parent_task_id,
        created_at=now,
        updated_at=now,
        artifacts=[],  # Process incoming artifacts if needed
        messages=[],
        metadata=request.metadata,
    )

    # 3. Store task (in-memory for now)
    TASKS_DB[task_id] = new_task
    logger.info(f"Task {task_id} created and stored (in-memory).")

    # 4. TODO: Trigger actual agent logic to process the task asynchronously

    # 5. Return response
    return CreateTaskResponse(task=new_task)


@app.post(
    "/tasks/{task_id}/messages",
    summary="Send Message",
    status_code=status.HTTP_201_CREATED,
    # Note: Returning a custom dict, so removed response_model=CreateMessageResponse
    # status_code=status.HTTP_202_ACCEPTED, # Use 202 if accepting for async processing
)
async def handle_create_message(
    task_id: TaskId = Path(...),
    request: CreateMessageRequest = Body(...),
    api_key: str = Depends(verify_api_key),  # Apply authentication
    # Creator agent ID should come from request body or auth
):
    """Handles a request to add a message to a task conversation."""
    logger.info(f"Received message for task {task_id} from {request.sender_agent_id}")

    # Basic validation
    if task_id not in TASKS_DB:
        logger.error(f"Message received for non-existent task: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found.",
        )
    if request.recipient_agent_id != THIS_AGENT_ID:
        logger.error(f"Message received for wrong agent: {request.recipient_agent_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This agent ({THIS_AGENT_ID}) cannot accept messages addressed to {request.recipient_agent_id}.",
        )

    # --- Placeholder Logic ---
    # 1. Generate Message ID
    message_id = f"msg_{uuid.uuid4()}"
    now = datetime.datetime.utcnow()

    # 2. Create Message object
    new_message = Message(
        id=message_id,
        task_id=task_id,
        session_id=request.session_id,
        role=request.role,
        content=request.content,
        sender_agent_id=request.sender_agent_id,
        recipient_agent_id=THIS_AGENT_ID,
        artifacts=request.artifacts,
        created_at=now,
        metadata=request.metadata,
    )

    # 3. Store message (in-memory)
    MESSAGES_DB[message_id] = new_message
    # Add message ID to the task's message list (if storing full task object)
    if task_id in TASKS_DB:
        if TASKS_DB[task_id].messages is None:
            TASKS_DB[task_id].messages = []
        TASKS_DB[task_id].messages.append(message_id)
        TASKS_DB[task_id].updated_at = now

    logger.info(f"Message {message_id} for task {task_id} stored (in-memory).")

    # 4. TODO: Trigger agent logic to process the message (e.g., generate response)

    # --- Forward message to Messaging Agent ---
    # Instead of storing locally, route to the MessagingAgent for filtering/handling
    messaging_agent_id = os.getenv("MESSAGING_AGENT_ID", "messaging-agent-001")
    messaging_agent_endpoint = os.getenv(
        "MESSAGING_AGENT_ENDPOINT", "http://localhost:8005"
    )

    if not messaging_agent_endpoint:
        logger.error("Messaging Agent endpoint not configured. Cannot forward message.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Messaging service configuration error.",
        )

    target_agent_info = Agent(
        id=messaging_agent_id,
        name="Messaging Agent",  # Name/desc might not be strictly needed by client
        endpoint=messaging_agent_endpoint,
    )

    # Use the A2A client to send the *original* request data to the Messaging Agent
    # The Messaging Agent will then handle validation, filtering, and actual forwarding
    try:
        # Note: We are sending the *request* object, not the *new_message* object we created
        # The Messaging Agent will create its own Message object upon receipt if needed.
        # We might need a different client function or endpoint on the Messaging Agent
        # that accepts the raw CreateMessageRequest payload.
        # For now, let's assume the Messaging Agent's handle_message can process this,
        # or we adapt the client/MessagingAgent endpoint later.

        # Re-create the message object based on the request for forwarding
        # (Alternatively, the Messaging Agent could have an endpoint accepting CreateMessageRequest)
        forward_message = Message(
            id=f"fwd_{uuid.uuid4()}",  # Indicate it's a forwarded representation if needed
            task_id=task_id,
            session_id=request.session_id,
            role=request.role,
            content=request.content,
            sender_agent_id=request.sender_agent_id,
            recipient_agent_id=request.recipient_agent_id,  # Original intended recipient
            artifacts=request.artifacts,
            created_at=datetime.datetime.utcnow(),  # Timestamp of forwarding attempt
            metadata=request.metadata,
        )

        # We need a way for the Messaging Agent to handle this incoming message.
        # Let's assume the Messaging Agent exposes a generic /messages endpoint
        # or its handle_message function is triggered internally.
        # Direct A2A call simulation:
        # await a2a_client.send_message(...) # This might create a loop if not handled carefully

        # --- Placeholder: Simulate direct call to Messaging Agent logic ---
        # In reality, this server wouldn't directly call another agent's Python method.
        # It would make an HTTP request via a2a_client to the Messaging Agent's endpoint.
        # messaging_agent_instance = get_messaging_agent_instance() # Need a way to get this
        # await messaging_agent_instance.handle_message(forward_message)
        logger.info(
            f"Message for task {task_id} conceptually forwarded to Messaging Agent."
        )
        print(
            f"TODO: Implement actual HTTP forwarding of message {forward_message.id} to Messaging Agent at {messaging_agent_endpoint}"
        )

        # Since the request is forwarded, what should this endpoint return?
        # Option 1: Return 202 Accepted immediately.
        # Option 2: Wait for a response from Messaging Agent (makes it synchronous).
        # Option 1 is generally better for decoupled systems.
        # We still need a response model. Let's return the original request data
        # wrapped in a generic "accepted" response, or just the message ID.

        # Return a simplified response indicating acceptance for processing
        return {"message_id": forward_message.id, "status": "forwarded_for_processing"}
        # Or adjust response model if needed CreateMessageResponse(message=forward_message) might imply it was created *here*

    except Exception as e:
        logger.error(
            f"Error forwarding message for task {task_id} to Messaging Agent: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to forward message to messaging service.",
        )


# --- Add other endpoints as needed ---
# GET /tasks/{task_id}
# PUT /tasks/{task_id}/status
# POST /tasks/{task_id}/artifacts
# GET /tasks/{task_id}/artifacts/{artifact_id}


# --- Optional: Add main block to run server locally ---
if __name__ == "__main__":
    print(f"Starting A2A Agent Server for Agent ID: {THIS_AGENT_ID}")
    print(f"Access API docs at {THIS_AGENT_ENDPOINT}/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)  # Use port 8000 by default
