"""
SecureRotate AI - User Database Model
Stores user identity, credentials creator link, and Role-Based Access Control (RBAC) details.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.credential import Credential
    from app.models.approval import RotationApproval
    from app.models.audit import AuditLog


class User(Base):
    """
    User model representing application accounts and RBAC information.
    Allowed roles: Admin, DevOps, Auditor.
    Password hashes only (never store plaintext passwords).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="Auditor")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    credentials: Mapped[List["Credential"]] = relationship(
        "Credential", back_populates="user"
    )
    requested_approvals: Mapped[List["RotationApproval"]] = relationship(
        "RotationApproval", foreign_keys="[RotationApproval.requested_by]", back_populates="requester"
    )
    approved_approvals: Mapped[List["RotationApproval"]] = relationship(
        "RotationApproval", foreign_keys="[RotationApproval.approved_by]", back_populates="approver"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
