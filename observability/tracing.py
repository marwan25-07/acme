import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from runner.schemas import TraceEventStatus, TraceEventPayload, TraceEventType, ToolResultStatus

TRACE_DIR = Path("traces")
TRACE_DIR.mkdir(exist_ok=True)


def now_ms() -> int:
    return int(time.time() * 1000)


def new_trace_id() -> str:
    return str(uuid.uuid4())


def get_trace_file(trace_id: str) -> Path:
    return TRACE_DIR / f"{trace_id}.jsonl"


def write_trace_event(trace_id: str, event_type: TraceEventType, payload: TraceEventPayload) -> None:  #Dict[str, Any]
    event = {
        "timestamp_ms": now_ms(),
        "trace_id": trace_id,
        "event_type": event_type,
        "payload": payload,
    }

    with get_trace_file(trace_id).open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")


def trace_tool_call(
    trace_id: str,
    tool_name: str,
    tool_status: ToolResultStatus,
    tool_input: Dict[str, Any],
    tool_output: Optional[Any] = None,
    latency_ms: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    write_trace_event(
        trace_id=trace_id,
        event_type= TraceEventType.TOOL_CALL,
        payload={
            "tool_name": tool_name,
            "tool_status": tool_status,
            "tool_input": tool_input,
            "tool_output": str(tool_output) if tool_output is not None else None,
            "latency_ms": latency_ms,
            "error": error,
        },
    )


def get_tool_names_from_trace(trace_id: str) -> list[str]:
    """
    Reads a trace JSONL file and returns the unique tool names
    from events where event_type == 'tool_call'.
    """
    trace_file = get_trace_file(trace_id)

    if not trace_file.exists():
        return []

    tool_names = []

    with trace_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            event = json.loads(line)

            if event.get("event_type") != "tool_call":
                continue

            tool_name = event.get("tool_name")

            if tool_name and tool_name not in tool_names:
                tool_names.append(tool_name)

    return tool_names