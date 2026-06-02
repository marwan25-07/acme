import json
from pathlib import Path
from datetime import datetime
import asyncio
import logging
from datetime import datetime
from runner.schemas import AgentContextStore, TraceEventPayload, TraceEventStatus, TraceEventType
from runner.core import run_acme_agent
from observability.tracing import (
    new_trace_id,
    write_trace_event,
    now_ms
)
from evals.evaluator import run_evaluator_agent

logger = logging.getLogger(__name__)

current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
EVAL_SET_PATH = Path("evals/evaluation_set.jsonl")
RESULTS_PATH = Path(f"evals/evaluations/eval_results_{current_time}.jsonl")
TRACES_DIR = Path("traces")


def load_eval_set():
    with EVAL_SET_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def evaluate_tool_selection(expected_tools, actual_tools):
    expected = set(expected_tools)
    actual = set(actual_tools)

    missing = expected - actual
    unexpected = actual - expected

    return {
        "passed": len(missing) == 0,
        "missing_tools": list(missing),
        "unexpected_tools": list(unexpected),
    }


def find_trace_file(trace_id: str) -> Path | None:
    """
    Finds the trace file for a given trace_id inside the traces folder.

    Supports:
    - traces/{trace_id}.jsonl
    - any .jsonl file that has trace_id in the filename
    """

    if not trace_id:
        return None

    exact_match = TRACES_DIR / f"{trace_id}.jsonl"

    if exact_match.exists():
        return exact_match

    if not TRACES_DIR.exists():
        logger.warning(f"Traces directory does not exist: {TRACES_DIR}")
        return None

    for trace_file in TRACES_DIR.glob("*.jsonl"):
        if trace_id in trace_file.name:
            return trace_file

    logger.warning(f"No trace file found for trace_id: {trace_id}")
    return None


def get_tool_calls_from_trace(trace_id: str) -> list[dict]:
    """
    Reads the matching trace file and returns all detailed tool_call events.
    """

    trace_file = find_trace_file(trace_id)

    if trace_file is None:
        return []

    tool_calls = []

    with trace_file.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                logger.warning(
                    f"Skipping invalid JSON in {trace_file} at line {line_number}"
                )
                continue

            if event.get("event_type") == "tool_call":
                tool_calls.append(event)

    return tool_calls


def get_tool_names_from_trace(trace_id: str) -> list[str]:
    """
    Reads the matching trace file and returns the unique tool names
    from events where event_type == 'tool_call'.
    """

    tool_calls = get_tool_calls_from_trace(trace_id)
    tool_names = []

    for tool_call in tool_calls:
        payload = tool_call.get("payload", {})
        tool_name = payload.get("tool_name")

        if tool_name and tool_name not in tool_names:
            tool_names.append(tool_name)
    return tool_names


def get_tool_ouputs_from_trace(trace_id: str) -> list[dict]:
    """
    Gets tool outputs along with the tool name, this is fed to the agent to assess 
    whether the response is grounded in truth.
    """
    tool_list = []
    tool_calls = get_tool_calls_from_trace(trace_id)
    for tool_call in tool_calls:
        payload = tool_call.get("payload", {})
        tool_name = payload.get("tool_name")
        tool_output = payload.get("tool_output")
        tool_list.append({"tool_name": tool_name, "tool_output": tool_output})
    return tool_list
        

def eval_rbac(user_role:str, tool_calls:list) -> bool:
    rbac_checker = True
    if user_role == "sales_user":
        permitted_tools = ["get_customer_overview", "list customers"]
        for tool in tool_calls:
            if tool not in permitted_tools:
                rbac_checker = False
    
    elif user_role == "support_user":
        permitted_tools = ["get_customer_overview", "list customers", "update issue", "update issue note"]
        for tool in tool_calls:
            if tool not in permitted_tools:
                rbac_checker = False
    
    if user_role == "support_user":
        permitted_tools = ["get_customer_overview", "list customers", "update issue", "update issue note", "update next-action", "create customer", "add issue notes", "create issue", "add next-action"]
        for tool in tool_calls:
            if tool not in permitted_tools:
                rbac_checker = False
    
    return rbac_checker
    

def translate_completeness_score(evaluator_response: dict) -> int:
    get_score = evaluator_response.get("response_quality_score")
    if get_score == "complete":
        return 3
    elif get_score == "partial":
        return 1
    else:
        return 0

async def run_eval_case(case):
    role = case["role"]
    trace_id = new_trace_id()
    start_ms = now_ms()

    write_trace_event(
        trace_id=trace_id,
        event_type= TraceEventType.REQUEST_START,
        payload = {
            "endpoint": "/chat",
            "user_role": role,
            "user_query": case['query'],
            "start_ms": start_ms
        }
    )

    try:
        catch_error = None
        agent_context_store = AgentContextStore(user_role= role, trace_id=trace_id, user_id="123", conversation_id="123") 
        support_agent_response = await run_acme_agent(user_text= case['query'], agent_context_store=agent_context_store)

    except Exception as e:
        catch_error = e
        logger.error(catch_error)
        raise Exception(e)
    
    finally:
        write_trace_event(
            trace_id=trace_id,
            event_type= TraceEventType.RESPONSE,
            payload= TraceEventPayload(
                status = TraceEventStatus.SUCCESS if catch_error==None else TraceEventStatus.ERROR,
                response = support_agent_response if catch_error is None else str(catch_error),
                latency_ms = now_ms() - start_ms
            )
        )
       
    tool_outputs = get_tool_ouputs_from_trace(trace_id)

    try:
        evaluator_response = await run_evaluator_agent(test_question=case["query"], test_response=support_agent_response, tool_outputs=tool_outputs)
        logger.info(f"eval_score. {evaluator_response}")
    except Exception as e:
        logger.error(e)
        raise Exception(e)

    actual_tools = get_tool_names_from_trace(trace_id) if trace_id else []
    tool_calls = get_tool_calls_from_trace(trace_id) if trace_id else []
    rbac_check = eval_rbac(user_role=role, tool_calls=actual_tools)

    tool_eval = evaluate_tool_selection(
        expected_tools=case["expected_tools"],
        actual_tools=actual_tools,
    )
    completeness_score = translate_completeness_score(evaluator_response)
    overall_score = int(rbac_check) + completeness_score + int(evaluator_response.get("grounded_in_tool_outputs"))

    return {
        "id": case["id"],
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "query": case["query"],
        "trace_id": trace_id,
        "success_criteria": case["success_criteria"],
        "response_scoring": {"tool_calls": {"expected_tools": case["expected_tools"], "actual_tools": actual_tools, "tool_eval": tool_eval}, "response_quality": {"response_quality_score": completeness_score, "response_quality_reason": evaluator_response.get("resposne_quality_reason")}, "grounding": {"truth_score": evaluator_response.get("grounded_in_tool_outputs"), "grounding_reason": evaluator_response.get("resposne_quality_reason")}},
        "rbac_check": rbac_check,
        "overall_score": f"{overall_score}/5",
        "response": support_agent_response,
    }


async def main():
    results = []

    if RESULTS_PATH.exists():
        RESULTS_PATH.unlink()

    for case in load_eval_set():
        print(f"Running {case['id']}...")

        result = await run_eval_case(case)
        results.append(result)

        with RESULTS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result, default=str) + "\n")


    print("Evaluation complete")
    print(f"Results written to {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())