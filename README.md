# Real Temperature Proxy API

A high-performance REST API that fetches current temperature and wind speed data from the Open-Meteo Forecast API and returns normalized, cached responses.

## Features

- ✅ **Fast & Efficient**: 60-second caching and request coalescing minimize upstream API calls
- ✅ **Resilient**: Exponential backoff retries with configurable timeouts
- ✅ **Production-Ready**: Health checks, metrics, structured logging, and Kubernetes manifests
- ✅ **Type-Safe**: Full Pydantic validation and type hints
- ✅ **Observable**: OpenTelemetry metrics with Prometheus export
- ✅ **Secure**: Non-root container, CORS support, and security headers

## Quick Start

### Prerequisites

- Python 3.14+
- [mise](https://mise.jdx.dev/) (manages Python and uv versions)
- [uv](https://github.com/astral-sh/uv) (fast Python package manager)

### Installation

```bash
# Install dependencies
uv sync

# Run the application
uv run python main.py
```

The API will be available at `http://localhost:8000`.

### Docker

```bash
# Build the image
docker build -t real-temperature-proxy-api .

# Run the container
docker run -p 8000:8000 real-temperature-proxy-api
```

### Kubernetes

```bash
# Apply manifests
kubectl apply -k k8s/

# Or using individual files
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

## API Usage

### Get Current Weather

**Endpoint:** `GET /v1/current`

**Query Parameters:**
- `lat` or `latitude` (required): Latitude in decimal degrees (-90 to 90)
- `lon` or `longitude` (required): Longitude in decimal degrees (-180 to 180)

**Example Request:**

```bash
curl "http://localhost:8000/v1/current?lat=52.52&lon=13.41"
```

**Example Response:**

```json
{
  "location": {
    "lat": 52.52,
    "lon": 13.41
  },
  "current": {
    "temperatureC": 1.2,
    "windSpeedKmh": 9.7
  },
  "source": "open-meteo",
  "retrievedAt": "2026-01-20T10:12:54Z"
}
```

### Health Checks

```bash
# Liveness probe
curl http://localhost:8000/health

# Readiness probe
curl http://localhost:8000/ready
```

### Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/metrics
```

## Configuration

Configure via environment variables:

### Upstream Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `UPSTREAM_TIMEOUT` | `1.0` | Timeout for Open-Meteo API requests (seconds) |
| `OPENMETEO_BASE_URL` | `https://api.open-meteo.com/v1/forecast` | Base URL for Open-Meteo API |
| `OPENMETEO_API_KEY` | `None` | Optional API key for Open-Meteo |

### Cache Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_TTL` | `60` | Cache TTL in seconds |
| `CACHE_MAX_SIZE` | `10000` | Maximum cached entries (LRU eviction) |

### Retry Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `RETRY_COUNT` | `3` | Maximum number of retries |
| `RETRY_DELAY` | `100` | Initial retry delay (milliseconds) |
| `RETRY_BACKOFF_MULTIPLIER` | `2.0` | Exponential backoff multiplier |

### Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `REQUEST_COALESCE_LIMIT` | `100` | Max concurrent waiters per coordinate |

## Development

### Setup Development Environment

```bash
# Install all dependencies (including dev)
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run integration tests
uv run pytest tests/test_integration.py -m integration

# Run specific test file
uv run pytest tests/test_api.py -v
```

### Code Quality

```bash
# Run linter
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Run security checks
uv run bandit -r src/

# Type checking
uv run mypy src/ --ignore-missing-imports
```

### Running with Live Reload

```bash
uv run uvicorn src.real_temperature_proxy_api.app:app --reload
```

## Architecture

### Component Overview

```
┌─────────────┐
│   Client    │
└─────┬───────┘
      │
      ▼
┌─────────────────────────────────────────┐
│         FastAPI Application              │
│  ┌────────────────────────────────────┐ │
│  │   Weather Endpoint (/v1/current)   │ │
│  │   - Parameter validation           │ │
│  │   - Request coalescing             │ │
│  │   - 60s caching (fastapi-cache2)   │ │
│  └────────────┬───────────────────────┘ │
│               │                          │
│  ┌────────────▼───────────────────────┐ │
│  │      Weather Service               │ │
│  │   - Coordinate rounding            │ │
│  │   - Duplicate request handling     │ │
│  └────────────┬───────────────────────┘ │
│               │                          │
│  ┌────────────▼───────────────────────┐ │
│  │    Open-Meteo Client               │ │
│  │   - Async HTTP (httpx)             │ │
│  │   - Retry w/ exponential backoff   │ │
│  │   - 1s timeout                     │ │
│  │   - Response normalization         │ │
│  └────────────┬───────────────────────┘ │
└───────────────┼─────────────────────────┘
                │
                ▼
        ┌───────────────┐
        │  Open-Meteo   │
        │      API      │
        └───────────────┘
```

### Key Design Decisions

1. **Caching Strategy**: In-memory cache with 60s TTL, coordinates rounded to 4 decimal places for cache keys
2. **Request Coalescing**: Prevents thundering herd by deduplicating concurrent requests for same coordinates
3. **Retry Logic**: Exponential backoff with jitter, retries on timeouts and 5xx errors only
4. **Error Handling**: Proper HTTP status codes (502 for upstream errors, 504 for timeouts, 400 for validation)
5. **Horizontal Scaling**: Sticky sessions recommended due to per-pod cache (consider Redis for distributed cache)

## Performance

- **Cached responses**: p95 < 50ms
- **Uncached responses**: p95 < 1.5s
- **Throughput**: ≥ 1000 req/s (with caching)

## Monitoring

### Metrics

The `/metrics` endpoint exposes Prometheus-compatible metrics:

- Request count (by status code and endpoint)
- Request duration histogram
- Cache hit/miss ratio
- Upstream API latency
- Upstream API error rate

### Logging

Structured logging with loguru includes:

- Request/response logging
- Upstream API calls (status codes, latency)
- Error logging with stack traces
- **Note**: Coordinates are NOT logged in normal operation (PII concern)

## Security

- ✅ Non-root container user
- ✅ Read-only root filesystem (where applicable)
- ✅ Dropped capabilities
- ✅ CORS enabled for all origins
- ✅ Security headers (X-Content-Type-Options, HSTS) at ingress level
- ✅ Rate limiting at ingress controller
- ✅ No authentication (public API)

## Documentation

- **[docs/decisions.md](docs/decisions.md)**: All implementation decisions organized by topic
- **[docs/task_description.md](docs/task_description.md)**: Original task requirements and context
- **[CLAUDE.md](CLAUDE.md)**: Project guidance for Claude Code

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run pre-commit hooks: `uv run pre-commit run --all-files`
5. Submit a pull request

All commits must pass:
- Ruff linting and formatting
- Bandit security checks
- Mypy type checking
- Pytest unit tests

## Acknowledgments

- [Open-Meteo](https://open-meteo.com/) for providing the free weather API
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [uv](https://github.com/astral-sh/uv) for blazing-fast package management
