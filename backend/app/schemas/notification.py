"""
SecureRotate AI - Notification Pydantic Schemas
Defines safe serialization schemas for outgoing alert notifications.
Excludes any plaintext passwords or secrets.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    """Safe response model for dispatched alert notifications."""
    id: int
    credential_id: Optional[int] = Field(None, description="Associated credential ID")
    recipient: str = Field(..., description="Target stakeholder group or recipient email")
    notification_type: str = Field(..., description="Alert category (e.g. EXPIRY_WARNING, HIGH_RISK_WARNING, CRITICAL_WARNING)")
    title: str = Field(..., description="Notification headline")
    message: str = Field(..., description="Notification body details")
    risk_level: Optional[str] = Field(None, description="Assigned risk level classification")
    status: str = Field(..., description="Delivery status (PENDING, SENT, FAILED)")
    sent_at: Optional[datetime] = Field(None, description="Timestamp when alert was dispatched")
    created_at: datetime = Field(..., description="Notification creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class ExpiryScanResponse(BaseModel):
    """Response model for manual credential expiry scan trigger."""
    checked_credentials: int = Field(..., description="Total credentials evaluated")
    notifications_created: int = Field(..., description="Number of new alert notifications generated")
