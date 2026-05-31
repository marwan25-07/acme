from runner.schemas import AgentContextStore
from agents import RunContextWrapper
import logging 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# determine tool permissions
def validate_tool_permissions(ctx: RunContextWrapper[AgentContextStore]) -> dict:
    user_role = ctx.context.user_role
    
    tool_permissions = {
        user_role.ADMIN: {
            "read_customer": True,
            "create_customer": True,
            "update_customer": True,
            "read_issue": True,
            "create_issue": True,
            "update_issue": True,
            "read_actions": True,
            "create_actions": True,
            "update_actions": True           
        },
    
        user_role.SUPPORT_USER: {
            "read_customer": True,
            "create_customer": False,
            "update_customer": False,
            "read_issue": True,
            "create_issue": False,
            "update_issue": True,
            "read_actions": False,
            "create_actions": False,
            "update_actions": False           
        },

        user_role.SALES_USER: {
            "read_customer": True,
            "create_customer": False,
            "update_customer": False,
            "read_issue": True,
            "create_issue": False,
            "update_issue": False,
            "read_actions": False,
            "create_actions": False,
            "update_actions": False           
        }}
    return tool_permissions.get(user_role, {})

def has_permission(ctx: RunContextWrapper[AgentContextStore], permission_name:str) -> bool:
    permissions = validate_tool_permissions(ctx)
    return permissions.get(permission_name, False)

def permission_checker(permission_name:str):
    def checker(ctx: RunContextWrapper[AgentContextStore], agent=None) -> bool:
        allowed = has_permission(ctx, permission_name)
        return allowed
    return checker