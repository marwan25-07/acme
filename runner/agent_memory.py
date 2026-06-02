from pydantic import BaseModel
from runner.redis_client import RedisStore
import runner.config.prompts as prompts
import json
import logging
from fastapi import BackgroundTasks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    async def check_existing_session(self) -> list:
        retrieve_conversation = await self.redis.get_item(f"{self.user_id}:{self.conversation_id}")
        if retrieve_conversation is not None:
            decoded_retrieve_conversation = json.loads(retrieve_conversation)
            return decoded_retrieve_conversation
        else:
            return None

    def check_conversation_memory_size(self, conversation_list:list) -> list:
        conversation_size = len(conversation_list)
        if conversation_size >= 21:
            logger.info(f"conversation size {conversation_size} exceeded the limit. Adjusting conversation memory")
            del conversation_list[1:3] #deleting the second and third item in the conversation which are to be the oldest user and agent messages after the system message
            return conversation_list
        else:
            return conversation_list

    async def get_agent_conversation_memory(self) -> list:
        retrieve_current_conversation = await self.check_existing_session()
        if retrieve_current_conversation is not None:
            adjusted_conversation_memory = self.check_conversation_memory_size(retrieve_current_conversation)
            return adjusted_conversation_memory
        else:
            get_greeting_message = self.generate_system_message_if_needed()
            return get_greeting_message