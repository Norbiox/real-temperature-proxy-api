"""FastAPI dependencies for request handling."""

from typing import Annotated

from fastapi import HTTPException, Query


def get_latitude_param(
    lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    latitude: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    LAT: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    Lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    LATITUDE: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    Latitude: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
) -> float | None:
    """Get latitude parameter with case-insensitive support and conflict detection.

    Supports: lat, latitude, LAT, Lat, LATITUDE, Latitude
    Priority: lowercase short > lowercase long > mixed/uppercase

    Detects conflicts: if lat=52.52 and latitude=52.53 (different values), returns 400.

    Args:
        lat: Latitude (lowercase short form)
        latitude: Latitude (lowercase long form)
        LAT: Latitude (uppercase short form)
        Lat: Latitude (mixed case short form)
        LATITUDE: Latitude (uppercase long form)
        Latitude: Latitude (mixed case long form)

    Returns:
        Latitude value or None

    Raises:
        HTTPException: 400 if conflicting values provided

    Example:
        >>> # GET /v1/current?LAT=52.52&lon=13.41
        >>> # Returns: 52.52
    """
    # Collect all non-None values (normalized to lowercase names)
    values = {}
    if lat is not None:
        values["lat"] = lat
    if Lat is not None:
        values["lat_mixed"] = Lat
    if LAT is not None:
        values["lat_upper"] = LAT
    if latitude is not None:
        values["latitude"] = latitude
    if Latitude is not None:
        values["latitude_mixed"] = Latitude
    if LATITUDE is not None:
        values["latitude_upper"] = LATITUDE

    if not values:
        return None

    # Check for conflicts between short and long forms
    short_values = {
        v
        for k, v in values.items()
        if k.startswith("lat") and not k.startswith("latitude")
    }
    long_values = {v for k, v in values.items() if k.startswith("latitude")}

    # If both short and long forms provided with different values, that's a conflict
    if short_values and long_values and short_values != long_values:
        raise HTTPException(
            status_code=400,
            detail={"error": "Conflicting latitude values provided (lat and latitude)"},
        )

    # Return first available value with priority
    if lat is not None:
        return lat
    if Lat is not None:
        return Lat
    if LAT is not None:
        return LAT
    if latitude is not None:
        return latitude
    if Latitude is not None:
        return Latitude
    if LATITUDE is not None:
        return LATITUDE
    return None


def get_longitude_param(
    lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    longitude: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    LON: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    Lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    LONGITUDE: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    Longitude: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
) -> float | None:
    """Get longitude parameter with case-insensitive support and conflict detection.

    Supports: lon, longitude, LON, Lon, LONGITUDE, Longitude
    Priority: lowercase short > lowercase long > mixed/uppercase

    Detects conflicts: if lon=13.41 and longitude=13.42 (different values), returns 400.

    Args:
        lon: Longitude (lowercase short form)
        longitude: Longitude (lowercase long form)
        LON: Longitude (uppercase short form)
        Lon: Longitude (mixed case short form)
        LONGITUDE: Longitude (uppercase long form)
        Longitude: Longitude (mixed case long form)

    Returns:
        Longitude value or None

    Raises:
        HTTPException: 400 if conflicting values provided

    Example:
        >>> # GET /v1/current?lat=52.52&LON=13.41
        >>> # Returns: 13.41
    """
    # Collect all non-None values (normalized to lowercase names)
    values = {}
    if lon is not None:
        values["lon"] = lon
    if Lon is not None:
        values["lon_mixed"] = Lon
    if LON is not None:
        values["lon_upper"] = LON
    if longitude is not None:
        values["longitude"] = longitude
    if Longitude is not None:
        values["longitude_mixed"] = Longitude
    if LONGITUDE is not None:
        values["longitude_upper"] = LONGITUDE

    if not values:
        return None

    # Check for conflicts between short and long forms
    short_values = {
        v
        for k, v in values.items()
        if k.startswith("lon") and not k.startswith("longitude")
    }
    long_values = {v for k, v in values.items() if k.startswith("longitude")}

    # If both short and long forms provided with different values, that's a conflict
    if short_values and long_values and short_values != long_values:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Conflicting longitude values provided (lon and longitude)"
            },
        )

    # Return first available value with priority
    if lon is not None:
        return lon
    if Lon is not None:
        return Lon
    if LON is not None:
        return LON
    if longitude is not None:
        return longitude
    if Longitude is not None:
        return Longitude
    if LONGITUDE is not None:
        return LONGITUDE
    return None
