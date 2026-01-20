"""Tests for configuration management."""

import pytest
from pydantic import ValidationError

from src.real_temperature_proxy_api.core.config import Settings


class TestSettings:
    """Test configuration settings."""

    def test_default_values(self):
        """Test that default values are loaded correctly."""
        settings = Settings()

        assert settings.UPSTREAM_TIMEOUT == 1.0
        assert settings.CACHE_TTL == 60
        assert settings.CACHE_MAX_SIZE == 10000
        assert settings.PORT == 8000
        assert settings.LOG_LEVEL == "INFO"
        assert settings.OPENMETEO_BASE_URL == "https://api.open-meteo.com/v1/forecast"
        assert settings.RETRY_COUNT == 3
        assert settings.RETRY_DELAY == 100
        assert settings.RETRY_BACKOFF_MULTIPLIER == 2.0
        assert settings.REQUEST_COALESCE_LIMIT == 100

    def test_log_level_validation(self):
        """Test that log level is validated and normalized."""
        # Valid log levels
        assert Settings(LOG_LEVEL="DEBUG").LOG_LEVEL == "DEBUG"
        assert Settings(LOG_LEVEL="info").LOG_LEVEL == "INFO"
        assert Settings(LOG_LEVEL="WARNING").LOG_LEVEL == "WARNING"
        assert Settings(LOG_LEVEL="error").LOG_LEVEL == "ERROR"

        # Invalid log level
        with pytest.raises(ValidationError, match="LOG_LEVEL must be one of"):
            Settings(LOG_LEVEL="INVALID")

    def test_base_url_validation(self):
        """Test that base URL is validated and normalized."""
        # Valid URLs
        settings = Settings(OPENMETEO_BASE_URL="https://api.example.com/")
        assert settings.OPENMETEO_BASE_URL == "https://api.example.com"

        settings = Settings(OPENMETEO_BASE_URL="http://localhost:8080")
        assert settings.OPENMETEO_BASE_URL == "http://localhost:8080"

        # Invalid URL (no protocol)
        with pytest.raises(ValidationError, match="must start with http"):
            Settings(OPENMETEO_BASE_URL="api.example.com")

    def test_numeric_constraints(self):
        """Test that numeric constraints are enforced."""
        # Valid values
        Settings(UPSTREAM_TIMEOUT=0.5)
        Settings(CACHE_TTL=30)
        Settings(CACHE_MAX_SIZE=1000)
        Settings(PORT=3000)

        # Invalid values
        with pytest.raises(ValidationError):
            Settings(UPSTREAM_TIMEOUT=0.05)  # Too low

        with pytest.raises(ValidationError):
            Settings(CACHE_TTL=0)  # Too low

        with pytest.raises(ValidationError):
            Settings(PORT=70000)  # Too high

    def test_optional_api_key(self):
        """Test that API key is optional."""
        settings = Settings()
        assert settings.OPENMETEO_API_KEY is None

        settings = Settings(OPENMETEO_API_KEY="test-key-123")
        assert settings.OPENMETEO_API_KEY == "test-key-123"
