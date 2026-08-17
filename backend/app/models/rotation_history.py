"""
SecureRotate AI - Rotation History Database Model
Records every credential rotation attempt for historical tracking, analytics, and audit compliance.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.credential import Credential


class RotationHistory(Base):
    """
    RotationHistory model tracking every rotation attempt.
    Stores old/new expiry dates, trigger type, status, and failure details.
    """

    __tablename__ = "rotation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    credential_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("credentials.id", ondelete="CASCADE"), nullable=False, index=True
    )

    old_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    new_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    trigger_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="MANUAL"
    )  # MANUAL, SCHEDULED, AUTO, EMERGENCY
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="IN_PROGRESS"
    )  # IN_PROGRESS, SUCCESS, FAILED, ROLLED_BACK
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    risk_score_at_rotation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    verification_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    rotation_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationship
    credential: Mapped["Credential"] = relationship("Credential", back_populates="rotation_history")

    def __repr__(self) -> str:
        return (
            f"<RotationHistory(id={self.id}, credential_id={self.credential_id}, "
            f"status='{self.status}')>"
        )
