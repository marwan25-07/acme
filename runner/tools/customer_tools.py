from pydantic import BaseModel, Field
from agents import function_tool, RunContextWrapper
from runner.schemas import AgentContextStore
from enum import Enum
from typing import Any, Optional
from db.customer_repository import (
    add_customer,
    get_customer,
    get_customer_by_id,
    list_customers,
    update_customer,
    add_issue,
    get_issue,
    get_customer_issues,
    update_issue,
    add_issue_update,
    get_issue_updates,
    update_issue_update,
    add_next_action,
    get_next_actions,
    update_next_action,
    get_customer_overview,
)
from runner.tools.tool_permissions import permission_checker, validate_tool_permissions
import logging 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def success(message: str, data: Any = None) -> dict:
    return ToolResult(
        status=ToolResultStatus.SUCCESS,
        message=message,
        data=data,
    ).model_dump()


def error(message: str, data: Any = None) -> dict:
    return ToolResult(
        status=ToolResultStatus.ERROR,
        message=message,
        data=data,
    ).model_dump()  

def clean_title(value: str|None) -> str|None:
    if value is None:
        return None
    else:
        value = value.strip().title()
        return value


# create customer
class CreateCustomerInput(BaseModel):
    name: str = Field(..., description="The company name.")
    industry: Optional[str] = Field(None, description="The customer's industry.")
    account_manager: Optional[str] = Field(None, description="The internal account manager responsible for this customer.")

@function_tool(
        description_override= "Create a new customer, or update the existing customer if the name already exists.",
        strict_mode = True,
        is_enabled=permission_checker("create_customer")
)
def create_customer_tool(args: CreateCustomerInput) -> dict:
    logger.info("entering customer_tool: create_customer_tool")
    try:
        customer_id = add_customer(
            name=clean_title(args.name),
            industry=clean_title(args.industry),
            account_manager=clean_title(args.account_manager),
        )

        customer = get_customer_by_id(customer_id)

        return success(
            message="Customer created or updated successfully.",
            data=customer,
        )

    except Exception as exc:
        logger.error(f"customer_tool: create_customer_tool. error: {exc}")
        return error(f"Failed to create customer: {str(exc)}")
    
# find customer
class FindCustomerInput(BaseModel):
    customer_name: str = Field(..., description="The exact customer/company name to search for.")

@function_tool(
        description_override= "Finds Customer information by providing customer name as input",
        strict_mode = True,
        is_enabled=permission_checker("read_customer")
)
def find_customer_tool(args: FindCustomerInput) -> dict:
    logger.info("entering customer_tool: find_customer_tool")
    try:
        customer = get_customer(clean_title(args.customer_name))

        if customer is None:
            return error(
                message="Customer not found.",
                data={"customer_name": args.customer_name},
            )

        return success(
            message="Customer found.",
            data=customer,
        )

    except Exception as exc:
        logger.error(f"customer_tool: find_customer_tool. error: {exc}")
        return error(f"Failed to find customer: {str(exc)}")
    
# list customer
class ListCustomersInput(BaseModel):
    search: Optional[str] = Field(
        None,
        description="Optional search term for customer name, industry, or account manager.",
    )

@function_tool(
        #description_override= "List all customers, optionally filtered by a search term.",
        #strict_mode = True,
        is_enabled= True #permission_checker("read_customer")
)
def list_customers_tool() -> dict:
    logger.info(f"entering customer_tool: list_customers_tool")
    try:
        customers = list_customers(search=None)

        return success(
            message=f"Found {len(customers)} customer(s).",
            data=customers,
        )

    except Exception as exc:
        logger.error(f"customer_tool: list_customers_tool. error: {exc}")
        return error(f"Failed to list customers: {str(exc)}")
    
# update customer
class UpdateCustomerInput(BaseModel):
    customer_id: int = Field(..., description="The ID of the customer to update.")
    name: Optional[str] = Field(None, description="Updated customer name.")
    industry: Optional[str] = Field(None, description="Updated industry.")
    account_manager: Optional[str] = Field(None, description="Updated account manager.")

@function_tool(
        description_override= "Update customer details. Only supplied fields are changed.",
        strict_mode = True,
        is_enabled=permission_checker("update_customer")
)
def update_customer_tool(args: UpdateCustomerInput) -> dict:
    logger.info(f"entering customer_tool: update_customer_tool")
    try:
        updated_customer = update_customer(
            customer_id=args.customer_id,
            name=clean_title(args.name),
            industry=clean_title(args.industry),
            account_manager=clean_title(args.account_manager),
        )

        if updated_customer is None:
            return error(
                message="Customer not found or could not be updated.",
                data={"customer_id": args.customer_id},
            )

        return success(
            message="Customer updated successfully.",
            data=updated_customer,
        )

    except Exception as exc:
        logger.error(f"customer_tool: update_customer_tool. error: {exc}")
        return error(f"Failed to update customer: {str(exc)}")

# create issue
class CreateIssueInput(BaseModel):
    customer_id: int = Field(..., description="The ID of the customer this issue belongs to.")
    title: str = Field(..., description="Human-readable issue title.")
    status: IssueStatus = Field(IssueStatus.OPEN, description="Current issue status.")
    priority: Optional[IssuePriority] = Field(None, description="Issue priority.")

@function_tool(
        description_override= "Create a new issue linked to a customer. If the issue already exists, update it.",
        strict_mode = True,
        is_enabled=permission_checker("create_issue")
)
def create_issue_tool(args: CreateIssueInput) -> dict:
    logger.info(f"entering customer_tool: create_issue_tool")
    try:
        issue_id = add_issue(
            customer_id=args.customer_id,
            title=args.title,
            status=args.status.value,
            priority=args.priority.value if args.priority else None,
        )

        issue = get_issue(issue_id)

        return success(
            message="Issue created or updated successfully.",
            data=issue,
        )

    except Exception as exc:
        logger.error(f"customer_tool: create_issue_tool. error: {exc}")
        return error(f"Failed to create issue: {str(exc)}")
    
# get issue
class GetIssueInput(BaseModel):
    issue_id: int = Field(..., description="The issue ID.")

@function_tool(
        description_override= "Get a single issue, by passing issue id as input",
        strict_mode = True,
        is_enabled=permission_checker("read_issue")
)
def get_issue_tool(args: GetIssueInput) -> dict:
    logger.info(f"entering customer_tool: get_issue_tool")
    try:
        issue = get_issue(args.issue_id)

        if issue is None:
            return error(
                message="Issue not found.",
                data={"issue_id": args.issue_id},
            )

        return success(
            message="Issue found.",
            data=issue,
        )

    except Exception as exc:
        logger.error(f"customer_tool: get_issue_tool. error: {exc}")
        return error(f"Failed to get issue: {str(exc)}")
    
# list customer issues
class GetCustomerIssuesInput(BaseModel):
    customer_id: int = Field(..., description="The customer ID.")

@function_tool(
        description_override= "Gets all issues relating to a single customer by passing customer id as input",
        strict_mode = True,
        is_enabled=permission_checker("read_issue")
)
def get_customer_issues_tool(args: GetCustomerIssuesInput) -> dict:
    logger.info(f"entering customer_tool: get_customer_issues_tool")
    try:
        issues = get_customer_issues(args.customer_id)

        return success(
            message=f"Found {len(issues)} issue(s).",
            data=issues,
        )

    except Exception as exc:
        logger.error(f"customer_tool: get_customer_issues_tool. error: {exc}")
        return error(f"Failed to get customer issues: {str(exc)}")
    
# update issues
class UpdateIssueInput(BaseModel):
    issue_id: int = Field(..., description="The issue ID to update.")
    title: Optional[str] = Field(None, description="Updated issue title.")
    status: Optional[IssueStatus] = Field(None, description="Updated issue status.")
    priority: Optional[IssuePriority] = Field(None, description="Updated issue priority.")

@function_tool(
        description_override= "Update an issue. Only supplied fields are changed",
        strict_mode = True,
        is_enabled=permission_checker("update_issue")
)
def update_issue_tool(args: UpdateIssueInput) -> dict:
    logger.info(f"entering customer_tool: update_issue_tool.")
    try:
        updated_issue = update_issue(
            issue_id=args.issue_id,
            title=clean_title(args.title),
            status=args.status.value if args.status else None,
            priority=args.priority.value if args.priority else None,
        )

        if updated_issue is None:
            return error(
                message="Issue not found or could not be updated.",
                data={"issue_id": args.issue_id},
            )

        return success(
            message="Issue updated successfully.",
            data=updated_issue,
        )

    except Exception as exc:
        logger.error(f"customer_tool:update_issue_tool. error: {exc}")
        return error(f"Failed to update issue: {str(exc)}")

# add issue note
class AddIssueNoteInput(BaseModel):
    issue_id: int = Field(..., description="The issue ID this note belongs to.")
    note_text: str = Field(..., description="The note/update text to add to the issue.")

@function_tool(
        description_override= "Add a note, by passing as inputs: issue id, and note.",
        strict_mode = True,
        is_enabled=permission_checker("create_issue")
)
def add_issue_note_tool(args: AddIssueNoteInput) -> dict:
    logger.info(f"entering customer_tool:add_issue_note_tool")
    try:
        update_id = add_issue_update(
            issue_id=args.issue_id,
            update_text=args.note_text,
        )

        updates = get_issue_updates(args.issue_id)

        return success(
            message="Issue note added successfully.",
            data={
                "update_id": update_id,
                "issue_id": args.issue_id,
                "all_updates": updates,
            },
        )

    except Exception as exc:
        logger.error(f"customer_tool:add_issue_note_tool. error: {exc}")
        return error(f"Failed to add issue note: {str(exc)}")

# get issue notes
class GetIssueNotesInput(BaseModel):
    issue_id: int = Field(..., description="The issue ID.")

@function_tool(
        description_override= "Get all notes for a single issue by passing as input: issue id.",
        strict_mode = True,
        is_enabled=permission_checker("read_issue")
)
def get_issue_notes_tool(args: GetIssueNotesInput) -> dict:
    logger.info(f"entering customer_tool: get_issue_notes_tool")
    try:
        updates = get_issue_updates(args.issue_id)

        return success(
            message=f"Found {len(updates)} note(s).",
            data=updates,
        )

    except Exception as exc:
        logger.error(f"customer_tool: get_issue_notes_tool. error: {exc}")
        return error(f"Failed to get issue notes: {str(exc)}")

# update issue note   
class UpdateIssueNoteInput(BaseModel):
    update_id: int = Field(..., description="The ID of the note/update to edit.")
    note_text: str = Field(..., description="The new note text.")

@function_tool(
        description_override= "Updates an existing issue note, by passing as input: update id, note text.",
        strict_mode = True,
        is_enabled=permission_checker("update_issue")
)
def update_issue_note_tool(args: UpdateIssueNoteInput) -> dict:
    logger.info(f"entering customer_tool: update_issue_note_tool")
    try:
        updated_note = update_issue_update(
            update_id=args.update_id,
            update_text=args.note_text,
        )

        if updated_note is None:
            return error(
                message="Issue note not found or could not be updated.",
                data={"update_id": args.update_id},
            )

        return success(
            message="Issue note updated successfully.",
            data=updated_note,
        )

    except Exception as exc:
        logger.error(f"customer_tool: update_issue_note_tool. error: {exc}")
        return error(f"Failed to update issue note: {str(exc)}")
    
# add next action 
class AddNextActionInput(BaseModel):
    issue_id: int = Field(..., description="The issue ID this next action belongs to.")
    action_text: str = Field(..., description="The next action to add.")
    created_by: Optional[str] = Field(None, description="The person who created the action.")

@function_tool(
        description_override= "Add a next action for a single issue, by passing as input: issue_id, action_text, created_by",
        strict_mode = True,
        is_enabled=permission_checker("create_actions")
)
def add_next_action_tool(args: AddNextActionInput) -> dict:
    logger.info(f"entering customer_tool: add_next_action_tool")
    try:
        action_id = add_next_action(
            issue_id=args.issue_id,
            action_text=args.action_text,
            created_by=clean_title(args.created_by),
        )

        actions = add_next_action(args.issue_id)

        return success(
            message="Next action added successfully.",
            data={
                "action_id": action_id,
                "issue_id": args.issue_id,
                "all_next_actions": actions,
            },
        )

    except Exception as exc:
        logger.error(f"customer_tool: add_next_action_tool. error: {exc}")
        return error(f"Failed to add next action: {str(exc)}")
    
# get next actions
class GetNextActionsInput(BaseModel):
    issue_id: int = Field(..., description="The issue ID.")

@function_tool(
        description_override= "Gets all next actions for a single issue by passing as input: issue_id",
        strict_mode = True,
        is_enabled=permission_checker("read_actions")
)
def get_next_actions_tool(args: GetNextActionsInput) -> dict:
    logger.info(f"entering customer_tool: get_next_actions_tool")
    try:
        actions = get_next_actions(args.issue_id)

        return success(
            message=f"Found {len(actions)} next action(s).",
            data=actions,
        )

    except Exception as exc:
        logger.error(f"customer_tool: get_next_actions_tool. error: {exc}")
        return error(f"Failed to get next actions: {str(exc)}")
    
# update next actions 
class UpdateNextActionInput(BaseModel):
    action_id: int = Field(..., description="The next action ID to update.")
    action_text: Optional[str] = Field(None, description="Updated next action text.")
    created_by: Optional[str] = Field(None, description="Updated creator/owner.")

@function_tool(
        description_override= "Update a next action. Only supplied fields are changed.",
        strict_mode = True,
        is_enabled=permission_checker("update_actions")
)
def update_next_action_tool(args: UpdateNextActionInput) -> dict:
    logger.info(f"entering customer_tool: update_next_action_tool")
    try:
        updated_action = update_next_action(
            action_id=args.action_id,
            action_text=args.action_text,
            created_by=clean_title(args.created_by),
        )

        if updated_action is None:
            return error(
                message="Next action not found or could not be updated.",
                data={"action_id": args.action_id},
            )

        return success(
            message="Next action updated successfully.",
            data=updated_action,
        )

    except Exception as exc:
        logger.error(f"customer_tool: update_next_action_tool. error: {exc}")
        return error(f"Failed to update next action: {str(exc)}")
    
# get customer overview
class GetCustomerOverviewInput(BaseModel):
    customer_name: str = Field(..., description="The exact company name.")

@function_tool(
        description_override= "Get a customer, their issues, issue notes and next actions. This is the main-context loading tool for the agent.",
        strict_mode = True,
        is_enabled=permission_checker("read_customer")
)
def get_customer_overview_tool(args:GetCustomerOverviewInput):
    logger.info(f"entering customer_tool: get_customer_overview. customer name is {args.customer_name}")
    try:
        customer_name = clean_title(args.customer_name)
        overview = get_customer_overview(customer_name = customer_name)
        if overview is None:
            return error(
                message="Customer not found.",
                data = {"customer_name": args.customer_name})
        else:
            return success(
                message="Customer overview found",
                data = overview
            )
    except Exception as exc:
        logger.error(f"customer_tool: get_customer_overview. error: {exc}")
        return error(f"failed to get customer overview: {str(exc)}")
    
# check permissions tool
    
@function_tool(
    description_override = "provides permissions on actions the user can do. Such as the ability to read/update/create customer/issues/issue notes/next actions",
    strict_mode= True,
    is_enabled = True
)
def get_my_permissions_tool(ctx: RunContextWrapper[AgentContextStore]) -> dict:
    try:
        logger.info("entered get_my_permissions tool")
        permissions = validate_tool_permissions(ctx)
        return success(
            message = "agent tool permissions found",
            data = permissions
        )
    except Exception as exc:
        logger.error(f"get_my_permissions_tool: error: {exc}")
        return error(f"failed to get tool permissions: {str(exc)}")
        

