import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from runscope_api.middleware import correlation_id_context

logger = logging.getLogger(__name__)


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def request_correlation_id(request: Request) -> str:
    return str(
        getattr(request.state, "correlation_id", "")
        or correlation_id_context.get()
        or request.headers.get("x-correlation-id", "")
    )[:128]


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    correlation_id = request_correlation_id(request)
    logger.warning(
        "API command rejected",
        extra={
            "correlation_id": correlation_id,
            "error_code": exc.code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        },
    )
    body = ErrorResponse(
        error=ErrorBody(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            correlation_id=correlation_id,
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(mode="json"),
        headers={"X-Correlation-ID": correlation_id},
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = request_correlation_id(request)
    logger.exception(
        "Unhandled API error",
        exc_info=exc,
        extra={
            "correlation_id": correlation_id,
            "error_code": "internal_error",
            "status_code": 500,
            "path": request.url.path,
            "method": request.method,
        },
    )
    body = ErrorResponse(
        error=ErrorBody(
            code="internal_error",
            message="An unexpected internal error occurred",
            correlation_id=correlation_id,
        )
    )
    return JSONResponse(
        status_code=500,
        content=body.model_dump(mode="json"),
        headers={"X-Correlation-ID": correlation_id},
    )
