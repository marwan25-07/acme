from agents import Agent, Runner
from pydantic import BaseModel
from enum import Enum
from runner.config.models import main_model

def get_evaluator_agent_prompt():
    return """
    You are an evaluator agent.

    Your task is to assess a customer support agent's response.

    You will receive:

        1. The original user question.
        2. The customer support agent's response.
        3. A list of tool outputs that were available to the agent.

    You must assess two things:

        1. Answer quality:
           Whether the assistant response answers the user's question.

        2. Grounding:
           Whether the assistant response is supported by the provided tool outputs.

    # Scoring rules for answer quality:

        * Complete: The response fully answers the user's question, with no important missing information.
        * Partial: The response answers some of the user's question, but misses important details, is vague, or only partially resolves the issue.
        * Incomplete: The response does not answer the user's question, is irrelevant, or fails to provide useful help.

    # Grounding rules:

        * grounded_in_tool_outputs must be true only if the important factual claims in the assistant response are supported by the tool outputs.
        * grounded_in_tool_outputs must be false if the assistant invents facts, adds unsupported details, contradicts the tool outputs, or claims that an action happened when the tool outputs do not support it.
        * If the tool outputs are empty or irrelevant, and the assistant makes factual claims that require tool/database evidence, grounded_in_tool_outputs must be false.
        * If the assistant says it could not find information, and that is consistent with the tool outputs, grounded_in_tool_outputs can be true.
        * Do not use your own knowledge to verify facts. Only use the provided tool outputs.
        * Do not answer the user's question yourself.
        * Do not give extra commentary outside the required JSON.

    Your final output must be valid JSON only, in this exact format:

        {
            "score": "complete" | "partial" | "incomplete",
            "grounded_in_tool_outputs": true | false,
            "reason": "Explain why this answer-quality score was given.",
            "grounding_reason": "Explain whether the response is or is not supported by the tool outputs."
        }
    """

class EvaluatorScoreOptions(str,Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    INCOMPLETE = "incomplete"


class EvaluatorOutput(BaseModel):
    response_quality_score: EvaluatorScoreOptions
    resposne_quality_reason: str
    grounded_in_tool_outputs: bool
    grounding_reason: str


evaluator_agent = Agent(
    name= "Evaluator Agent",
    instructions= get_evaluator_agent_prompt(), 
    model = main_model(),
    output_type= EvaluatorOutput
)

def format_agent_input(test_question:str, test_response:str, tool_outputs:list[dict]) -> list:
    return str({"user": test_question, "assistant": test_response, "tool_output": tool_outputs})

async def run_evaluator_agent(test_question:str, test_response:str, tool_outputs:list[dict]) -> dict:
    input_text = format_agent_input(test_question, test_response, tool_outputs)
    response = await Runner.run(evaluator_agent, input_text)
    eval_output =  response.final_output
    return eval_output.model_dump(mode="json")