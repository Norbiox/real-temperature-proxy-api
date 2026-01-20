"""Application configuration using Pydantic Settings."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings have sensible defaults but can be overridden via environment variables.
    Configuration is validated at startup and the application will fail fast if invalid.

    Example:
        >>> settings = Settings()
        >>> settings.UPSTREAM_TIMEOUT >= 0.1
        True
        >>> settings.CACHE_TTL >= 1
        True
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Upstream API Configuration
    UPSTREAM_TIMEOUT: float = Field(
        default=1.0,
        description="Timeout for Open-Meteo API requests in seconds",
        ge=0.1,
        le=30.0,
    )
    OPENMETEO_BASE_URL: str = Field(
        default="https://api.open-meteo.com/v1/forecast",
        description="Base URL for Open-Meteo API",
    )
    OPENMETEO_API_KEY: str | None = Field(
        default=None,
        description="Optional API key for Open-Meteo (only passed if set)",
    )

    # Retry Configuration
    RETRY_COUNT: int = Field(
        default=3,
        description="Maximum number of retries on upstream failure",
        ge=0,
        le=10,
    )
    RETRY_DELAY: int = Field(
        default=100,
        description="Initial retry delay in milliseconds",
        ge=10,
        le=5000,
    )
    RETRY_BACKOFF_MULTIPLIER: float = Field(
        default=2.0,
        description="Exponential backoff multiplier for retries",
        ge=1.0,
        le=10.0,
    )

    # Cache Configuration
    CACHE_TTL: int = Field(
        default=60,
        description="Cache TTL in seconds",
        ge=1,
        le=3600,
    )
    CACHE_MAX_SIZE: int = Field(
        default=10000,
        description="Maximum number of cached entries (LRU eviction)",
        ge=1,
        le=1000000,
    )

    # Request Coalescing
    REQUEST_COALESCE_LIMIT: int = Field(
        default=100,
        description="Max concurrent waiters per coordinate to prevent unbounded memory growth",
        ge=1,
        le=10000,
    )

    # Server Configuration
    PORT: int = Field(
        default=8000,
        description="Server port",
        ge=1,
        le=65535,
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # Environment Configuration
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that LOG_LEVEL is a valid logging level.

        Args:
            v: The log level string to validate

        Returns:
            The uppercase log level string

        Raises:
            ValueError: If the log level is invalid

        Example:
            >>> Settings(LOG_LEVEL="info").LOG_LEVEL
            'INFO'
            >>> Settings(LOG_LEVEL="DEBUG").LOG_LEVEL
            'DEBUG'
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}, got {v}")
        return v_upper

    @field_validator("OPENMETEO_BASE_URL")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate that the base URL is properly formatted.

        Args:
            v: The URL string to validate

        Returns:
            The URL string without trailing slash

        Raises:
            ValueError: If the URL is invalid

        Example:
            >>> Settings(OPENMETEO_BASE_URL="https://api.example.com/").OPENMETEO_BASE_URL
            'https://api.example.com'
        """
        if not v.startswith(("http://", "https://")):
            raise ValueError("OPENMETEO_BASE_URL must start with http:// or https://")
        # Remove trailing slash for consistency
        return v.rstrip("/")


# Global settings instance
settings = Settings()
