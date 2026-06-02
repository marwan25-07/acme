import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class LoggingTemplates:
    def __init__(
        self,
        filename: str,
        user_id: str | None = None,
        conversation_id: str | None = None
    ):
        self.filename = filename
        self.user_id = user_id
        self.conversation_id = conversation_id

    def create_error_log(
        self,
        event: str,
        function: str,
        error_type: str,
        error: Exception,
        developer_note: str|None = None
    ) -> dict:
        error_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "ERROR",
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "event": event,
            "error_type": error_type,
            "error_class": error.__class__.__name__,
            "error": str(error),
            "developer_note": developer_note,
            "source": {
                "filename": self.filename,
                "function": function
            }
        }

        logger.error(error_log)
        return error_log

    def create_critical_log(
        self,
        event: str,
        function: str,
        error_type: str,
        error: Exception,
        developer_note: str
    ) -> dict:
        critical_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "CRITICAL",
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "event": event,
            "error_type": error_type,
            "error_class": error.__class__.__name__,
            "error": str(error),
            "developer_note": developer_note,
            "source": {
                "filename": self.filename,
                "function": function
            }
        }

        logger.critical(critical_log)
        return critical_log

    def create_info_log(
        self,
        event: str,
        function: str,
        developer_note=None
    ) -> dict:
        info_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "event": event,
            "source": {
                "filename": self.filename,
                "function": function
            }
        }

        logger.info(info_log)
        return info_log