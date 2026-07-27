from collections.abc import Awaitable, Callable
from contextvars import ContextVar, Token
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

correlation_id_context: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = request.headers.get("x-correlation-id") or str(uuid4())
        correlation_id = correlation_id[:128]
        request.state.correlation_id = correlation_id
        token: Token[str] = correlation_id_context.set(correlation_id)
        try:
            response = await call_next(request)
            response.headers["x-correlation-id"] = correlation_id
            return response
        finally:
            correlation_id_context.reset(token)
