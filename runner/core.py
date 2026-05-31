from agents import(
    Agent,
    Runner, 
    handoff,
    RunContextWrapper,
    TResponseInputItem,
    input_guardrail,
    InputGuardrailTripwireTriggered,
    GuardrailFunctionOutput
)
from runner.tools.customer_tools import(
    create_customer_tool,
    list_customers_tool,
    update_customer_tool,
    create_issue_tool,
    update_issue_tool,
    add_issue_note_tool,
    update_issue_note_tool,
    add_next_action_tool,
    update_next_action_tool,
    get_customer_overview_tool,
    get_my_permissions_tool,
    get_next_actions_tool
)
from runner.config.models import main_model, mini_model
from runner.schemas import AgentContextStore
import runner.config.prompts as prompts
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TargetAgentOptions(str, Enum):
    small_tasks = "Small Tasks agent"
    customer_support = "Customers Support agent"

class RequiredContextFormat(BaseModel):
    customer_id: Optional[int|None] = Field(..., description="The customer id.")
    customer_name: Optional[str|None] = Field(..., description= "The company's name.")
    issue_id: Optional[int|None] = Field(..., description= "The issue id.")
    issue_name: Optional[str|None] = Field(..., description= "The name of the issue")

class RouterOutputFormat(BaseModel):
    target_agent: TargetAgentOptions = Field(..., description= "Name of agent being handed off to.")
    reason: str = Field(..., description= "The reason why the target agent was selected for handoff")
    user_intent: str = Field(..., description= "A concise statement of the intent behind the user question")
    required_context: RequiredContextFormat

class HandoffToRouterFormat(BaseModel):
    target_agent: str = "Router agent"
    reason: str = Field(..., description= "Why this agent could not complete the user request")

# Input Guardrail
class ContextGuardrailFormat(BaseModel):
    out_of_context: bool = Field(..., description= "True or False on whether the question provided by the user has breached the guardrails of the system")
    reason: str = Field(..., description= "What criteria did the user breach, for their question to be considered out of context")

context_guardrail = Agent(
    name = "Context Guardrail Agent",
    model = mini_model(),
    instructions = prompts.get_context_guardrail_instructions(),
    output_type= ContextGuardrailFormat
)

@input_guardrail
async def context_guardrail_check(ctx: RunContextWrapper[None], agent: Agent, input: str|list[TResponseInputItem]) -> GuardrailFunctionOutput:
    result = await Runner.run(context_guardrail, input, context=ctx.context)
    return GuardrailFunctionOutput(
        output_info= result.final_output.reason,
        tripwire_triggered = result.final_output.out_of_context
    )

# Core Agents
def on_handoff_router_to_agent_flow(context, args: RouterOutputFormat):
    logger.info("HANDOFFF OCCURED")
    logger.info({
        "target_agent": args.target_agent,
        "reason": args.reason,
        "user_intent": args.user_intent,
        "required_context": args.required_context
    })

def on_handoff_agent_to_router_flow(context, args: HandoffToRouterFormat):
    logger.info({
        "target_agent": args.target_agent,
        "reason": args.reason,
    })

router_agent = Agent(
    name = "Router agent",
    instructions = prompts.get_router_instructions(),
    model = main_model(),
    input_guardrails = [context_guardrail_check]
)

small_tasks_agent = Agent(
    name = "Small Tasks agent",
    instructions = prompts.get_small_tasks_instrcutions(),
    model = mini_model(),
)

customer_support_agent = Agent(
    name = "Customer Support agent",
    instructions = prompts.get_customer_support_instructions(),
    model = main_model(),
    tools= [create_customer_tool,  
            list_customers_tool, 
            update_customer_tool, 
            create_issue_tool, 
            update_issue_tool, 
            add_issue_note_tool, 
            update_issue_note_tool, 
            add_next_action_tool, 
            update_next_action_tool, 
            get_customer_overview_tool,
            get_my_permissions_tool,
            get_next_actions_tool]
)

# Handoffs
handoff_to_small_tasks = handoff(
    small_tasks_agent,
    is_enabled=True,
    input_type = RouterOutputFormat,
    on_handoff = on_handoff_router_to_agent_flow
)
handoff_to_customer_support = handoff(
    customer_support_agent,
    is_enabled=True,
    input_type= RouterOutputFormat,
    on_handoff = on_handoff_router_to_agent_flow
)
handoff_to_router = handoff(
    router_agent,
    is_enabled=True,
    input_type=HandoffToRouterFormat,
    on_handoff = on_handoff_agent_to_router_flow
)

router_agent.handoffs = [handoff_to_customer_support, handoff_to_small_tasks]
customer_support_agent.handoffs =[handoff_to_router]
small_tasks_agent.handoffs =[handoff_to_router]

async def run_router_agent(user_text: list[str], agent_context_store:RunContextWrapper[AgentContextStore]) -> str:
    try:
        response = await Runner.run(router_agent, user_text, context=agent_context_store)
        return response.final_output
    except InputGuardrailTripwireTriggered:
        logger.warning("Context guardrail triggered")
        raise Exception("User query out of context")
    