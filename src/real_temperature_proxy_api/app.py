"""Main FastAPI application."""

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from loguru import logger
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from prometheus_client import REGISTRY, generate_latest

from .api import health, routes
from .core.config import settings


def setup_logging():
    """Configure loguru for structured logging.

    Sets up logging with the configured log level from settings.
    Logs are written to stderr with structured format.
    """
    # Remove default handler
    logger.remove()

    # Add custom handler with structured format
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level> | {extra}",
        level=settings.LOG_LEVEL,
        serialize=False,  # Human-readable format
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    logger.info(
        "Logging configured",
        level=settings.LOG_LEVEL,
    )


def setup_metrics():
    """Configure OpenTelemetry metrics with Prometheus exporter.

    Sets up OpenTelemetry with Prometheus exporter for metrics collection.
    Metrics are exposed at /metrics endpoint compatible with Prometheus scraping.
    """
    # Create Prometheus metric reader
    reader = PrometheusMetricReader()

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": "real-temperature-proxy-api",
            "service.version": "0.1.0",
        }
    )

    # Create meter provider
    provider = MeterProvider(
        resource=resource,
        metric_readers=[reader],
    )

    # Set global meter provider
    metrics.set_meter_provider(provider)

    logger.info("OpenTelemetry metrics configured")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize cache, log configuration
    - Shutdown: Cleanup resources

    Args:
        app: FastAPI application instance

    Example:
        >>> # Used automatically by FastAPI
        >>> app = FastAPI(lifespan=lifespan)
    """
    # Startup
    logger.info("Starting Real Temperature Proxy API")

    # Log active configuration (without sensitive values)
    logger.info(
        "Configuration loaded",
        upstream_timeout=settings.UPSTREAM_TIMEOUT,
        cache_ttl=settings.CACHE_TTL,
        cache_max_size=settings.CACHE_MAX_SIZE,
        retry_count=settings.RETRY_COUNT,
        retry_delay=settings.RETRY_DELAY,
        retry_backoff_multiplier=settings.RETRY_BACKOFF_MULTIPLIER,
        request_coalesce_limit=settings.REQUEST_COALESCE_LIMIT,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL,
        openmeteo_base_url=settings.OPENMETEO_BASE_URL,
        # Do NOT log API key
    )

    # Initialize cache
    FastAPICache.init(
        InMemoryBackend(),
        prefix="weather-cache:",
    )
    logger.info("Cache initialized")

    # Application is now ready
    logger.info("Application ready to serve requests")

    yield

    # Shutdown
    logger.info("Shutting down Real Temperature Proxy API")


# Set up logging first
setup_logging()

# Set up metrics
setup_metrics()

# Create FastAPI application
app = FastAPI(
    title="Real Temperature Proxy API",
    description="REST API that fetches current temperature data from Open-Meteo and returns normalized responses",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.LOG_LEVEL == "DEBUG" else None,  # Swagger UI only in debug mode
    redoc_url=None,  # Disable ReDoc
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(routes.router, tags=["Weather"])


# Metrics endpoint
@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    """Prometheus metrics endpoint.

    Exposes OpenTelemetry metrics in Prometheus format for scraping.
    This endpoint is open to everyone (no authentication).

    Returns:
        Prometheus-formatted metrics

    Example:
        >>> # GET /metrics
        >>> # Returns: Prometheus metrics in text format
    """
    return JSONResponse(
        content=generate_latest(REGISTRY).decode("utf-8"),
        media_type="text/plain",
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors.

    Logs the exception and returns a generic error response to avoid
    exposing internal details to clients.

    Args:
        request: The incoming request
        exc: The unhandled exception

    Returns:
        JSON error response with 500 status code
    """
    logger.exception(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


# Instrument with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

logger.info("FastAPI application created")
