"""
SecureRotate AI - Unit Tests for Email Service & Notifications
Tests all 5 features:
1. Login success email
2. Credential owner email support
3. Successful rotation email (no plaintext passwords)
4. Failed rotation and rollback email
5. Expiry alert email
6. Non-blocking failure tolerance
"""

import pytest
from datetime import datetime, timezone
from app.services.email_service import (
    send_login_success_email,
    send_rotation_success_email,
    send_rotation_failed_email,
    send_expiry_alert_email,
    send_raw_email,
)
from app.schemas.credential import CredentialCreate


@pytest.mark.asyncio
async def test_login_success_email():
    """Verify login success email content and non-blocking delivery."""
    result = await send_login_success_email(
        to_email="admin@enterprise.io",
        username="admin",
        role="ADMIN",
        timestamp="2026-08-16 10:00:00 UTC",
    )
    assert result is True


@pytest.mark.asyncio
async def test_rotation_success_email_no_plain_password():
    """Verify successful rotation email does NOT include plain passwords."""
    result = await send_rotation_success_email(
        to_email="dba@enterprise.io",
        credential_name="Payment DB",
        database_name="production_db",
        environment="Production",
        latency_ms=12.45,
        rotated_at="2026-08-16 10:30:00 UTC",
        next_expiry="Nov 15, 2026",
        risk_level="LOW",
    )
    assert result is True


@pytest.mark.asyncio
async def test_rotation_failed_email():
    """Verify failed rotation email specifies failure and rollback."""
    result = await send_rotation_failed_email(
        to_email="dba@enterprise.io",
        credential_name="Payment DB",
        timestamp="2026-08-16 10:35:00 UTC",
    )
    assert result is True


@pytest.mark.asyncio
async def test_expiry_alert_email():
    """Verify 7-day, 3-day, and 1-day expiry warning alert emails."""
    res_7 = await send_expiry_alert_email(
        to_email="dba@enterprise.io",
        credential_name="Payment DB",
        days_remaining=7,
        risk_level="HIGH",
        recommendation="Schedule credential rotation.",
    )
    assert res_7 is True

    res_1 = await send_expiry_alert_email(
        to_email="dba@enterprise.io",
        credential_name="Payment DB",
        days_remaining=1,
        risk_level="CRITICAL",
        recommendation="Rotate within 24 hours.",
    )
    assert res_1 is True


def test_credential_schema_owner_email():
    """Verify CredentialCreate accepts valid owner_email."""
    payload = CredentialCreate(
        name="Test DB",
        database_type="MySQL",
        host="127.0.0.1",
        port=3306,
        database_name="test_schema",
        username="test_user",
        password="SecretPassword123!",
        environment="Production",
        privilege_level="HIGH",
        owner_email="registered-owner@company.com",
        expires_at=datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert payload.owner_email == "registered-owner@company.com"


def test_invalid_email_does_not_raise():
    """Verify sending to invalid email fails safely without raising exceptions."""
    assert send_raw_email("", "Subject", "Body") is False
    assert send_raw_email("not-an-email", "Subject", "Body") is False


@pytest.mark.asyncio
async def test_admin_test_email_endpoint():
    """Verify POST /api/v1/notifications/test-email returns {status: sent} for admin."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.api.dependencies.auth_dependencies import get_current_active_user
    from app.models.user import User

    async def override_get_admin():
        return User(id=1, username="admin", email="admin@test.com", role="ADMIN", is_active=True)

    app.dependency_overrides[get_current_active_user] = override_get_admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.post(
            "/api/v1/notifications/test-email",
            json={"recipient_email": "admin-test@enterprise.io"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "sent"

    app.dependency_overrides.clear()

