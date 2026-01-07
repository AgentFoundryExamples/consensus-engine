# Copyright 2025 John Brosnihan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Main FastAPI application factory.

This module creates and configures the FastAPI application with
dependency injection, middleware, and routes.
"""

import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from consensus_engine.api.routes import expand, health, review
from consensus_engine.config import get_settings
from consensus_engine.config.logging import get_logger, setup_logging
from consensus_engine.exceptions import (
    ConsensusEngineError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
)

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
    app.state.start_time = time.time()
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

    # Register middleware
    @app.middleware("http")
    async def logging_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Middleware to log requests with request IDs.

        Adds a unique request_id to each request and logs request/response
        information without storing full payloads.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler in the chain

        Returns:
            HTTP response
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log incoming request
        start_time = time.time()
        logger.info(
            "Incoming request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )

        # Process request
        response = await call_next(request)

        # Log response
        elapsed_time = time.time() - start_time
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "elapsed_time": f"{elapsed_time:.3f}s",
            },
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    # Register exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors (422).

        Args:
            request: The request that caused the error
            exc: The validation error

        Returns:
            JSON response with validation error details
        """
        request_id = getattr(request.state, "request_id", "unknown")

        # Convert error details to JSON-serializable format
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "type": error.get("type"),
                    "loc": list(error.get("loc", [])),
                    "msg": str(error.get("msg", "")),
                    "input": str(error.get("input", ""))[:100],  # Truncate long inputs
                }
            )

        logger.warning(
            "Validation error",
            extra={
                "request_id": request_id,
                "errors": errors,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": errors,
                "request_id": request_id,
            },
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Handle Pydantic ValidationError (422).

        Args:
            request: The request that caused the error
            exc: The validation error

        Returns:
            JSON response with validation error details
        """
        request_id = getattr(request.state, "request_id", "unknown")

        # Convert error details to JSON-serializable format
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "type": error.get("type"),
                    "loc": list(error.get("loc", [])),
                    "msg": str(error.get("msg", "")),
                    "input": str(error.get("input", ""))[:100],  # Truncate long inputs
                }
            )

        logger.warning(
            "Pydantic validation error",
            extra={
                "request_id": request_id,
                "errors": errors,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": errors,
                "request_id": request_id,
            },
        )

    @app.exception_handler(ConsensusEngineError)
    async def consensus_engine_exception_handler(
        request: Request, exc: ConsensusEngineError
    ) -> JSONResponse:
        """Handle domain exceptions with proper status codes.

        Args:
            request: The request that caused the error
            exc: The domain exception

        Returns:
            JSON response with error details
        """
        request_id = getattr(request.state, "request_id", "unknown")

        # Determine status code based on error type
        if isinstance(exc, LLMAuthenticationError):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(exc, LLMRateLimitError | LLMTimeoutError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        # Use appropriate log level based on status code
        log_level = "warning" if status_code < 500 else "error"
        getattr(logger, log_level)(
            "Domain exception",
            extra={
                "request_id": request_id,
                "code": exc.code,
                "message": exc.message,
            },
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions (500).

        Args:
            request: The request that caused the error
            exc: The exception

        Returns:
            JSON response with sanitized error details
        """
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "Unexpected exception",
            extra={"request_id": request_id},
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {},
                "request_id": request_id,
            },
        )

    # Register routers
    app.include_router(expand.router)
    app.include_router(health.router)
    app.include_router(review.router)

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
