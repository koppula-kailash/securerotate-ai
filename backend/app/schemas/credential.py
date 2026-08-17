"""
SecureRotate AI - Credential Schemas
Pydantic schemas for request validation and safe response serialization.
Passwords and encrypted passwords are STRICTLY excluded from response models.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CredentialCreate(BaseModel):
    """Schema for creating a new database credential."""
    name: str = Field(..., description="Human-readable credential identifier")
    database_type: str = Field(..., description="Target database engine type (e.g. MySQL, PostgreSQL, MongoDB)")
    host: str = Field(..., description="Target database hostname or IP address")
    port: int = Field(3306, description="Target database connection port")
    database_name: str = Field(..., description="Target database schema name")
    username: str = Field(..., description="Database user account name")
    password: str = Field(..., description="Plaintext database password (encrypted before storage)")
    environment: str = Field(..., description="Deployment environment (e.g. Production, Staging, Development)")
    privilege_level: str = Field("LOW", description="Privilege level (e.g. LOW, MEDIUM, HIGH, ADMIN)")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    auto_rotation_enabled: bool = Field(False, description="Enable automated AI/scheduled rotation")
    owner_email: Optional[str] = Field("admin@securerotate.local", description="Owner/Admin email to receive rotation alerts")


class CredentialUpdate(BaseModel):
    """Schema for updating existing credential fields."""
    name: Optional[str] = Field(None, description="Human-readable credential identifier")
    host: Optional[str] = Field(None, description="Target database hostname or IP address")
    port: Optional[int] = Field(None, description="Target database connection port")
    database_name: Optional[str] = Field(None, description="Target database schema name")
    username: Optional[str] = Field(None, description="Database user account name")
    password: Optional[str] = Field(None, description="New plaintext password (encrypted before storage)")
    environment: Optional[str] = Field(None, description="Deployment environment")
    privilege_level: Optional[str] = Field(None, description="Privilege level")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    auto_rotation_enabled: Optional[bool] = Field(None, description="Enable automated AI/scheduled rotation")
    owner_email: Optional[str] = Field(None, description="Owner/Admin email to receive rotation alerts")


class CredentialResponse(BaseModel):
    """
    Safe credential response schema.
    Plaintext and encrypted passwords are strictly EXCLUDED.
    """
    id: int
    name: str
    database_type: str
    host: str
    port: int
    database_name: str
    username: str
    environment: str
    privilege_level: str
    owner_email: Optional[str] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    status: str
    expires_at: Optional[datetime] = None
    last_rotated_at: Optional[datetime] = None
    auto_rotation_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
