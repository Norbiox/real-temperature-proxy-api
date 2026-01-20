"""Weather service with caching and request coalescing."""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from loguru import logger

from ..core.config import settings
from ..models.weather import WeatherResponse
from ..services.openmeteo import (
    OpenMeteoClient,
    OpenMeteoClientError,
    OpenMeteoError,
    OpenMeteoNetworkError,
    OpenMeteoTimeoutError,
    OpenMeteoUpstreamError,
)


class RequestCoalescer:
    """Implements request coalescing to prevent thundering herd.

    When multiple concurrent requests arrive for the same coordinates (cache miss),
    the first request fetches from upstream while others wait for the result.
    Limits concurrent waiters per coordinate to prevent unbounded memory growth.

    Example:
        >>> coalescer = RequestCoalescer()
        >>> # Multiple concurrent requests for same coordinates
        >>> # Only one upstream fetch occurs
    """

    def __init__(self, max_waiters: int = 100):
        """Initialize request coalescer.

        Args:
            max_waiters: Maximum concurrent waiters per coordinate
        """
        self._locks: dict[tuple[float, float], asyncio.Lock] = defaultdict(asyncio.Lock)
        self._events: dict[tuple[float, float], asyncio.Event] = {}
        self._results: dict[tuple[float, float], WeatherResponse | Exception] = {}
        self._waiter_counts: dict[tuple[float, float], int] = defaultdict(int)
        self._max_waiters = max_waiters

    async def coalesce(
        self,
        latitude: float,
        longitude: float,
        fetch_func,
    ) -> WeatherResponse:
        """Coalesce requests for the same coordinates.

        Args:
            latitude: Rounded latitude (cache key)
            longitude: Rounded longitude (cache key)
            fetch_func: Async function to fetch data if needed

        Returns:
            Weather response

        Raises:
            HTTPException: If too many concurrent waiters or fetch fails
        """
        key = (latitude, longitude)

        async with self._locks[key]:
            # Check if already fetching
            if key in self._events:
                # Check waiter limit
                if self._waiter_counts[key] >= self._max_waiters:
                    logger.warning(
                        "Request coalescing limit exceeded",
                        waiters=self._waiter_counts[key],
                        max_waiters=self._max_waiters,
                    )
                    raise HTTPException(
                        status_code=503,
                        detail={"error": "Service temporarily unavailable - too many concurrent requests"},
                    )

                # Wait for existing fetch to complete
                self._waiter_counts[key] += 1
                logger.debug(
                    "Request coalescing - waiting for existing fetch",
                    waiters=self._waiter_counts[key],
                )

        # Wait outside the lock
        if key in self._events:
            try:
                await self._events[key].wait()

                # Get result
                result = self._results.get(key)
                if isinstance(result, Exception):
                    raise result
                elif result is None:
                    # Should not happen, but handle gracefully
                    raise HTTPException(
                        status_code=500,
                        detail={"error": "Internal server error"},
                    )
                return result

            finally:
                async with self._locks[key]:
                    self._waiter_counts[key] -= 1

                    # Clean up if last waiter
                    if self._waiter_counts[key] == 0:
                        self._events.pop(key, None)
                        self._results.pop(key, None)
                        self._waiter_counts.pop(key, None)
                        self._locks.pop(key, None)

        # We're the first request - do the fetch
        async with self._locks[key]:
            # Double-check after acquiring lock
            if key in self._events:
                # Another request became first while we waited
                self._waiter_counts[key] += 1

            else:
                # We're definitely first - create event
                self._events[key] = asyncio.Event()

        # Check if we're now a waiter
        if self._waiter_counts[key] > 0:
            # Recursive call to wait
            return await self.coalesce(latitude, longitude, fetch_func)

        # Do the actual fetch
        try:
            logger.debug("Request coalescing - fetching from upstream")
            result = await fetch_func()
            self._results[key] = result

            # Notify waiters
            self._events[key].set()

            return result

        except Exception as e:
            # Store exception for waiters
            self._results[key] = e

            # Notify waiters
            if key in self._events:
                self._events[key].set()

            raise


class WeatherService:
    """Weather service orchestrating Open-Meteo client, caching, and request coalescing.

    This service coordinates:
    - Fetching data from Open-Meteo API
    - Request coalescing to prevent thundering herd
    - Error handling and HTTP exception mapping

    Note: Caching is handled at the FastAPI route level using fastapi-cache2 decorators.

    Example:
        >>> async def example():
        ...     service = WeatherService()
        ...     response = await service.get_current_weather(52.52, 13.41)
        ...     return response.current.temperatureC
    """

    def __init__(self):
        """Initialize weather service."""
        self._coalescer = RequestCoalescer(max_waiters=settings.REQUEST_COALESCE_LIMIT)

    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> WeatherResponse:
        """Get current weather for coordinates.

        Implements request coalescing and error handling.
        Returns cached data if available (handled by FastAPI route decorator).

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            Normalized weather response

        Raises:
            HTTPException: With appropriate status code and error message

        Example:
            >>> async def example():
            ...     service = WeatherService()
            ...     response = await service.get_current_weather(52.52, 13.41)
            ...     assert response.source == "open-meteo"
        """
        # Round coordinates for cache key consistency
        rounded_lat = round(latitude, 4)
        rounded_lon = round(longitude, 4)

        # Define fetch function for coalescer
        async def fetch():
            async with OpenMeteoClient() as client:
                return await client.get_current_weather(latitude, longitude)

        try:
            # Use request coalescing
            return await self._coalescer.coalesce(
                rounded_lat,
                rounded_lon,
                fetch,
            )

        except OpenMeteoTimeoutError as e:
            logger.warning("Upstream API timeout")
            raise HTTPException(
                status_code=504,
                detail={"error": "Gateway timeout - upstream API did not respond in time"},
            ) from e

        except OpenMeteoUpstreamError as e:
            logger.warning("Upstream API error (5xx)")
            raise HTTPException(
                status_code=502,
                detail={"error": "Bad gateway - upstream API error"},
            ) from e

        except (OpenMeteoClientError, OpenMeteoNetworkError) as e:
            logger.warning("Upstream API client/network error")
            raise HTTPException(
                status_code=502,
                detail={"error": "Bad gateway - upstream API error"},
            ) from e

        except OpenMeteoError as e:
            logger.error("Unexpected Open-Meteo error", error=str(e))
            raise HTTPException(
                status_code=502,
                detail={"error": "Bad gateway - upstream API error"},
            ) from e

        except HTTPException:
            # Re-raise HTTPExceptions (from coalescer)
            raise

        except Exception as e:
            logger.exception("Unexpected error in weather service")
            raise HTTPException(
                status_code=500,
                detail={"error": "Internal server error"},
            ) from e


# Global service instance
weather_service = WeatherService()
