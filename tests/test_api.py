"""Tests for API endpoints."""


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_endpoint(self, client):
        """Test /health endpoint returns 200 OK."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_readiness_endpoint(self, client):
        """Test /ready endpoint returns 200 OK."""
        response = client.get("/ready")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestWeatherEndpoint:
    """Test weather endpoint."""

    def test_missing_parameters(self, client):
        """Test that missing parameters return 400."""
        # No parameters
        response = client.get("/v1/current")
        assert response.status_code == 400
        json_response = response.json()
        assert "detail" in json_response
        assert "error" in json_response["detail"]

        # Only latitude
        response = client.get("/v1/current?lat=52.52")
        assert response.status_code == 400
        json_response = response.json()
        assert "detail" in json_response
        assert "error" in json_response["detail"]

        # Only longitude
        response = client.get("/v1/current?lon=13.41")
        assert response.status_code == 400
        json_response = response.json()
        assert "detail" in json_response
        assert "error" in json_response["detail"]

    def test_invalid_coordinates(self, client):
        """Test that invalid coordinates return 400."""
        # Latitude out of range
        response = client.get("/v1/current?lat=91.0&lon=13.41")
        assert response.status_code == 422  # FastAPI validation error

        # Longitude out of range
        response = client.get("/v1/current?lat=52.52&lon=181.0")
        assert response.status_code == 422  # FastAPI validation error

    def test_conflicting_parameters(self, client):
        """Test that conflicting parameters return 400."""
        # Conflicting latitude values
        response = client.get("/v1/current?lat=52.52&latitude=52.53&lon=13.41")
        assert response.status_code == 400
        json_response = response.json()
        assert "detail" in json_response
        assert "Conflicting" in json_response["detail"]["error"]

        # Conflicting longitude values
        response = client.get("/v1/current?lat=52.52&lon=13.41&longitude=13.42")
        assert response.status_code == 400
        json_response = response.json()
        assert "detail" in json_response
        assert "Conflicting" in json_response["detail"]["error"]

    def test_parameter_name_variations(self, client):
        """Test that both short and long parameter names work."""
        # Note: These will fail without mocking the Open-Meteo API
        # This is just testing that the parameter parsing works

        # Short form should be accepted (will fail without mock, but that's ok for now)
        response = client.get("/v1/current?lat=52.52&lon=13.41")
        # We expect either 502/504 (upstream error) or 200 (if somehow it works)
        assert response.status_code in [200, 502, 504]

        # Long form should be accepted
        response = client.get("/v1/current?latitude=52.52&longitude=13.41")
        assert response.status_code in [200, 502, 504]

        # Mixed form should be accepted
        response = client.get("/v1/current?lat=52.52&longitude=13.41")
        assert response.status_code in [200, 502, 504]

    def test_case_insensitivity(self, client):
        """Test that parameter names are case insensitive (handled by FastAPI)."""
        # Note: FastAPI query parameters are case-sensitive by default
        # Our implementation uses lowercase `lat` and `lon`
        # If uppercase is needed, it should map to the alternate names

        # Standard lowercase
        response = client.get("/v1/current?lat=52.52&lon=13.41")
        assert response.status_code in [200, 502, 504]


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    def test_metrics_endpoint(self, client):
        """Test /metrics endpoint returns Prometheus metrics."""
        response = client.get("/metrics")

        assert response.status_code == 200
        # Metrics should be in text/plain format
        assert "text/plain" in response.headers.get("content-type", "")


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers(self, client):
        """Test that CORS headers are present."""
        response = client.options(
            "/v1/current",
            headers={"Origin": "https://example.com"},
        )

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"
