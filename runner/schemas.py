from pydantic import BaseModel
from enum import Enum
from typing import Any, Optional 

class UserRole(str,Enum):
    ADMIN = "admin"
    SUPPORT_USER = "support_user"
    SALES_USER = "sales_user"

class AgentContextStore(BaseModel):
    user_role: UserRole
    user_id: int
    conversation_id: int
    router_turns: int = 3
    trace_id: str

# Trace Event Schema
class TraceEventStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

class TraceEventPayload(BaseModel):
    status: TraceEventStatus
    response: str
    latency_ms: int|float

class TraceEventType(str, Enum):
    TOOL_CALL = "tool_call"
    RESPONSE = "response"
    REQUEST_START = "request_start"

# Tool Call Schema
class IssueStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    RESOLVED = "resolved"
    CLOSED = "closed"

class IssuePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ToolResultStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

class ToolResult(BaseModel):
    status: ToolResultStatus
    message: str
    data: Optional[Any] = None