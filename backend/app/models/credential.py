"""
SecureRotate AI - Credential Database Model
Represents target database credentials managed and rotated by SecureRotate AI.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.dependency import Dependency
    from app.models.approval import RotationApproval
    from app.models.audit import AuditLog
    from app.models.rotation_history import RotationHistory


class Credential(Base):
    """
    Credential model storing target database access parameters.
    Passwords are strictly stored encrypted in `encrypted_password`.
    """

    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    database_type: Mapped[str] = mapped_column(String(50), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=3306)
    database_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)

    environment: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    privilege_level: Mapped[str] = mapped_column(String(50), nullable=False, default="LOW")
    access_frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dependency_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE", index=True)
    auto_rotation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    owner_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default="admin@securerotate.local")

    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    last_rotated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    @property
    def is_expired(self) -> bool:
        """Return True if the credential's expires_at is in the past (UTC)."""
        if not self.expires_at:
            return False
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires < datetime.now(timezone.utc)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="credentials"
    )
    dependencies: Mapped[List["Dependency"]] = relationship(
        "Dependency", back_populates="credential", cascade="all, delete-orphan"
    )
    approvals: Mapped[List["RotationApproval"]] = relationship(
        "RotationApproval", back_populates="credential", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="credential"
    )
    rotation_history: Mapped[List["RotationHistory"]] = relationship(
        "RotationHistory", back_populates="credential", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Credential(id={self.id}, name='{self.name}', status='{self.status}')>"
