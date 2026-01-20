"""API routes for weather endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi_cache.decorator import cache
from loguru import logger

from ..core.config import settings
from ..models.weather import WeatherResponse
from ..services.weather import weather_service
from .dependencies import get_latitude_param, get_longitude_param

router = APIRouter()


@router.get(
    "/v1/current",
    response_model=WeatherResponse,
    summary="Get current weather conditions",
    description="Fetch current temperature and wind speed for specified coordinates from Open-Meteo API",
    responses={
        200: {
            "description": "Current weather conditions",
            "content": {
                "application/json": {
                    "example": {
                        "location": {"lat": 52.52, "lon": 13.41},
                        "current": {
                            "temperatureC": 1.2,
                            "windSpeedKmh": 9.7,
                        },
                        "source": "open-meteo",
                        "retrievedAt": "2026-01-11T10:12:54Z",
                    }
                }
            },
        },
        400: {
            "description": "Invalid coordinates or parameters",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Latitude parameter required (lat or latitude)"
                    }
                }
            },
        },
        502: {
            "description": "Upstream API error",
            "content": {
                "application/json": {
                    "example": {"error": "Bad gateway - upstream API error"}
                }
            },
        },
        504: {
            "description": "Upstream API timeout",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Gateway timeout - upstream API did not respond in time"
                    }
                }
            },
        },
    },
)
@cache(expire=settings.CACHE_TTL)
async def get_current_weather(
    latitude_param: Annotated[float | None, Depends(get_latitude_param)],
    longitude_param: Annotated[float | None, Depends(get_longitude_param)],
) -> WeatherResponse:
    """Get current weather conditions for specified coordinates.

    Fetches data from Open-Meteo API and returns normalized temperature and wind speed.
    Results are cached for 60 seconds (configurable) to reduce API calls.

    Query parameters are case-insensitive and support multiple forms:
    - Latitude: lat, latitude, LAT, Lat, LATITUDE, Latitude
    - Longitude: lon, longitude, LON, Lon, LONGITUDE, Longitude

    Args:
        latitude_param: Latitude from case-insensitive query parameter
        longitude_param: Longitude from case-insensitive query parameter

    Returns:
        Current weather conditions with location, temperature, wind speed, and retrieval time

    Raises:
        HTTPException: 400 for invalid parameters, 502 for upstream errors, 504 for timeouts

    Example:
        >>> # GET /v1/current?lat=52.52&lon=13.41
        >>> # GET /v1/current?LAT=52.52&LON=13.41  (case-insensitive)
        >>> # Returns: {"location": {"lat": 52.52, "lon": 13.41}, ...}
    """
    # Validate required parameters
    if latitude_param is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Latitude parameter required (lat or latitude)"},
        )

    if longitude_param is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Longitude parameter required (lon or longitude)"},
        )

    logger.info(
        "Weather request received",
        # Note: Coordinates are logged here for debugging, but not in normal operation
        # to avoid PII concerns (as per decisions.md)
    )

    # Fetch weather (with caching and request coalescing)
    return await weather_service.get_current_weather(latitude_param, longitude_param)
