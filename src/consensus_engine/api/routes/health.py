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
"""Health check endpoint router.

This module implements the GET /health endpoint that reports service
status, configuration metadata, and uptime without exposing secrets.
"""

import time

from fastapi import APIRouter, Depends, Request

from consensus_engine.config import Settings, get_settings
from consensus_engine.config.logging import get_logger
from consensus_engine.schemas.requests import HealthResponse

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description=(
        "Returns service health status, configuration metadata, and uptime. "
        "Performs configuration sanity checks without exposing secrets. "
        "Status can be 'healthy', 'degraded', or 'unhealthy'."
    ),
    responses={
        200: {
            "description": "Service is healthy or degraded",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "environment": "production",
                        "debug": False,
                        "model": "gpt-5.1",
                        "temperature": 0.7,
                        "uptime_seconds": 3600.5,
                        "config_status": "ok",
                    }
                }
            },
        }
    },
)
async def health_check(
    request: Request, settings: Settings = Depends(get_settings)
) -> HealthResponse:
    """Health check endpoint with configuration metadata.

    Performs sanity checks on configuration and reports service status.
    Degrades gracefully if OpenAI configuration has issues.

    Args:
        request: The incoming request (to access app state)
        settings: Application settings injected via dependency

    Returns:
        HealthResponse with status, config metadata, and uptime
    """
    # Calculate uptime from app state
    start_time = getattr(request.app.state, "start_time", time.time())
    uptime_seconds = time.time() - start_time

    # Perform configuration sanity checks
    config_status = "ok"
    health_status = "healthy"

    # Check if API key looks valid (but don't expose it)
    if not settings.openai_api_key or len(settings.openai_api_key) < 10:
        config_status = "warning"
        health_status = "degraded"
        logger.warning("Health check detected invalid API key configuration")

    # Check temperature is in recommended range
    if settings.temperature < 0.5 or settings.temperature > 0.7:
        config_status = "warning" if config_status == "ok" else config_status
        logger.debug(f"Temperature {settings.temperature} is outside recommended range [0.5, 0.7]")

    # Build response
    response = HealthResponse(
        status=health_status,
        environment=settings.env.value,
        debug=settings.debug,
        model=settings.openai_model,
        temperature=settings.temperature,
        uptime_seconds=uptime_seconds,
        config_status=config_status,
    )

    logger.debug(
        "Health check completed",
        extra={
            "status": health_status,
            "config_status": config_status,
            "uptime_seconds": uptime_seconds,
        },
    )

    return response
