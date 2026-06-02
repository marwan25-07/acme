from redis.asyncio import Redis
from .config.settings import acme_settings
import logging
import json
from runner.templates.build_logger_templates import LoggingTemplates

logger = logging.getLogger(__name__)

class RedisStore:
    def __init__(self) -> None:
        self.redis_url = acme_settings.redis_url
        self.redis = Redis.from_url(self.redis_url, decode_responses=True)

    async def ping(self):
        try:
            await self.redis.ping()
            logging.info("redis successfully started")
            return  
        except Exception as e:
            logger.critical("redis ping failed")
            raise ConnectionError(detail= "redis store unavailable")
        
    async def add_item(self, key:str, value:str|list[str]|dict) -> None:
        try:
            await self.redis.set(key, json.dumps(value))
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
