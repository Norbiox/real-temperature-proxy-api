"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from src.real_temperature_proxy_api.app import app


@pytest.fixture(scope="function", autouse=True)
def setup_cache():
    """Initialize FastAPI cache for each test."""
    FastAPICache.init(InMemoryBackend(), prefix="test-cache:")
    yield
    # Reset after test
    FastAPICache.reset()


@pytest.fixture(scope="function")
def client():
    """Create a test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client
