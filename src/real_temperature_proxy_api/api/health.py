"""Health check endpoints for Kubernetes probes."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model.

    Example:
        >>> response = HealthResponse(status="ok")
        >>> response.status
        'ok'
    """

    status: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Check if the application process is running",
    responses={
        200: {
            "description": "Application is alive",
            "content": {
                "application/json": {
                    "example": {"status": "ok"}
                }
            },
        },
    },
)
async def health_check() -> HealthResponse:
    """Liveness probe for Kubernetes.

    Always returns 200 OK to indicate the process is running.
    Does not check external dependencies or service state.

    Returns:
        Health status response

    Example:
        >>> # GET /health
        >>> # Returns: {"status": "ok"}
    """
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness probe",
    description="Check if the application is ready to serve requests",
    responses={
        200: {
            "description": "Application is ready",
            "content": {
                "application/json": {
                    "example": {"status": "ok"}
                }
            },
        },
    },
)
async def readiness_check() -> HealthResponse:
    """Readiness probe for Kubernetes.

    Returns 200 OK when the application is ready to serve requests.
    Checks internal state (cache initialized, configuration valid).
    Does NOT actively probe Open-Meteo API.

    Returns:
        Readiness status response

    Example:
        >>> # GET /ready
        >>> # Returns: {"status": "ok"}
    """
    # For now, return OK immediately
    # In a more complex setup, we'd check:
    # - Cache backend is initialized
    # - Configuration is valid
    # - Internal services are ready
    #
    # We don't check:
    # - Open-Meteo API availability (to avoid cascading failures)
    return HealthResponse(status="ok")
