"""
SecureRotate AI - Credential Management & Risk Prediction Tests
Tests CRUD, encryption, dashboard stats, and ML risk prediction.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_dashboard_stats_endpoint():
    """Verify GET /api/v1/credentials/dashboard-stats returns expected schema with mocked database and auth."""
    from app.db.session import get_db
    from app.api.dependencies.auth_dependencies import get_current_active_user
    from app.models.user import User
    from unittest.mock import AsyncMock, MagicMock

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    async def override_get_db():
        yield mock_db

    async def override_get_user():
        return User(id=1, username="testadmin", email="admin@test.com", role="ADMIN", is_active=True)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/credentials/dashboard-stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_databases" in data
        assert "healthy" in data
        assert "warning" in data
        assert "critical" in data
        assert "expired" in data
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ml_risk_service_prediction():
    """Verify ML risk prediction service outputs valid continuous risk scores and explanations."""
    from app.services.ml_risk_service import predict_credential_risk, generate_recommendation_text

    result = predict_credential_risk(
        days_until_expiry=2,
        credential_age_days=60,
        dependency_count=7,
        privilege_level="ADMIN",
        environment="Production",
        historical_rotation_failures=2,
    )

    assert result["risk_level"] in ["CRITICAL", "HIGH"]
    assert 0.0 <= result["risk_score"] <= 1.0
    assert len(result["reasons"]) > 0

    recommendation = generate_recommendation_text(
        credential_name="Payment DB",
        risk_level=result["risk_level"],
        risk_score=result["risk_score"],
        days_until_expiry=2,
        environment="Production",
        dependency_count=7,
        privilege_level="ADMIN",
        historical_failures=2,
    )
    assert "Recommended Action:" in recommendation
    assert "Reason:" in recommendation


@pytest.mark.asyncio
async def test_long_expiry_risk_boundaries():
    """Verify credentials with > 50 days remaining are never categorized as CRITICAL or HIGH."""
    from app.services.ml_risk_service import predict_credential_risk
    from app.services.risk_calculator import calculate_risk_score
    from datetime import datetime, timezone, timedelta

    # Test with 55 days, Production, ADMIN, 6 dependencies
    result_ml_55 = predict_credential_risk(
        days_until_expiry=55,
        credential_age_days=30,
        dependency_count=6,
        privilege_level="ADMIN",
        environment="Production",
        historical_rotation_failures=0,
    )
    assert result_ml_55["risk_level"] in ["LOW", "MEDIUM"], f"Expected LOW/MEDIUM but got {result_ml_55['risk_level']}"
    assert result_ml_55["risk_level"] != "CRITICAL"
    assert result_ml_55["risk_level"] != "HIGH"

    # Test with 75 days, Production, ADMIN
    result_ml_75 = predict_credential_risk(
        days_until_expiry=75,
        credential_age_days=30,
        dependency_count=2,
        privilege_level="ADMIN",
        environment="Production",
        historical_rotation_failures=0,
    )
    assert result_ml_75["risk_level"] in ["LOW", "MEDIUM"]
    assert result_ml_75["risk_level"] != "CRITICAL"

    # Test rule-based risk calculator with 60 days
    now = datetime.now(timezone.utc)
    future_60 = now + timedelta(days=60)
    score, level = calculate_risk_score("Production", "ADMIN", expires_at=future_60)
    assert level in ["LOW", "MEDIUM"]
    assert level != "CRITICAL"
    assert level != "HIGH"

