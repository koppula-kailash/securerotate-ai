"""
SecureRotate AI - Rotation Approval Model
Tracks human authorization workflow for credential rotation requests.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.credential import Credential


class RotationApproval(Base):
    """
    RotationApproval model managing approval workflows.
    Allowed statuses: PENDING, APPROVED, REJECTED, CANCELLED.
    """

    __tablename__ = "rotation_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    credential_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("credentials.id"), nullable=False, index=True
    )
    requested_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    impact_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    impact_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    requested_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    credential: Mapped["Credential"] = relationship(
        "Credential", back_populates="approvals"
    )
    requester: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[requested_by], back_populates="requested_approvals"
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[approved_by], back_populates="approved_approvals"
    )

    def __repr__(self) -> str:
        return (
            f"<RotationApproval(id={self.id}, credential_id={self.credential_id}, "
            f"status='{self.status}')>"
        )
