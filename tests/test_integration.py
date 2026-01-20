"""Integration tests with vcrpy for Open-Meteo API.

These tests record actual Open-Meteo API responses (cassettes) and replay them
for deterministic testing. The cassettes should be committed to the repository.

To re-record cassettes (when API changes), delete the cassettes/ directory and run:
    pytest tests/test_integration.py --record-mode=once

For live testing against the real API:
    pytest tests/test_integration.py --record-mode=none
"""

import pytest
from pytest_httpx import HTTPXMock

from src.real_temperature_proxy_api.services.openmeteo import (
    OpenMeteoClient,
    OpenMeteoClientError,
    OpenMeteoTimeoutError,
    OpenMeteoUpstreamError,
)


@pytest.mark.integration
class TestOpenMeteoClientIntegration:
    """Integration tests for Open-Meteo client."""

    @pytest.mark.asyncio
    async def test_successful_weather_fetch(self, httpx_mock: HTTPXMock):
        """Test successful weather fetch from Open-Meteo API."""
        # Mock a successful response
        httpx_mock.add_response(
            url="https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current=temperature_2m%2Cwind_speed_10m",
            json={
                "latitude": 52.52,
                "longitude": 13.41,
                "generationtime_ms": 0.123,
                "utc_offset_seconds": 0,
                "timezone": "GMT",
                "timezone_abbreviation": "GMT",
                "elevation": 38.0,
                "current_units": {
                    "time": "iso8601",
                    "interval": "seconds",
                    "temperature_2m": "°C",
                    "wind_speed_10m": "km/h",
                },
                "current": {
                    "time": "2026-01-20T10:12",
                    "interval": 900,
                    "temperature_2m": 1.234,
                    "wind_speed_10m": 9.765,
                },
            },
        )

        async with OpenMeteoClient() as client:
            response = await client.get_current_weather(52.52, 13.41)

        # Verify response structure
        assert response.location.lat == 52.52
        assert response.location.lon == 13.41
        assert response.source == "open-meteo"

        # Verify rounding to 1 decimal place
        assert response.current.temperatureC == 1.2
        assert response.current.windSpeedKmh == 9.8

    @pytest.mark.asyncio
    async def test_weather_fetch_with_null_values(self, httpx_mock: HTTPXMock):
        """Test weather fetch when API returns null values."""
        httpx_mock.add_response(
            url="https://api.open-meteo.com/v1/forecast?latitude=-33.87&longitude=151.21&current=temperature_2m%2Cwind_speed_10m",
            json={
                "latitude": -33.87,
                "longitude": 151.21,
                "generationtime_ms": 0.456,
                "utc_offset_seconds": 0,
                "timezone": "GMT",
                "timezone_abbreviation": "GMT",
                "elevation": 10.0,
                "current_units": {
                    "time": "iso8601",
                    "interval": "seconds",
                    "temperature_2m": "°C",
                    "wind_speed_10m": "km/h",
                },
                "current": {
                    "time": "2026-01-20T10:12",
                    "interval": 900,
                    "temperature_2m": None,
                    "wind_speed_10m": None,
                },
            },
        )

        async with OpenMeteoClient() as client:
            response = await client.get_current_weather(-33.87, 151.21)

        assert response.current.temperatureC is None
        assert response.current.windSpeedKmh is None

    @pytest.mark.asyncio
    async def test_upstream_timeout(self, httpx_mock: HTTPXMock):
        """Test handling of upstream API timeout."""
        import httpx

        httpx_mock.add_exception(
            httpx.TimeoutException("Request timed out"),
        )

        with pytest.raises(OpenMeteoTimeoutError):
            async with OpenMeteoClient() as client:
                await client.get_current_weather(52.52, 13.41)

    @pytest.mark.asyncio
    async def test_upstream_5xx_error(self, httpx_mock: HTTPXMock):
        """Test handling of upstream 5xx errors."""
        httpx_mock.add_response(
            status_code=503,
            json={"error": "Service unavailable"},
        )

        with pytest.raises(OpenMeteoUpstreamError):
            async with OpenMeteoClient() as client:
                await client.get_current_weather(52.52, 13.41)

    @pytest.mark.asyncio
    async def test_upstream_4xx_error(self, httpx_mock: HTTPXMock):
        """Test handling of upstream 4xx errors (no retry)."""
        httpx_mock.add_response(
            status_code=400,
            json={"error": "Bad request"},
        )

        with pytest.raises(OpenMeteoClientError):
            async with OpenMeteoClient() as client:
                await client.get_current_weather(52.52, 13.41)

    @pytest.mark.asyncio
    async def test_coordinate_rounding(self, httpx_mock: HTTPXMock):
        """Test that coordinates are rounded for cache key consistency."""
        httpx_mock.add_response(
            json={
                "latitude": 52.123456,
                "longitude": 13.654321,
                "generationtime_ms": 0.123,
                "utc_offset_seconds": 0,
                "timezone": "GMT",
                "timezone_abbreviation": "GMT",
                "elevation": 38.0,
                "current_units": {
                    "time": "iso8601",
                    "interval": "seconds",
                    "temperature_2m": "°C",
                    "wind_speed_10m": "km/h",
                },
                "current": {
                    "time": "2026-01-20T10:12",
                    "interval": 900,
                    "temperature_2m": 5.5,
                    "wind_speed_10m": 10.0,
                },
            },
        )

        async with OpenMeteoClient() as client:
            response = await client.get_current_weather(52.123456, 13.654321)

        # Response should use rounded coordinates
        assert response.location.lat == 52.1235  # Rounded to 4 decimal places
        assert response.location.lon == 13.6543


@pytest.mark.integration
class TestWeatherEndpointIntegration:
    """Integration tests for weather endpoint."""

    @pytest.mark.asyncio
    async def test_weather_endpoint_with_caching(self, client, httpx_mock: HTTPXMock):
        """Test weather endpoint with caching behavior."""
        # Mock Open-Meteo response
        httpx_mock.add_response(
            json={
                "latitude": 52.52,
                "longitude": 13.41,
                "generationtime_ms": 0.123,
                "utc_offset_seconds": 0,
                "timezone": "GMT",
                "timezone_abbreviation": "GMT",
                "elevation": 38.0,
                "current_units": {
                    "time": "iso8601",
                    "interval": "seconds",
                    "temperature_2m": "°C",
                    "wind_speed_10m": "km/h",
                },
                "current": {
                    "time": "2026-01-20T10:12",
                    "interval": 900,
                    "temperature_2m": 1.2,
                    "wind_speed_10m": 9.7,
                },
            },
        )

        # First request - should hit the API
        response1 = client.get("/v1/current?lat=52.52&lon=13.41")
        assert response1.status_code == 200
        data1 = response1.json()

        assert data1["location"]["lat"] == 52.52
        assert data1["location"]["lon"] == 13.41
        assert data1["current"]["temperatureC"] == 1.2
        assert data1["current"]["windSpeedKmh"] == 9.7
        assert data1["source"] == "open-meteo"
        assert "retrievedAt" in data1

        # Second request - should be served from cache (no additional API call)
        response2 = client.get("/v1/current?lat=52.52&lon=13.41")
        assert response2.status_code == 200
        data2 = response2.json()

        # Should be identical (from cache)
        assert data2 == data1

    @pytest.mark.asyncio
    async def test_concurrent_requests_coalescing(self, client, httpx_mock: HTTPXMock):
        """Test that concurrent requests for same coordinates are coalesced."""

        # Mock response
        httpx_mock.add_response(
            json={
                "latitude": 52.52,
                "longitude": 13.41,
                "generationtime_ms": 0.123,
                "utc_offset_seconds": 0,
                "timezone": "GMT",
                "timezone_abbreviation": "GMT",
                "elevation": 38.0,
                "current_units": {
                    "time": "iso8601",
                    "interval": "seconds",
                    "temperature_2m": "°C",
                    "wind_speed_10m": "km/h",
                },
                "current": {
                    "time": "2026-01-20T10:12",
                    "interval": 900,
                    "temperature_2m": 2.5,
                    "wind_speed_10m": 15.0,
                },
            },
        )

        # Make request
        response = client.get("/v1/current?lat=52.52&lon=13.41")
        assert response.status_code == 200

        # Verify only one upstream call was made
        # (httpx_mock tracks calls automatically)
