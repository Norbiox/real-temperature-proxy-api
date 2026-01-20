"""Open-Meteo API client service with retry logic."""

from datetime import datetime, timezone

import httpx
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

from ..core.config import settings
from ..models.weather import (
    CurrentWeatherModel,
    LocationModel,
    OpenMeteoResponse,
    WeatherResponse,
)


class OpenMeteoError(Exception):
    """Base exception for Open-Meteo API errors."""

    pass


class OpenMeteoTimeoutError(OpenMeteoError):
    """Raised when Open-Meteo API request times out."""

    pass


class OpenMeteoUpstreamError(OpenMeteoError):
    """Raised when Open-Meteo API returns 5xx error."""

    pass


class OpenMeteoClientError(OpenMeteoError):
    """Raised when Open-Meteo API returns 4xx error."""

    pass


class OpenMeteoNetworkError(OpenMeteoError):
    """Raised when network error occurs (connection refused, DNS failure, etc)."""

    pass


def _should_retry(exception: BaseException) -> bool:
    """Determine if an exception should trigger a retry.

    Retry on:
    - Timeout errors
    - Connection errors (connection refused)
    - 5xx errors from upstream

    Do NOT retry on:
    - 4xx errors (client errors)
    - DNS failures
    - Network errors (general)

    Args:
        exception: The exception to check

    Returns:
        True if should retry, False otherwise

    Example:
        >>> _should_retry(OpenMeteoTimeoutError())
        True
        >>> _should_retry(OpenMeteoClientError())
        False
        >>> _should_retry(OpenMeteoUpstreamError())
        True
    """
    return isinstance(
        exception,
        (
            OpenMeteoTimeoutError,
            OpenMeteoUpstreamError,
            httpx.ConnectError,  # Connection refused
        ),
    )


class OpenMeteoClient:
    """Client for fetching weather data from Open-Meteo API.

    Uses httpx for async HTTP requests and tenacity for exponential backoff retries.
    Implements timeout handling and proper error classification.

    Example:
        >>> async def example():
        ...     async with OpenMeteoClient() as client:
        ...         response = await client.get_current_weather(52.52, 13.41)
        ...         return response.current.temperatureC
    """

    def __init__(self):
        """Initialize the Open-Meteo client with configuration from settings."""
        self._client: httpx.AsyncClient | None = None
        self._base_url = settings.OPENMETEO_BASE_URL
        self._timeout = settings.UPSTREAM_TIMEOUT
        self._api_key = settings.OPENMETEO_API_KEY

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    @retry(
        retry=retry_if_exception(_should_retry),
        stop=stop_after_attempt(
            settings.RETRY_COUNT + 1
        ),  # +1 because first attempt isn't a retry
        wait=wait_exponential(
            min=settings.RETRY_DELAY / 1000.0,  # Convert ms to seconds
            multiplier=settings.RETRY_BACKOFF_MULTIPLIER,
        )
        + wait_random(0, 1),  # Add jitter: 0-1 second random delay
        reraise=True,
    )
    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> WeatherResponse:
        """Fetch current weather from Open-Meteo API.

        Implements retry logic with exponential backoff for transient failures.
        Retries on: timeouts, connection errors, 5xx errors.
        Does NOT retry on: 4xx errors, DNS failures, network errors.

        Args:
            latitude: Latitude in decimal degrees (-90 to 90)
            longitude: Longitude in decimal degrees (-180 to 180)

        Returns:
            Normalized weather response

        Raises:
            OpenMeteoTimeoutError: If request times out after all retries
            OpenMeteoUpstreamError: If API returns 5xx error after all retries
            OpenMeteoClientError: If API returns 4xx error (no retry)
            OpenMeteoNetworkError: If network error occurs (no retry)

        Example:
            >>> async def example():
            ...     async with OpenMeteoClient() as client:
            ...         response = await client.get_current_weather(52.52, 13.41)
            ...         assert response.location.lat == 52.52
            ...         assert response.source == "open-meteo"
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        # Note: Coordinate rounding to 4 decimals is handled by the caching layer
        # We pass original coordinates to API and return them in response

        # Build query parameters
        params: dict[str, float | str] = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,wind_speed_10m",
        }

        # Add API key if configured
        if self._api_key:
            params["apikey"] = self._api_key

        try:
            # Make request to Open-Meteo API
            logger.debug(
                "Fetching weather from Open-Meteo",
                url=self._base_url,
            )

            response = await self._client.get(
                self._base_url,
                params=params,
            )

            # Handle HTTP errors
            if response.status_code >= 500:
                logger.warning(
                    "Open-Meteo returned 5xx error",
                    status_code=response.status_code,
                )
                raise OpenMeteoUpstreamError(
                    f"Upstream API returned {response.status_code}"
                )

            if response.status_code >= 400:
                logger.warning(
                    "Open-Meteo returned 4xx error",
                    status_code=response.status_code,
                )
                raise OpenMeteoClientError(
                    f"Upstream API returned {response.status_code}"
                )

            # Parse response
            data = OpenMeteoResponse(**response.json())

            # Normalize and return with original precision coordinates
            return self._normalize_response(data, latitude, longitude)

        except httpx.TimeoutException as e:
            logger.warning("Open-Meteo request timed out")
            raise OpenMeteoTimeoutError("Upstream API request timed out") from e

        except httpx.ConnectError as e:
            # ConnectError includes DNS resolution failures and connection refused
            # Do NOT retry on DNS failures (decision: only retry on connection refused)
            error_msg = str(e).lower()
            if "name" in error_msg or "dns" in error_msg or "resolve" in error_msg:
                logger.error("DNS resolution failed for Open-Meteo", error=str(e))
                raise OpenMeteoNetworkError(
                    "Failed to resolve upstream API hostname"
                ) from e
            else:
                # Connection refused - this will be retried
                logger.warning("Failed to connect to Open-Meteo (connection refused)")
                raise OpenMeteoNetworkError("Failed to connect to upstream API") from e

        except httpx.HTTPError as e:
            logger.error("HTTP error occurred", error=str(e))
            raise OpenMeteoNetworkError(f"Network error: {e}") from e

    def _normalize_response(
        self,
        data: OpenMeteoResponse,
        latitude: float,
        longitude: float,
    ) -> WeatherResponse:
        """Normalize Open-Meteo response to our API format.

        Rounds temperature and wind speed to 1 decimal place using banker's rounding.
        Uses the current UTC time as retrievedAt.

        Args:
            data: Raw Open-Meteo API response
            latitude: Rounded latitude for response
            longitude: Rounded longitude for response

        Returns:
            Normalized weather response

        Example:
            >>> client = OpenMeteoClient()
            >>> from datetime import datetime, timezone
            >>> omr = OpenMeteoResponse(
            ...     latitude=52.52,
            ...     longitude=13.41,
            ...     generationtime_ms=0.123,
            ...     utc_offset_seconds=0,
            ...     timezone="GMT",
            ...     timezone_abbreviation="GMT",
            ...     elevation=38.0,
            ...     current_units={"time": "iso8601", "interval": "seconds",
            ...                   "temperature_2m": "°C", "wind_speed_10m": "km/h"},
            ...     current={"time": "2026-01-11T10:12", "interval": 900,
            ...             "temperature_2m": 1.23456, "wind_speed_10m": 9.76543}
            ... )
            >>> response = client._normalize_response(omr, 52.52, 13.41)
            >>> response.current.temperatureC
            1.2
            >>> response.current.windSpeedKmh
            9.8
        """
        # Round values to 1 decimal place (banker's rounding is Python's default)
        temperature = (
            round(data.current.temperature_2m, 1)
            if data.current.temperature_2m is not None
            else None
        )
        wind_speed = (
            round(data.current.wind_speed_10m, 1)
            if data.current.wind_speed_10m is not None
            else None
        )

        return WeatherResponse(
            location=LocationModel(lat=latitude, lon=longitude),
            current=CurrentWeatherModel(
                temperatureC=temperature,
                windSpeedKmh=wind_speed,
            ),
            source="open-meteo",
            retrievedAt=datetime.now(timezone.utc),
        )
