"""Weather data models for request/response handling."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LocationModel(BaseModel):
    """Location coordinates.

    Example:
        >>> loc = LocationModel(lat=52.52, lon=13.41)
        >>> loc.lat
        52.52
        >>> loc.lon
        13.41
    """

    lat: float = Field(
        ...,
        description="Latitude in decimal degrees",
        ge=-90.0,
        le=90.0,
    )
    lon: float = Field(
        ...,
        description="Longitude in decimal degrees",
        ge=-180.0,
        le=180.0,
    )

    @field_validator("lat", "lon")
    @classmethod
    def validate_precision(cls, v: float) -> float:
        """Validate coordinate precision (max 6 decimal places).

        Args:
            v: The coordinate value

        Returns:
            The coordinate value

        Raises:
            ValueError: If precision exceeds 6 decimal places

        Example:
            >>> LocationModel(lat=52.123456, lon=13.123456)
            LocationModel(lat=52.123456, lon=13.123456)
        """
        # Check if more than 6 decimal places
        str_val = f"{v:.10f}".rstrip("0")
        if "." in str_val:
            decimals = len(str_val.split(".")[1])
            if decimals > 6:
                raise ValueError(
                    f"Coordinate precision must not exceed 6 decimal places, got {decimals}"
                )
        return v


class CurrentWeatherModel(BaseModel):
    """Current weather conditions.

    Example:
        >>> weather = CurrentWeatherModel(temperatureC=1.2, windSpeedKmh=9.7)
        >>> weather.temperatureC
        1.2
        >>> weather.windSpeedKmh
        9.7
    """

    temperatureC: float | None = Field(
        ...,
        description="Temperature in Celsius (1 decimal place)",
    )
    windSpeedKmh: float | None = Field(
        ...,
        description="Wind speed in km/h (1 decimal place)",
    )


class WeatherResponse(BaseModel):
    """Normalized weather response returned to clients.

    Example:
        >>> from datetime import datetime, timezone
        >>> response = WeatherResponse(
        ...     location=LocationModel(lat=52.52, lon=13.41),
        ...     current=CurrentWeatherModel(temperatureC=1.2, windSpeedKmh=9.7),
        ...     source="open-meteo",
        ...     retrievedAt=datetime(2026, 1, 11, 10, 12, 54, tzinfo=timezone.utc)
        ... )
        >>> response.source
        'open-meteo'
    """

    location: LocationModel = Field(..., description="Location coordinates")
    current: CurrentWeatherModel = Field(..., description="Current weather conditions")
    source: Literal["open-meteo"] = Field(
        default="open-meteo",
        description="Data source identifier",
    )
    retrievedAt: datetime = Field(
        ...,
        description="ISO 8601 UTC timestamp when data was originally fetched",
    )

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class OpenMeteoCurrentUnits(BaseModel):
    """Units from Open-Meteo API response."""

    time: str
    interval: str
    temperature_2m: str
    wind_speed_10m: str


class OpenMeteoCurrentData(BaseModel):
    """Current weather data from Open-Meteo API.

    Example:
        >>> data = OpenMeteoCurrentData(
        ...     time="2026-01-11T10:12",
        ...     interval=900,
        ...     temperature_2m=1.2,
        ...     wind_speed_10m=9.7
        ... )
        >>> data.temperature_2m
        1.2
    """

    time: str
    interval: int
    temperature_2m: float | None = None
    wind_speed_10m: float | None = None


class OpenMeteoResponse(BaseModel):
    """Full response from Open-Meteo API.

    Example:
        >>> response = OpenMeteoResponse(
        ...     latitude=52.52,
        ...     longitude=13.41,
        ...     generationtime_ms=0.123,
        ...     utc_offset_seconds=0,
        ...     timezone="GMT",
        ...     timezone_abbreviation="GMT",
        ...     elevation=38.0,
        ...     current_units=OpenMeteoCurrentUnits(
        ...         time="iso8601",
        ...         interval="seconds",
        ...         temperature_2m="°C",
        ...         wind_speed_10m="km/h"
        ...     ),
        ...     current=OpenMeteoCurrentData(
        ...         time="2026-01-11T10:12",
        ...         interval=900,
        ...         temperature_2m=1.2,
        ...         wind_speed_10m=9.7
        ...     )
        ... )
        >>> response.latitude
        52.52
    """

    latitude: float
    longitude: float
    generationtime_ms: float
    utc_offset_seconds: int
    timezone: str
    timezone_abbreviation: str
    elevation: float
    current_units: OpenMeteoCurrentUnits
    current: OpenMeteoCurrentData
