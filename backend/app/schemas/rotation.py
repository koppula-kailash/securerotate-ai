"""
SecureRotate AI - Rotation Schemas
Defines request validation and response models for credential rotation and verification.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RotationTriggerRequest(BaseModel):
    """Payload to trigger credential rotation."""
    simulate_failure: bool = Field(False, description="Simulate a verification failure to test rollback")


class RotationExecutionResponse(BaseModel):
    """Response returned upon rotation execution."""
    success: bool
    status: str = Field(..., description="SUCCESS, ROLLED_BACK, FAILED")
    credential_id: int
    message: str
    rotation_time: Optional[datetime] = None
    verification_latency_ms: Optional[float] = None
    rollback_performed: bool = False

    model_config = ConfigDict(from_attributes=True)


class RotationStatusResponse(BaseModel):
    """Status details for a credential's rotation lifecycle."""
    credential_id: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    verification_status: str
    duration_ms: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class RotationHistoryResponse(BaseModel):
    """Historical rotation attempt log record."""
    id: int
    credential_id: int
    old_expiry: Optional[datetime] = None
    new_expiry: Optional[datetime] = None
    trigger_type: str
    status: str
    failure_reason: Optional[str] = None
    risk_score_at_rotation: Optional[float] = None
    verification_latency_ms: Optional[float] = None
    rotation_time: datetime

    model_config = ConfigDict(from_attributes=True)
