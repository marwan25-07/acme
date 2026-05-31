from redis.asyncio import Redis
from .config.settings import acme_settings
import logging
import json
from runner.templates.build_logger_templates import logging_templates

logger = logging.getLogger(__name__)
draft_logging_ticket = logging_templates(filename="redis_client.py")

class RedisStore:
    def __init__(self) -> None:
        self.redis_url = acme_settings.redis_url
        self.redis = Redis.from_url(self.redis_url, decode_responses=True)

    async def ping(self):
        try:
            await self.redis.ping()
            info_log = draft_logging_ticket.create_info_log(
                event = "redis successfully started",
                function= self.ping.__name__,
            )
            return  
        except Exception as e:
            critical_log = draft_logging_ticket.create_critical_log(
                event="redis ping failed",
                function= self.ping.__name__,
                error_type= type(e).__name__,
                error= e,
                developer_note= "check health status of redis",
            )
            logger.critical(critical_log)
            raise ConnectionError(detail= "redis store unavailable")
        
    async def add_item(self, key:str, value:str|list[str]|dict) -> None:
        try:
            await self.redis.set(key, json.dumps(value), ex=acme_settings.agent_memory_expiry_ttl)
        except Exception as e:
            logger.error(f"redis_store failed to add item: {e}")
        return None
    
    async def get_item(self, key:str) -> str|list[str]|dict:
        try:
            retrieved_item = await self.redis.get(key)
        except Exception as e:
            logger.error(f"redis_store failed to get item: {e}")
        return retrieved_item
    
    async def delete_item(self, key:str) -> None:
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"redis_store failed to delete item: {e}")
        return None

    async def close(self) -> None:
        try:
            await self.redis.close()
        except Exception as e:
            logger.error(f"error closing redis connection: {e}")
