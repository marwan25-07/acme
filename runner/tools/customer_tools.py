from pydantic import BaseModel, Field
from agents import function_tool, RunContextWrapper
from runner.schemas import (
    AgentContextStore,
    ToolResultStatus,
    ToolResult,
    IssuePriority,
    IssueStatus
)
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
from observability.tracing import trace_tool_call
from runner.tools.tool_permissions import permission_checker, validate_tool_permissions
from runner.templates.build_logger_templates import LoggingTemplates
import time
import logging 



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def success(message: str, data: Any = None) -> dict:
    return ToolResult(
        status=ToolResultStatus.SUCCESS.value,
        message=message,
        data=data,
    ).model_dump()


def error(message: str, data: Any = None) -> dict:
    return ToolResult(
        status=ToolResultStatus.ERROR.value,
        message=message,
        data=data,
    ).model_dump()  

def clean_title(value: str|None) -> str|None:
    if value is None:
        return None
    else:
        value = value.strip().title()
        return value
    
def log_agent_info(ctx: RunContextWrapper[AgentContextStore]):
    init_logger = LoggingTemplates(filename="customer_tools.py", user_id=ctx.context.user_id, conversation_id=ctx.context.conversation_id)
    return init_logger


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
def create_customer_tool(ctx:RunContextWrapper[AgentContextStore], args: CreateCustomerInput) -> dict:
    start_time=time.time()

    #set default values
    caught_error = None
    customer = None

    log = log_agent_info(ctx)
    log.create_info_log(event="create_customer_tool called", function="create_customer_tool", developer_note= None)
    try:
        customer_id = add_customer(
            name=clean_title(args.name),
            industry=clean_title(args.industry),
            account_manager=clean_title(args.account_manager),
        )
        customer = get_customer_by_id(customer_id)
        
        log.create_info_log(event="create_customer_tool completed", function="create_customer_tool", developer_note= None)
        return success(
            message="Customer created or updated successfully.",
            data=customer,
        )

    except Exception as exc:
        caught_error = exc
        log.create_error_log(event="create_customer_tool failed", function="create_customer_tool", error_type= type(exc).__name__, error= exc, developer_note= None)
        return error(f"Failed to create customer: {str(exc)}")
    
    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="create customer",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= {"title": args.name, "industry":args.industry, "account_manager": args.account_manager},
                tool_output= customer,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="create_customer tool call traced", function="create_customer_tool", developer_note= None)
    
    
# find customer
class FindCustomerInput(BaseModel):
    customer_name: str = Field(..., description="The exact customer/company name to search for.")

@function_tool(
        description_override= "Finds Customer information by providing customer name as input",
        strict_mode = True,
        is_enabled=permission_checker("read_customer")
)
def find_customer_tool(ctx:RunContextWrapper[AgentContextStore], args: FindCustomerInput) -> dict:
    start_time=time.time()

    #set default values
    caught_error = None
    customer = None

    log = log_agent_info(ctx)
    log.create_info_log(event="find_customer_tool called", function="find_customer_tool", developer_note= None)
    try:
        customer = get_customer(clean_title(args.customer_name))

        if customer is None:
            return error(
                message="Customer not found.",
                data={"customer_name": args.customer_name},
            )
        
        find_customer_tool
        return success(
            message="Customer found.",
            data=customer,
        )

    except Exception as exc:
        caught_error = exc
        logger.error(f"customer_tool: find_customer_tool. error: {exc}")
        return error(f"Failed to find customer: {str(exc)}")
    
    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="find customer",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= {"customer_name": args.customer_name},
                tool_output= customer,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="find_customer tool call traced", function="find_customer_tool", developer_note= None)
    
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
def list_customers_tool(ctx:RunContextWrapper[AgentContextStore]) -> dict:
    start_time=time.time()

    #set default values
    caught_error = None
    customers = None

    log = log_agent_info(ctx)
    log.create_info_log(event="list_customers_tool called", function="list_customers_tool", developer_note= None)
    try:
        customers = list_customers(search=None)

        log.create_info_log(event="list_customers_tool completed", function="list_customers_tool", developer_note= None)
        return success(
            message=f"Found {len(customers)} customer(s).",
            data=customers,
        )

    except Exception as exc:
        caught_error = exc
        logger.error(f"customer_tool: list_customers_tool. error: {exc}")
        return error(f"Failed to list customers: {str(exc)}")

    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="list customers",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= None,
                tool_output= customers,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="list_customers tool call traced", function="list_customers_tool", developer_note= None)
    
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
def update_customer_tool(ctx:RunContextWrapper[AgentContextStore], args: UpdateCustomerInput) -> dict:
    start_time=time.time()

    #set default values
    caught_error = None
    updated_customer = None

    log = log_agent_info(ctx)
    log.create_info_log(event="list_customers_tool called", function="update_customer_tool", developer_note= None)
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
        log.create_info_log(event="list_customers_tool completed", function="update_customer_tool", developer_note= None)
        return success(
            message="Customer updated successfully.",
            data=updated_customer,
        )

    except Exception as exc:
        caught_error = exc
        logger.error(f"customer_tool: update_customer_tool. error: {exc}")
        return error(f"Failed to update customer: {str(exc)}")
    
    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="update customer",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= {"customer_id": args.customer_id, "title":args.title, "industry": args.industry, "account_manager": args.account_manager},
                tool_output= updated_customer,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="list_customers tool trace completed", function="update_customer_tool", developer_note= None)

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
def create_issue_tool(ctx:RunContextWrapper[AgentContextStore], args: CreateIssueInput) -> dict:
    start_time=time.time()

    #set default values
    caught_error = None
    issue = None
    
    log = log_agent_info(ctx)
    log.create_info_log(event="create_issue_tool called", function="create_issue_tool", developer_note= None)
    try:
        issue_id = add_issue(
            customer_id=args.customer_id,
            title=args.title,
            status=args.status.value,
            priority=args.priority.value if args.priority else None,
        )
        issue = get_issue(issue_id)

        log.create_info_log(event="create_issue_tool completed", function="create_issue_tool", developer_note= None)
        return success(
            message="Issue created or updated successfully.",
            data=issue,
        )

    except Exception as exc:
        caught_error = exc
        logger.error(f"customer_tool: create_issue_tool. error: {exc}")
        return error(f"Failed to create issue: {str(exc)}")
    
    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="create issue",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= {"customer_id": args.customer_id, "title":args.title, "status": args.status, "priority": args.priority},
                tool_output= issue,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="create_issue tool trace completed", function="create_issue_tool", developer_note= None)
    
# get issue
class GetIssueInput(BaseModel):
    issue_id: int = Field(..., description="The issue ID.")

@function_tool(
        description_override= "Get a single issue, by passing issue id as input",
        strict_mode = True,
        is_enabled=permission_checker("read_issue")
)
def get_issue_tool(ctx:RunContextWrapper[AgentContextStore], args: GetIssueInput) -> dict:
    start_time=time.time()

    #set default values
    caught_error = None
    issue = None

    log = log_agent_info(ctx)
    log.create_info_log(event="get_issue_tool called", function="get_issue_tool", developer_note= None)
    try:
        issue = get_issue(args.issue_id)

        if issue is None:
            return error(
                message="Issue not found.",
                data={"issue_id": args.issue_id},
            )

        log.create_info_log(event="get_issue_tool completed", function="get_issue_tool", developer_note= None)
        return success(
            message="Issue found.",
            data=issue,
        )

    except Exception as exc:
        caught_error = exc
        logger.error(f"customer_tool: get_issue_tool. error: {exc}")
        return error(f"Failed to get issue: {str(exc)}")
    
    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="get issue",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= {"issue_id": args.issue_id},
                tool_output= issue,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="get_issue tool trace completed", function="get_issue_tool", developer_note= None)
    
# list customer issues
class GetCustomerIssuesInput(BaseModel):
    customer_id: int = Field(..., description="The customer ID.")

@function_tool(
        description_override= "Gets all issues relating to a single customer by passing customer id as input",
        strict_mode = True,
        is_enabled=permission_checker("read_issue")
)
def get_customer_issues_tool(ctx:RunContextWrapper[AgentContextStore], args: GetCustomerIssuesInput) -> dict:
    start_time=time.time()

    #set default values
    caught_error = None
    issues = None

    log = log_agent_info(ctx)
    log.create_info_log(event="get_customer_issues_tool called", function="get_customer_issues_tool", developer_note= None)
    try:
        issues = get_customer_issues(args.customer_id)

        log.create_info_log(event="get_customer_issues_tool completed", function="get_customer_issues_tool", developer_note= None)
        return success(
            message=f"Found {len(issues)} issue(s).",
            data=issues,
        )

    except Exception as exc:
        caught_error = exc
        logger.error(f"customer_tool: get_customer_issues_tool. error: {exc}")
        return error(f"Failed to get customer issues: {str(exc)}")
    
    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="get customer issues",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= {"customer_id": args.customer_id},
                tool_output= issues,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="get_customer_issues_tool trace completed", function="get_customer_issues_tool", developer_note= None)
    
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
def update_issue_tool(ctx:RunContextWrapper[AgentContextStore], args: UpdateIssueInput) -> dict:
    start_time=time.time()

    #set default values
    caught_error = None
    updated_issue = None

    log = log_agent_info(ctx)
    log.create_info_log(event="update_issue_tool called", function="update_issue_tool", developer_note= None)
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

        log.create_info_log(event="update_issue_tool completed", function="update_issue_tool", developer_note= None)
        return success(
            message="Issue updated successfully.",
            data=updated_issue,
        )

    except Exception as exc:
        caught_error = exc
        logger.error(f"customer_tool:update_issue_tool. error: {exc}")
        return error(f"Failed to update issue: {str(exc)}")

    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="update issue",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= {"issue_id": args.issue_id, "title": args.title, "status": args.status.value if args.status else None, "priority": args.priority.value if args.priority else None},
                tool_output= updated_issue,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="update_issue_tool trace completed", function="update_issue_tool", developer_note= None)

# add issue note
class AddIssueNoteInput(BaseModel):
    issue_id: int = Field(..., description="The issue ID this note belongs to.")
    note_text: str = Field(..., description="The note/update text to add to the issue.")

@function_tool(
        description_override= "Add a note, by passing as inputs: issue id, and note.",
        strict_mode = True,
        is_enabled=permission_checker("create_issue")
)
def add_issue_note_tool(ctx:RunContextWrapper[AgentContextStore], args: AddIssueNoteInput) -> dict:
    start_time=time.time()

    #set default values
    caught_error = None
    update_id = None
    
    log = log_agent_info(ctx)
    log.create_info_log(event="add_issue_note_tool called", function="add_issue_note_tool", developer_note= None)
    try:
        update_id = add_issue_update(
            issue_id=args.issue_id,
            update_text=args.note_text,
        )
        updates = get_issue_updates(args.issue_id)

        log.create_info_log(event="add_issue_note_tool completed", function="add_issue_note_tool", developer_note= None)
        return success(
            message="Issue note added successfully.",
            data={
                "update_id": update_id,
                "issue_id": args.issue_id,
                "all_updates": updates,
            },
        )

    except Exception as exc:
        caught_error = exc
        logger.error(f"customer_tool:add_issue_note_tool. error: {exc}")
        return error(f"Failed to add issue note: {str(exc)}")
    
    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="add issue notes",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= {"issue_id": args.issue_id, "update_text": args.note_text},
                tool_output= update_id,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="add_issue_note_tool trace completed", function="add_issue_note_tool", developer_note= None)

# get issue notes
class GetIssueNotesInput(BaseModel):
    issue_id: int = Field(..., description="The issue ID.")

@function_tool(
        description_override= "Get all notes for a single issue by passing as input: issue id.",
        strict_mode = True,
        is_enabled=permission_checker("read_issue")
)
def get_issue_notes_tool(ctx:RunContextWrapper[AgentContextStore], args: GetIssueNotesInput) -> dict:
    start_time=time.time()

    #set default values
    caught_error = None
    updates = None

    log = log_agent_info(ctx)
    log.create_info_log(event="get_issue_notes_tool called", function="get_issue_notes_tool", developer_note= None)
    try:
        updates = get_issue_updates(args.issue_id)

        log.create_info_log(event="get_issue_notes_tool completed", function="get_issue_notes_tool", developer_note= None)
        return success(
            message=f"Found {len(updates)} note(s).",
            data=updates,
        )

    except Exception as exc:
        caught_error = exc
        logger.error(f"customer_tool: get_issue_notes_tool. error: {exc}")
        return error(f"Failed to get issue notes: {str(exc)}")
    
    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="get issue notes",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= {"issue_id": args.issue_id},
                tool_output= updates,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="get_issue_notes_tool trace completed", function="get_issue_notes_tool", developer_note= None)

# update issue note   
class UpdateIssueNoteInput(BaseModel):
    update_id: int = Field(..., description="The ID of the note/update to edit.")
    note_text: str = Field(..., description="The new note text.")

@function_tool(
        description_override= "Updates an existing issue note, by passing as input: update id, note text.",
        strict_mode = True,
        is_enabled=permission_checker("update_issue")
)
def update_issue_note_tool(ctx:RunContextWrapper[AgentContextStore], args: UpdateIssueNoteInput) -> dict:
    start_time=time.time()
    logger.info(f"entering customer_tool: update_issue_note_tool")

    #set default values
    caught_error = None
    updated_note = None

    log = log_agent_info(ctx)
    log.create_info_log(event="update_issue_note_tool called", function="update_issue_note_tool", developer_note= None)
    try:
        updated_note = update_issue_update(
            update_id=args.update_id,
            update_text=args.note_text,
        )

        log.create_info_log(event="update_issue_note_tool completed", function="update_issue_note_tool", developer_note= None)
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
        caught_error = exc
        logger.error(f"customer_tool: update_issue_note_tool. error: {exc}")
        return error(f"Failed to update issue note: {str(exc)}")
    
    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="update issue note",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= {"update_id": args.update_id, "updated_text": args.update_text},
                tool_output= None,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="update_issue_note_tool trace completed", function="update_issue_note_tool", developer_note= None)
    
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
def add_next_action_tool(ctx:RunContextWrapper[AgentContextStore], args: AddNextActionInput) -> dict:
    start_time=time.time()

    #set default values
    caught_error = None
    actions = None

    log = log_agent_info(ctx)
    log.create_info_log(event="add_next_action_tool called", function="add_next_action_tool", developer_note= None)
    try:
        action_id = add_next_action(
            issue_id=args.issue_id,
            action_text=args.action_text,
            created_by=clean_title(args.created_by),
        )
        actions = get_next_actions(args.issue_id)

        log.create_info_log(event= f"add_next_action_tool completed. {str(actions)}", function="add_next_action_tool", developer_note= None)
        test_success = success(
            message="Next action added successfully.",
            data=None,
        )
        logger.info(f"logging test {test_success}")
        return test_success
    except Exception as exc:
        logging.info("i am in expection block")
        caught_error = exc
        logger.error(f"customer_tool: add_next_action_tool. error: {exc}")
        return error(f"Failed to add next action: {str(exc)}")
    
    finally:
        logging.info("i am in finally block")
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="add next-action",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= {"issue_id": args.issue_id},
                tool_output= None,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="add_next_action_tool trace completed", function="add_next_action_tool", developer_note= None)
    
# get next actions
class GetNextActionsInput(BaseModel):
    issue_id: int = Field(..., description="The issue ID.")

@function_tool(
        description_override= "Gets all next actions for a single issue by passing as input: issue_id",
        strict_mode = True,
        is_enabled=permission_checker("read_actions")
)
def get_next_actions_tool(ctx:RunContextWrapper[AgentContextStore], args: GetNextActionsInput) -> dict:
    start_time=time.time()

    #set default values
    caught_error = None
    actions = None

    log = log_agent_info(ctx)
    log.create_info_log(event="get_next_actions_tool called", function="get_next_actions_tool", developer_note= None)
    try:
        actions = get_next_actions(args.issue_id)

        log.create_info_log(event="get_next_actions_tool completed", function="get_next_actions_tool", developer_note= None)
        return success(
            message=f"Found {len(actions)} next action(s).",
            data=actions,
        )

    except Exception as exc:
        caught_error = exc
        logger.error(f"customer_tool: get_next_actions_tool. error: {exc}")
        return error(f"Failed to get next actions: {str(exc)}")
    
    finally:
        latency_ms = int((time.time() - start_time)*1000)
        try:
            trace_tool_call(
                    trace_id = ctx.context.trace_id,
                    tool_name="get next-actions",
                    tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                    tool_input= {"issue_id": args.issue_id},
                    tool_output= actions,
                    latency_ms = latency_ms,
                    error=str(caught_error) if caught_error else None
                )
            log.create_info_log(event="get_next_actions_tool trace completed", function="get_next_actions_tool", developer_note= None)
        except Exception as e:
            logger.exception(f"error: {e}")
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
def update_next_action_tool(ctx:RunContextWrapper[AgentContextStore], args: UpdateNextActionInput) -> dict:
    start_time=time.time()

    #set default values
    caught_error = None
    updated_action = None

    log = log_agent_info(ctx)
    log.create_info_log(event="update_next_action_tool called", function="update_next_action_tool", developer_note= None)
    try:
        updated_action = update_next_action(
            action_id=args.action_id,
            action_text=args.action_text,
            created_by=clean_title(args.created_by),
        )

        log.create_info_log(event="update_next_action_tool completed", function="update_next_action_tool", developer_note= None)
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
        caught_error = exc
        logger.error(f"customer_tool: update_next_action_tool. error: {exc}")
        return error(f"Failed to update next action: {str(exc)}")
    
    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_name="update next-action",
                tool_input= {"action_id": args.action_id, "action_text": args.action_text, "created_by": args.created_by},
                tool_output= None,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="update_next_action_tool trace completed", function="update_next_action_tool", developer_note= None)
    
# get customer overview
class GetCustomerOverviewInput(BaseModel):
    customer_name: str = Field(..., description="The exact company name.")

@function_tool(
        description_override= "Get a customer, their issues, issue notes. This is the main-context loading tool for the agent.",
        strict_mode = True,
        is_enabled=permission_checker("read_customer")
)
def get_customer_overview_tool(ctx:RunContextWrapper[AgentContextStore], args:GetCustomerOverviewInput):
    start_time = time.time()

    #set default values
    caught_error = None
    overview = None
    customer_name = None

    #run
    log = log_agent_info(ctx)
    log.create_info_log(event="get_customer_overview_tool called", function="get_customer_overview_tool", developer_note= None)
    try:
        customer_name = clean_title(args.customer_name)
        overview = get_customer_overview(customer_name = customer_name)

        log.create_info_log(event="get_customer_overview_tool completed", function="get_customer_overview_tool", developer_note= None)
        if overview is None:
            return error(
                message="Customer not found.",
                data = {"customer_name": args.customer_name})
        else:
            tool_result = success(
                message="Customer overview found",
                data = overview
            )
            return tool_result
        
    except Exception as exc:
        caught_error = exc
        logger.error(f"customer_tool: get_customer_overview. error: {exc}")
        tool_result = error(f"failed to get customer overview: {str(exc)}")
        return tool_result
    
    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="get_customer_overview",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= {"customer_name": customer_name or args.customer_name},
                tool_output= overview,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="get_customer_overview_tool trace completed", function="get_customer_overview_tool", developer_note= None)


# check permissions tool  
@function_tool(
    description_override = "provides permissions on actions the user can do. Such as the ability to read/update/create customer/issues/issue notes/next actions",
    strict_mode= True,
    is_enabled = True
)
def get_my_permissions_tool(ctx: RunContextWrapper[AgentContextStore]) -> dict:
    start_time = time.time()

    #set default values
    caught_error = None
    permissions = None

    log = log_agent_info(ctx)
    log.create_info_log(event="get_my_permissions_tool called", function="get_my_permissions_tool", developer_note= None)
    try:
        permissions = validate_tool_permissions(ctx)

        log.create_info_log(event="get_my_permissions_tool completed", function="get_my_permissions_tool", developer_note= None)
        return success(
            message = "agent tool permissions found",
            data = permissions
        )
    except Exception as exc:
        caught_error = exc
        logger.error(f"get_my_permissions_tool: error: {exc}")
        return error(f"failed to get tool permissions: {str(exc)}")

    finally:
        latency_ms = int((time.time() - start_time)*1000)
        trace_tool_call(
                trace_id = ctx.context.trace_id,
                tool_name="get_my_permission",
                tool_status = ToolResultStatus.SUCCESS if caught_error is None else ToolResultStatus.ERROR,
                tool_input= None,
                tool_output= permissions,
                latency_ms = latency_ms,
                error=str(caught_error) if caught_error else None
            )
        log.create_info_log(event="get_my_permissions_tool trace completed", function="get_my_permissions_tool", developer_note= None)
        

