"""API routes for weather endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi_cache.decorator import cache
from loguru import logger

from ..core.config import settings
from ..models.weather import WeatherResponse
from ..services.weather import weather_service

router = APIRouter()


def _normalize_coordinate_params(
    lat: float | None,
    latitude: float | None,
    lon: float | None,
    longitude: float | None,
) -> tuple[float, float]:
    """Normalize and validate coordinate query parameters.

    Handles both `lat`/`lon` and `latitude`/`longitude` parameter names.
    Precedence: if both names are provided, use the shorter version (`lat`, `lon`).
    Returns 400 if both names are provided with conflicting values.

    Args:
        lat: Latitude (short form)
        latitude: Latitude (long form)
        lon: Longitude (short form)
        longitude: Longitude (long form)

    Returns:
        Tuple of (latitude, longitude)

    Raises:
        HTTPException: If parameters are missing or conflicting

    Example:
        >>> _normalize_coordinate_params(52.52, None, 13.41, None)
        (52.52, 13.41)
        >>> _normalize_coordinate_params(None, 52.52, None, 13.41)
        (52.52, 13.41)
    """
    # Determine which latitude to use
    if lat is not None and latitude is not None:
        if lat != latitude:
            raise HTTPException(
                status_code=400,
                detail={"error": "Conflicting latitude values provided (lat and latitude)"},
            )
        final_lat = lat
    elif lat is not None:
        final_lat = lat
    elif latitude is not None:
        final_lat = latitude
    else:
        raise HTTPException(
            status_code=400,
            detail={"error": "Latitude parameter required (lat or latitude)"},
        )

    # Determine which longitude to use
    if lon is not None and longitude is not None:
        if lon != longitude:
            raise HTTPException(
                status_code=400,
                detail={"error": "Conflicting longitude values provided (lon and longitude)"},
            )
        final_lon = lon
    elif lon is not None:
        final_lon = lon
    elif longitude is not None:
        final_lon = longitude
    else:
        raise HTTPException(
            status_code=400,
            detail={"error": "Longitude parameter required (lon or longitude)"},
        )

    return final_lat, final_lon


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
                    "example": {"error": "Latitude parameter required (lat or latitude)"}
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
                    "example": {"error": "Gateway timeout - upstream API did not respond in time"}
                }
            },
        },
    },
)
@cache(expire=settings.CACHE_TTL)
async def get_current_weather(
    lat: Annotated[
        float | None,
        Query(
            description="Latitude in decimal degrees (-90 to 90)",
            ge=-90.0,
            le=90.0,
            examples=[52.52],
        ),
    ] = None,
    latitude: Annotated[
        float | None,
        Query(
            description="Latitude in decimal degrees (-90 to 90) - alternative to 'lat'",
            ge=-90.0,
            le=90.0,
            examples=[52.52],
        ),
    ] = None,
    lon: Annotated[
        float | None,
        Query(
            description="Longitude in decimal degrees (-180 to 180)",
            ge=-180.0,
            le=180.0,
            examples=[13.41],
        ),
    ] = None,
    longitude: Annotated[
        float | None,
        Query(
            description="Longitude in decimal degrees (-180 to 180) - alternative to 'lon'",
            ge=-180.0,
            le=180.0,
            examples=[13.41],
        ),
    ] = None,
) -> WeatherResponse:
    """Get current weather conditions for specified coordinates.

    Fetches data from Open-Meteo API and returns normalized temperature and wind speed.
    Results are cached for 60 seconds (configurable) to reduce API calls.

    Query parameters support both short (`lat`, `lon`) and long (`latitude`, `longitude`) forms.
    If both forms are provided, the short form takes precedence unless values conflict.

    Args:
        lat: Latitude in decimal degrees (-90 to 90)
        latitude: Alternative latitude parameter
        lon: Longitude in decimal degrees (-180 to 180)
        longitude: Alternative longitude parameter

    Returns:
        Current weather conditions with location, temperature, wind speed, and retrieval time

    Raises:
        HTTPException: 400 for invalid parameters, 502 for upstream errors, 504 for timeouts

    Example:
        >>> # GET /v1/current?lat=52.52&lon=13.41
        >>> # Returns: {"location": {"lat": 52.52, "lon": 13.41}, ...}
    """
    # Normalize and validate parameters
    final_lat, final_lon = _normalize_coordinate_params(lat, latitude, lon, longitude)

    logger.info(
        "Weather request received",
        # Note: Coordinates are logged here for debugging, but not in normal operation
        # to avoid PII concerns (as per decisions.md)
    )

    # Fetch weather (with caching and request coalescing)
    return await weather_service.get_current_weather(final_lat, final_lon)
