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
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
customer_support_agent = Agent[AgentContextStore](
    name = "Customer Support agent",
    instructions = prompts._get_dynamic_system_prompt,
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

async def run_acme_agent(user_text: list[str], agent_context_store:RunContextWrapper[AgentContextStore]) -> str:
    try:
        response = await Runner.run(customer_support_agent, user_text, context=agent_context_store)
        return response.final_output
    except InputGuardrailTripwireTriggered:
        logger.warning("Context guardrail triggered")
        raise Exception("User query out of context")
    