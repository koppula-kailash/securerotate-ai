"""
SecureRotate AI - Audit Log API Router
Provides retrieval of immutable system audit logs.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.api.dependencies.auth_dependencies import get_current_active_user

from datetime import timezone

router = APIRouter()


@router.get(
    "/audit-logs",
    summary="List All Audit Logs",
    description="Returns full audit log trail sorted by creation date.",
)
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """Retrieve audit logs from MySQL database."""
    stmt = select(AuditLog).order_by(AuditLog.id.desc())
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    formatted_logs = []
    for log in logs:
        ts = None
        if log.created_at:
            dt = log.created_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ts = dt.isoformat()
            
        formatted_logs.append({
            "id": log.id,
            "credential_id": log.credential_id,
            "event_type": log.event_type,
            "action": log.action,
            "status": log.status,
            "details": log.details,
            "timestamp": ts,
            "created_at": ts,
        })
    return formatted_logs
