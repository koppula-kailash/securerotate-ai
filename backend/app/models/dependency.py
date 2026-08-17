"""
SecureRotate AI - Credential Dependency Model
Represents applications and microservices dependent on specific database credentials.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.credential import Credential


class Dependency(Base):
    """
    Dependency model for downstream applications or services using a credential.
    Helps evaluate rotation impact score and criticality.
    """

    __tablename__ = "dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    credential_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("credentials.id"), nullable=False, index=True
    )
    service_name: Mapped[str] = mapped_column(String(255), nullable=False)
    service_type: Mapped[str] = mapped_column(String(50), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    criticality: Mapped[str] = mapped_column(String(50), nullable=False, default="MEDIUM")
    impact_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    credential: Mapped["Credential"] = relationship(
        "Credential", back_populates="dependencies"
    )

    def __repr__(self) -> str:
        return (
            f"<Dependency(id={self.id}, service_name='{self.service_name}', "
            f"credential_id={self.credential_id})>"
        )
