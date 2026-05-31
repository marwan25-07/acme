import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

class logging_templates:
    def __init__(self, filename:str):
        self.filename = filename
    
    def create_error_log(self, event: str, function:str, error_type:str, error: Exception, developer_note: str, user_id: str, conversation_id: str) -> dict:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "ERROR",
            "user_id": user_id,
            "conversation_id": conversation_id,
            "event": event,
            "error_type": error_type,
            "error": error,
            "developer_note": developer_note,
            "source": {
                "filename": self.filename,
                "function": function
            }
        }
    
    def create_critical_log(self, event: str, function: str, error_type: str, error: Exception, developer_note: str) -> dict:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "CRITICAL",
            "event": event,
            "error_type": error_type,
            "error": error,
            "developer_note": developer_note,
            "source": {
                "filename": self.filename,
                "function": function
            }
        }
    
    def create_info_log(self, event:str, function:str, user_id: str|None = None, conversation_id: str|None = None) -> dict:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "user_id": user_id,
            "conversation_id": conversation_id,
            "event": event,
            "source": {
                "filename": self.filename,
                "function": function
            }
        }