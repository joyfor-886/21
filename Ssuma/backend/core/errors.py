from enum import Enum
from typing import Optional, Dict, Any
from fastapi import HTTPException


class ErrorCode(Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    CIRCUIT_BREAKER_OPEN = "CIRCUIT_BREAKER_OPEN"
    SKILL_EXECUTION_FAILED = "SKILL_EXECUTION_FAILED"
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    UNAUTHORIZED = "UNAUTHORIZED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CONTEXT_OVERFLOW = "CONTEXT_OVERFLOW"
    FACT_CHECK_FAILED = "FACT_CHECK_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


ERROR_HTTP_STATUS = {
    ErrorCode.INVALID_REQUEST: 400,
    ErrorCode.PROJECT_NOT_FOUND: 404,
    ErrorCode.LLM_UNAVAILABLE: 503,
    ErrorCode.LLM_TIMEOUT: 504,
    ErrorCode.CIRCUIT_BREAKER_OPEN: 503,
    ErrorCode.SKILL_EXECUTION_FAILED: 500,
    ErrorCode.WORKFLOW_ERROR: 500,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.CONTEXT_OVERFLOW: 413,
    ErrorCode.FACT_CHECK_FAILED: 500,
    ErrorCode.VALIDATION_FAILED: 422,
}


class SsumaError(HTTPException):
    def __init__(
        self,
        code: ErrorCode,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        self.error_code = code
        self.message = message or code.value
        self.detail_dict = details or {}
        self.request_id = request_id
        status_code = ERROR_HTTP_STATUS.get(code, 500)
        error_body = {
            "error": code.value,
            "message": self.message,
            "detail": self.detail_dict,
        }
        if request_id:
            error_body["request_id"] = request_id
        super().__init__(
            status_code=status_code,
            detail=error_body,
        )
