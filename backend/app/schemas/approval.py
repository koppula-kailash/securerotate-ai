"""
SecureRotate AI - Rotation Approval Pydantic Schemas
Defines request validation and response models for rotation approval workflows.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RotationApprovalCreate(BaseModel):
    """Schema for submitting a new credential rotation request."""
    credential_id: int = Field(..., description="Target credential ID requiring rotation")
    reason: Optional[str] = Field(None, description="Justification or trigger reason for rotation")


class RotationApprovalReject(BaseModel):
    """Schema for rejecting a rotation approval request."""
    rejection_reason: str = Field(..., description="Required explanation for rejecting rotation")


class RotationApprovalResponse(BaseModel):
    """Safe response model for rotation approval status."""
    id: int
    credential_id: int
    status: str
    risk_level: Optional[str] = None
    risk_score: Optional[float] = None
    impact_level: Optional[str] = None
    impact_score: Optional[float] = None
    reason: Optional[str] = None
    rejection_reason: Optional[str] = None
    requested_by: Optional[int] = None
    approved_by: Optional[int] = None
    requested_at: datetime
    approved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
