"""
SecureRotate AI - Phase 1 Foundation API Tests
Tests root endpoint GET / and health endpoint GET /api/v1/health.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Verify root GET / endpoint returns 200 and serves the SPA index HTML."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "SecureRotate AI" in response.text


@pytest.mark.asyncio
async def test_health_endpoint_structure():
    """Verify GET /api/v1/health endpoint responds with expected JSON schema."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/health")
        # Status code is either 200 (healthy) or 503 (database offline during isolated test)
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert data["status"] in ["healthy", "unhealthy"]
        assert data["database"] in ["connected", "disconnected"]
