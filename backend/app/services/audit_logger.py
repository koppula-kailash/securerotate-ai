"""
SecureRotate AI - Audit Logger Service
Provides reusable helper functions to record immutable audit trail records across services.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog


async def log_audit_event(
    db: AsyncSession,
    event_type: str,
    action: str,
    status: str,
    details: Optional[str] = None,
    user_id: Optional[int] = None,
    credential_id: Optional[int] = None,
) -> AuditLog:
    """Records an audit log entry within the active async database session."""
    entry = AuditLog(
        user_id=user_id,
        credential_id=credential_id,
        event_type=event_type,
        action=action,
        status=status,
        details=details,
    )
    db.add(entry)
    await db.flush()
    return entry
