from pydantic import BaseModel
from enum import Enum

class UserRole(str,Enum):
    ADMIN = "admin"
    SUPPORT_USER = "support_user"
    SALES_USER = "sales_user"

class AgentContextStore(BaseModel):
    user_role: UserRole
    router_turns: int = 3