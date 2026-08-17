"""
SecureRotate AI - Notification Database Model
Stores outgoing and dispatched alert notifications regarding credential expiry and rotation lifecycle events.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.credential import Credential


class Notification(Base):
    """
    Notification model tracking dispatched alerts and warnings.
    Types: EXPIRY_WARNING, HIGH_RISK_WARNING, CRITICAL_WARNING, ROTATION_SUCCESS, ROTATION_FAILED, EXPIRED
    Statuses: PENDING, SENT, FAILED
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    credential_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("credentials.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recipient: Mapped[str] = mapped_column(String(255), nullable=False, default="DBA Team")
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", index=True)

    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationship
    credential: Mapped[Optional["Credential"]] = relationship("Credential")

    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, credential_id={self.credential_id}, "
            f"type='{self.notification_type}', status='{self.status}')>"
        )
