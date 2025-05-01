"""
Core data types for the A2A (Agent-to-Agent) protocol implementation.

Based on the A2A specification and examples found in:
- knowledge-bases/A2A/specification/json/a2a.json
- knowledge-bases/A2A/samples/python/common/types.py
"""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, HttpUrl
import datetime

# --- Basic Identifiers ---

AgentId = str
TaskId = str
MessageId = str
ArtifactId = str
SessionId = str  # Assuming sessions might be needed later, aligning with ADK concepts

# --- Enums and Literals ---

TaskStatus = Literal[
    "PENDING",
    "IN_PROGRESS",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
]

MessageRole = Literal[
    "USER",  # Typically the initiator of a task or conversation turn
    "AGENT",  # The agent responding or acting
    "SYSTEM",  # System-level messages or instructions
    "TOOL",  # Messages representing tool calls or results
]

ArtifactType = Literal[
    "TEXT",
    "IMAGE",
    "JSON",
    "FILE",  # Generic file type
    "URL",
    "TOOL_CALL",
    "TOOL_RESULT",
    "BID_CARD",  # Custom type for InstaBids
    "PROJECT_DETAILS",  # Custom type for InstaBids
    # Add other relevant types as needed
]

# --- Core A2A Structures ---


class Agent(BaseModel):
    """Represents an agent participating in the A2A protocol."""

    id: AgentId
    name: str
    description: Optional[str] = None
    endpoint: HttpUrl  # The URL where the agent can be reached
    capabilities: Optional[List[str]] = None  # e.g., ['project_creation', 'bidding']
    metadata: Optional[Dict[str, Any]] = None


class Artifact(BaseModel):
    """Represents a piece of data exchanged between agents."""

    id: ArtifactId
    task_id: TaskId
    creator_agent_id: AgentId
    type: ArtifactType
    content: Any  # The actual data (string, dict, list, bytes representation, etc.)
    uri: Optional[HttpUrl] = (
        None  # Optional URI if content is stored elsewhere (e.g., GCS, Supabase Storage)
    )
    description: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class Message(BaseModel):
    """Represents a message within a task conversation."""

    id: MessageId
    task_id: TaskId
    session_id: Optional[SessionId] = None  # Link to a broader session if applicable
    role: MessageRole
    content: Union[
        str, Dict[str, Any]
    ]  # Can be simple text or structured content (e.g., tool calls)
    sender_agent_id: AgentId
    recipient_agent_id: AgentId
    artifacts: Optional[List[ArtifactId]] = (
        None  # IDs of artifacts associated with this message
    )
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class Task(BaseModel):
    """Represents a unit of work assigned by one agent to another."""

    id: TaskId
    title: Optional[str] = None
    description: str
    status: TaskStatus = "PENDING"
    creator_agent_id: AgentId
    assignee_agent_id: AgentId
    parent_task_id: Optional[TaskId] = None  # For sub-tasks
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    artifacts: Optional[List[ArtifactId]] = (
        None  # IDs of artifacts relevant to the task input/output
    )
    messages: Optional[List[MessageId]] = (
        None  # Chronological list of message IDs in the task conversation
    )
    result: Optional[Any] = (
        None  # Final result of the task, could be text or structured data
    )
    metadata: Optional[Dict[str, Any]] = None


# --- Request/Response Models (Example for Task Creation) ---
# These might live in the client/server implementation files later


class CreateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: str
    assignee_agent_id: AgentId
    parent_task_id: Optional[TaskId] = None
    artifacts: Optional[List[Artifact]] = None  # Allow sending initial artifacts
    metadata: Optional[Dict[str, Any]] = None


class CreateTaskResponse(BaseModel):
    task: Task


class CreateMessageRequest(BaseModel):
    task_id: TaskId
    session_id: Optional[SessionId] = None
    role: MessageRole
    content: Union[str, Dict[str, Any]]
    recipient_agent_id: AgentId
    artifacts: Optional[List[ArtifactId]] = None
    metadata: Optional[Dict[str, Any]] = None


class CreateMessageResponse(BaseModel):
    message: Message


# Add other request/response models as needed (e.g., GetTask, UpdateTask, AddArtifact)
