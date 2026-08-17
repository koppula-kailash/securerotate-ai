"""
SecureRotate AI - Audit Log Schemas
Defines request validation and response models for audit trail records.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """Schema for audit log record output."""
    id: int
    user_id: Optional[int] = None
    credential_id: Optional[int] = None
    event_type: str = Field(..., description="Category of event, e.g. LOGIN_SUCCESS, CREDENTIAL_CREATED")
    action: str = Field(..., description="Action type, e.g. CREATE, UPDATE, DELETE, ROTATE")
    status: str = Field(..., description="Execution outcome, e.g. SUCCESS, FAILED, PENDING")
    details: Optional[str] = None
    created_at: datetime
    timestamp: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogFilter(BaseModel):
    """Filter parameters for querying audit logs."""
    event_type: Optional[str] = None
    status: Optional[str] = None
    user_id: Optional[int] = None
    credential_id: Optional[int] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)
