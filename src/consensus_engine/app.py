"""Main FastAPI application factory.

This module creates and configures the FastAPI application with
dependency injection, middleware, and routes.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from consensus_engine.config import Settings, get_settings
from consensus_engine.config.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown.

    Args:
        app: FastAPI application instance

    Yields:
        Control back to the application during its lifecycle
    """
    # Startup
    settings = get_settings()
    setup_logging(settings)
    logger.info("Starting Consensus Engine API")
    logger.info(f"Environment: {settings.env.value}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.debug(f"Configuration: {settings.get_safe_dict()}")

    yield

    # Shutdown
    logger.info("Shutting down Consensus Engine API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Consensus Engine API",
        description="FastAPI backend with LLM integration for consensus building",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check(settings: Settings = Depends(get_settings)) -> dict:
        """Health check endpoint.

        Args:
            settings: Application settings injected via dependency

        Returns:
            Health status and configuration info
        """
        return {
            "status": "healthy",
            "environment": settings.env.value,
            "debug": settings.debug,
            "model": settings.openai_model,
        }

    # Root endpoint
    @app.get("/", tags=["root"])
    async def root() -> dict:
        """Root endpoint with API information.

        Returns:
            API welcome message and version
        """
        return {
            "message": "Consensus Engine API",
            "version": "0.1.0",
            "docs": "/docs",
        }

    return app


# Create app instance
app = create_app()
