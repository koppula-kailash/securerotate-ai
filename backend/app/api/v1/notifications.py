"""
SecureRotate AI - Notifications API Router
Provides manual expiry check triggers and notification history retrieval endpoints.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationResponse, ExpiryScanResponse
from app.services.expiry_monitor import run_expiry_scan
from pydantic import BaseModel, Field
from app.api.dependencies.auth_dependencies import get_current_active_user, require_roles

router = APIRouter()


class TestEmailRequest(BaseModel):
    recipient_email: str = Field(..., description="Target email address for test message")


@router.post(
    "/test-email",
    summary="Send Test Email (Admin Only)",
    description="Dispatches a test email to verify SMTP configuration without exposing secrets.",
)
async def send_test_email(
    payload: TestEmailRequest,
    current_user: User = Depends(require_roles(["ADMIN"])),
) -> Dict[str, Any]:
    """Admin-only test email endpoint."""
    from app.services.email_service import send_raw_email, log_email_audit

    subject = "SecureRotate AI — Email Test"
    body = """Hello,

This is a test email from SecureRotate AI.

SecureRotate AI
"""
    success = send_raw_email(payload.recipient_email, subject, body)

    await log_email_audit(
        event_type="TEST_EMAIL_SENT" if success else "TEST_EMAIL_FAILED",
        action="SEND_TEST_EMAIL",
        status="SUCCESS" if success else "FAILED",
        details=f"Test email to {payload.recipient_email} {'dispatched' if success else 'failed'}.",
        user_id=current_user.id,
    )

    return {
        "status": "sent",
        "recipient": payload.recipient_email,
        "delivery": "live_smtp" if success else "logged",
    }


@router.post(
    "/check-expiry",
    response_model=ExpiryScanResponse,
    summary="Manually Trigger Credential Expiry Scan",
    description="Evaluates credential expiration dates, creates alert notifications, dispatches console alerts, and records audit logs.",
)
async def trigger_expiry_check(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ExpiryScanResponse:
    """Manually trigger expiration scan for developer testing and demonstration."""
    result = await run_expiry_scan(db)
    return ExpiryScanResponse(
        checked_credentials=result["checked_credentials"],
        notifications_created=result["notifications_created"],
    )


@router.get(
    "",
    response_model=List[NotificationResponse],
    summary="List All Dispatched Notifications",
    description="Returns notification history records sorted by creation timestamp.",
)
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[NotificationResponse]:
    """Retrieve history of all dispatched notifications."""
    stmt = select(Notification).order_by(Notification.id.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())

