import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from runscope_api.api.auth import router as auth_router
from runscope_api.api.experiments import router as experiments_router
from runscope_api.api.health import router as health_router
from runscope_api.api.projects import router as projects_router
from runscope_api.api.runs import router as runs_router
from runscope_api.api.workers import router as workers_router
from runscope_api.config import get_settings
from runscope_api.errors import AppError, app_error_handler, unexpected_error_handler
from runscope_api.logging import configure_logging
from runscope_api.metrics import MetricsMiddleware
from runscope_api.middleware import CorrelationIdMiddleware
from runscope_api.outbox import run_outbox_dispatcher


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    dispatcher = (
        asyncio.create_task(run_outbox_dispatcher(settings))
        if settings.outbox_dispatcher_enabled
        else None
    )
    try:
        yield
    finally:
        if dispatcher:
            dispatcher.cancel()
            with suppress(asyncio.CancelledError):
                await dispatcher


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="RunScope API",
        version="0.1.0",
        description="Control plane for trusted CPU-based machine-learning runs.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unexpected_error_handler)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(experiments_router, prefix="/api/v1")
    app.include_router(runs_router, prefix="/api/v1")
    app.include_router(workers_router, prefix="/api/v1")
    return app


app = create_app()
