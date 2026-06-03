from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from contextlib import asynccontextmanager
from pydantic import BaseModel
from auth import validate_token
import logging
from runner.redis_client import RedisStore
from runner.core import run_acme_agent
from runner.schemas import AgentContextStore, TraceEventPayload, TraceEventStatus, TraceEventType
from runner.agent_memory import memory_store
from observability.tracing import (
    new_trace_id,
    write_trace_event,
    now_ms
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_store = RedisStore()

def extract_user_info(token_payload:dict) -> dict:
    allowed_roles = ["admin", "sales_user", "support_user"]
    user_roles = token_payload.get('realm_access', {}).get('roles', {})
    official_role = None
    for role in user_roles:
        if role in allowed_roles:
            official_role=role 
            break
    if official_role ==None:
        raise HTTPException(status_code=403, detail="Invalid Authorisation Role")
    else:
        return {
            "name": token_payload.get('name'),
            "role": official_role  
        }

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ping redis 
    await redis_store.ping()

    yield
    #close redis connection
    await redis_store.close()

app = FastAPI(lifespan=lifespan)

class request_payload(BaseModel):
    text:str


@app.post("/acme/chat/completion")
async def validate_acme(
    payload: request_payload,
    background_tasks: BackgroundTasks,
    authorization:str = Header(alias="Authorization"),
    conversation_id:str|int = Header(alias="conversation-id"),
    user_id:str|int = Header(alias="user-id"),
    ):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail = "Invalid authorization")
    
    extract_authorization_token = authorization.split(" ")[1]
    token_payload = validate_token(extract_authorization_token)

    user_info = extract_user_info(token_payload)
    _memory_store = memory_store(conversation_id=conversation_id, user_id=user_id, user_name= user_info['name'], user_role=user_info['role'])
    agent_memory = await _memory_store.get_agent_conversation_memory()
    agent_memory.append({"role":"user", "content": payload.text})
    logger.info(agent_memory)

    # init traces
    trace_id = new_trace_id()
    start_ms = now_ms()

    write_trace_event(
        trace_id=trace_id,
        event_type= TraceEventType.REQUEST_START,
        payload = {
            "endpoint": "/chat",
            "user_role": user_info['role'],
            "user_query": payload.text,
            "start_ms": start_ms
        }
    )

    # run agent
    response = None
    catch_error = None
    try:
    
        agent_context_store = AgentContextStore(user_role= user_info['role'], trace_id=trace_id, user_id=user_id, conversation_id=conversation_id)  #user_info['role']
        response = await run_acme_agent(user_text= agent_memory, agent_context_store=agent_context_store)
        _memory_store.extend_agent_memory(current_memory=agent_memory, new_knowledge= [{"role":"assistant", "content": response}], background_tasks=background_tasks)
        return {
        "trace_id": trace_id,
        "text": response
        }
    
    except Exception as e:
        catch_error = e
        logger.error(catch_error)
        logger.info("trace logged")
        raise HTTPException(status_code=500, detail=f"Trace ID: {trace_id}")
    
    finally:
        write_trace_event(
            trace_id=trace_id,
            event_type= TraceEventType.RESPONSE,
            payload= TraceEventPayload(
                status = TraceEventStatus.SUCCESS if catch_error==None else TraceEventStatus.ERROR,
                response = response if catch_error is None else str(catch_error),
                latency_ms = now_ms() - start_ms
            )
        )
        logger.info("Trace Logged")


