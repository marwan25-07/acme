from pydantic import BaseModel
from runner.redis_client import RedisStore
import runner.config.prompts as prompts
import json
import logging
from fastapi import BackgroundTasks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


"""
build agent notes -> check whether current session exist -> if exists, retrieve conversation history -> return 
if current session does not exist -> create initial system greeting message ->return 

##after agnet response on main py
append user text and response from agent to redis store (have a think about latency, if you save to context store before function return user expe-riences more latency)

#tools
append to agent_notes_store 
retrieve from agent_notes_store
greeting message generator 
"""

class agent_notes_schema(BaseModel):
    user_test: str
    agent_message: str


class memory_store:
    def __init__(self, conversation_id:str, user_id:str, user_name:str, user_role:str):
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.user_name = user_name
        self.user_role = user_role
        self.redis = RedisStore()

    def extend_agent_memory(self, current_memory:list, new_knowledge:list, background_tasks:BackgroundTasks) -> None:
        current_memory.extend(new_knowledge)
        background_tasks.add_task(self.redis.add_item, f"{self.user_id}:{self.conversation_id}", current_memory)
        logger.info("memory extended")
        return

    def generate_system_message_if_needed(self) -> list[dict]:
        get_message = prompts.get_system_greeting_message(user_name=self.user_name, user_role=self.user_role)
        return [{"role": "system", "content": get_message}]

    async def check_exsiting_session(self) -> dict:
        retrieve_conversation = await self.redis.get_item(f"{self.user_id}:{self.conversation_id}")
        if retrieve_conversation is not None:
            logger.info(f"this is waht is being retrrieved {retrieve_conversation}")
            decoded_retrieve_conversation = json.loads(retrieve_conversation)
            return decoded_retrieve_conversation
        else:
            return None

    async def get_agent_conversation_memory(self) -> list:
        retrieve_current_conversation = await self.check_exsiting_session()
        if retrieve_current_conversation is not None:
            return retrieve_current_conversation
        else:
            get_greeting_message = self.generate_system_message_if_needed()
            return get_greeting_message