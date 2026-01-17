# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Documentation

Before implementing, review these documents:
- **[docs/decisions.md](docs/decisions.md)**: All implementation decisions organized by topic. Start here to understand architecture and design choices.
- **[docs/task_description.md](docs/task_description.md)**: Original task requirements and context.

## Project Overview

Real Temperature Proxy API is a REST API that fetches current temperature data from the Open-Meteo Forecast API and returns a normalized response. The API normalizes temperature and wind speed data into a consistent format with location and retrieval metadata.
Requirements are in docs/task_description.md.

## Tech Stack

- **Language**: Python 3.14
- **Framework**: FastAPI
- **Package Manager**: uv
- **Tool Manager**: mise (manages Python and uv versions)
- **Testing**: pytest (TDD approach)
- **Linting**: ruff
- **Development Workflow**: Trunk-based development on master branch

## Architecture Overview

The API acts as a proxy between clients and the Open-Meteo API. Key architectural decisions:

1. **Caching**: Responses are cached by `(latitude, longitude)` tuple for 60 seconds to reduce API calls
2. **Timeout Strategy**: Upstream Open-Meteo calls have a 1-second timeout to prevent hanging requests
3. **Request-Response Normalization**: Raw Open-Meteo data is transformed into a standardized response format
4. **Response Shape**:
   ```json
   {
     "location": { "lat": 52.52, "lon": 13.41 },
     "current": {
       "temperatureC": 1.2,
       "windSpeedKmh": 9.7
     },
     "source": "open-meteo",
     "retrievedAt": "2026-01-11T10:12:54Z"
   }
   ```

## Common Development Commands

### Setup
```bash
# Install dependencies and set up environment
uv sync
```

### Running

```bash
# Run the application
python main.py

# Run the server (when FastAPI is integrated)
uv run uvicorn main:app --reload
```

### Testing

```bash
# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run a single test file
uv run pytest tests/test_api.py

# Run tests matching a pattern
uv run pytest -k "test_cache"

# Run tests with coverage report
uv run pytest --cov=. --cov-report=html
```

### Linting & Code Quality

```bash
# Check code with ruff
uv run ruff check .

# Fix issues automatically
uv run ruff check . --fix

# Format code
uv run ruff format .

# Run security checks (bandit)
uv run bandit -r .
```

### Git Workflow

This project uses trunk-based development:
- Work directly on `master` branch
- Make frequent, incremental commits
- Pre-commit hooks automatically run tests, linting, and security checks
- GitHub Actions runs the full suite (pytest, ruff, bandit) on push

## Open-Meteo Integration

The API calls Open-Meteo's `/v1/forecast` endpoint with the `current` parameter:

```
Base URL: https://api.open-meteo.com/v1/forecast
Required parameters: latitude, longitude, current=temperature_2m,wind_speed_10m
```

Example request:
```
GET https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current=temperature_2m,wind_speed_10m
```

The response contains current conditions that need to be normalized into the proxy API format.

## Key Implementation Details

- **Cache Strategy**: Implement a simple in-memory cache keyed by `(lat, lon)` with 60-second TTL
- **Error Handling**: Gracefully handle upstream timeouts and API errors; return appropriate HTTP status codes
- **Endpoint Design**: Design RESTful endpoint structure (e.g., `/weather?lat=...&lon=...` or `/weather/{lat}/{lon}`)
- **Configuration**: Support configurable timeouts and cache TTLs for production flexibility
- **Health Checks**: Implement health check endpoints for container orchestration
- **Resource Limits**: Add resource limits and request validation

## Production Considerations

- Container image with resource limits and health checks for Kubernetes deployment
- Configuration via environment variables for timeouts, cache TTLs
- Logging for debugging and monitoring
- Request validation and rate limiting if needed
