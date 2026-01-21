"""Tests for Pydantic models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.real_temperature_proxy_api.models.weather import (
    CurrentWeatherModel,
    LocationModel,
    OpenMeteoResponse,
    WeatherResponse,
)


class TestLocationModel:
    """Test LocationModel validation."""

    def test_valid_coordinates(self):
        """Test that valid coordinates are accepted."""
        loc = LocationModel(lat=52.52, lon=13.41)
        assert loc.lat == 52.52
        assert loc.lon == 13.41

        # Edge cases
        LocationModel(lat=90.0, lon=180.0)
        LocationModel(lat=-90.0, lon=-180.0)
        LocationModel(lat=0.0, lon=0.0)

    def test_invalid_coordinates(self):
        """Test that invalid coordinates are rejected."""
        # Latitude out of range
        with pytest.raises(ValidationError):
            LocationModel(lat=91.0, lon=0.0)

        with pytest.raises(ValidationError):
            LocationModel(lat=-91.0, lon=0.0)

        # Longitude out of range
        with pytest.raises(ValidationError):
            LocationModel(lat=0.0, lon=181.0)

        with pytest.raises(ValidationError):
            LocationModel(lat=0.0, lon=-181.0)

    def test_coordinate_precision_validation(self):
        """Test that coordinate precision is validated (max 6 decimal places)."""
        # Valid precision
        LocationModel(lat=52.123456, lon=13.123456)
        LocationModel(lat=52.1, lon=13.1)
        LocationModel(lat=52.0, lon=13.0)

        # Invalid precision (more than 6 decimal places)
        with pytest.raises(
            ValidationError, match="precision must not exceed 6 decimal places"
        ):
            LocationModel(lat=52.1234567, lon=13.0)

        with pytest.raises(
            ValidationError, match="precision must not exceed 6 decimal places"
        ):
            LocationModel(lat=52.0, lon=13.12345678)


class TestCurrentWeatherModel:
    """Test CurrentWeatherModel."""

    def test_valid_weather_data(self):
        """Test that valid weather data is accepted."""
        weather = CurrentWeatherModel(temperatureC=1.2, windSpeedKmh=9.7)
        assert weather.temperatureC == 1.2
        assert weather.windSpeedKmh == 9.7

    def test_null_values(self):
        """Test that null values are accepted."""
        weather = CurrentWeatherModel(temperatureC=None, windSpeedKmh=None)
        assert weather.temperatureC is None
        assert weather.windSpeedKmh is None

        weather = CurrentWeatherModel(temperatureC=1.2, windSpeedKmh=None)
        assert weather.temperatureC == 1.2
        assert weather.windSpeedKmh is None


class TestWeatherResponse:
    """Test WeatherResponse model."""

    def test_valid_response(self):
        """Test that valid weather response is created correctly."""
        response = WeatherResponse(
            location=LocationModel(lat=52.52, lon=13.41),
            current=CurrentWeatherModel(temperatureC=1.2, windSpeedKmh=9.7),
            source="open-meteo",
            retrievedAt=datetime(2026, 1, 11, 10, 12, 54, tzinfo=timezone.utc),
        )

        assert response.location.lat == 52.52
        assert response.location.lon == 13.41
        assert response.current.temperatureC == 1.2
        assert response.current.windSpeedKmh == 9.7
        assert response.source == "open-meteo"
        assert response.retrievedAt.year == 2026

    def test_default_source(self):
        """Test that source defaults to 'open-meteo'."""
        response = WeatherResponse(
            location=LocationModel(lat=52.52, lon=13.41),
            current=CurrentWeatherModel(temperatureC=1.2, windSpeedKmh=9.7),
            retrievedAt=datetime.now(timezone.utc),
        )

        assert response.source == "open-meteo"

    def test_json_serialization(self):
        """Test that response can be serialized to JSON."""
        response = WeatherResponse(
            location=LocationModel(lat=52.52, lon=13.41),
            current=CurrentWeatherModel(temperatureC=1.2, windSpeedKmh=9.7),
            source="open-meteo",
            retrievedAt=datetime(2026, 1, 11, 10, 12, 54, tzinfo=timezone.utc),
        )

        json_data = response.model_dump(mode="json")

        assert json_data["location"]["lat"] == 52.52
        assert json_data["location"]["lon"] == 13.41
        assert json_data["current"]["temperatureC"] == 1.2
        assert json_data["current"]["windSpeedKmh"] == 9.7
        assert json_data["source"] == "open-meteo"


class TestOpenMeteoModels:
    """Test Open-Meteo API response models."""

    def test_open_meteo_response_parsing(self):
        """Test that Open-Meteo response can be parsed."""
        data = {
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
                "time": "2026-01-11T10:12",
                "interval": 900,
                "temperature_2m": 1.2,
                "wind_speed_10m": 9.7,
            },
        }

        response = OpenMeteoResponse(**data)

        assert response.latitude == 52.52
        assert response.longitude == 13.41
        assert response.current.temperature_2m == 1.2
        assert response.current.wind_speed_10m == 9.7

    def test_open_meteo_response_with_null_values(self):
        """Test that Open-Meteo response handles null values."""
        data = {
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
                "time": "2026-01-11T10:12",
                "interval": 900,
                "temperature_2m": None,
                "wind_speed_10m": None,
            },
        }

        response = OpenMeteoResponse(**data)

        assert response.current.temperature_2m is None
        assert response.current.wind_speed_10m is None
