from agents import function_tool 
import logging
from pydantic import Field, BaseModel
from typing import Any, Optional
from enum import Enum
from db.customer_repository import (
    list_customers, 
)

logger = logging.getLogger(__name__)

class ToolResultStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

class ToolResult(BaseModel):
    status: ToolResultStatus
    message: str
    data: Optional[Any] = None

def success(message: str, data: Any = None) -> dict:
    return ToolResult(
        status=ToolResultStatus.SUCCESS,
        message=message,
        data=data,
    ).model_dump()


def error(message: str, data: Any = None) -> dict:
    return ToolResult(
        status=ToolResultStatus.ERROR,
        message=message,
        data=data,
    ).model_dump()  

@function_tool
def get_faq():
    logger.info("entered rfaq tool")
    return """
    What is company house?
    Companies House is an executive agency of the Department for Business and Trade. It is responsible for incorporating and dissolving limited companies in England and Wales, holding and publishing company information and making this available to the general public.

    Companies House plays a vital role in the UK by helping to protect the public by ensuring that registered companies comply with the law and that their information is transparent and publicly available.

    Here are some of the key things that Companies House does:

    Incorporates and dissolves limited companies
    Registers and maintains company information
    Makes company information available to the public
    Investigate and prosecute companies that break the law
"""

# list customer
@function_tool
def list_customers_tool() -> dict:
    logger.info(f"entering customer_tool:")
    try:
        customers = list_customers(search=None)

        return success(
            message=f"Found {len(customers)} customer(s).",
            data=customers,
        )

    except Exception as exc:
        logger.error(f"customer_tool: error: {exc}")
        return error(f"Failed to list customers: {str(exc)}")