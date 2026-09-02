"""FastAPI application entrypoint.

Run locally (outside docker):
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware

settings = get_settings()
configure_logging(debug=settings.debug)
logger = get_logger("pulse.api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("startup", environment=settings.environment, prefix=settings.api_v1_prefix)
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        summary="AI-powered artwork preparation for DTF printing.",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    # Liveness probe (unversioned, no side effects) for load balancers / k8s.
    @app.get("/health", tags=["meta"], include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
