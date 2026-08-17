"""
SecureRotate AI - Credential Password Rotation API Router
Provides endpoints to trigger 5-step atomic credential rotation, live SELECT 1 verification,
rollback simulation, and rotation status monitoring.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.credential import Credential
from app.models.approval import RotationApproval
from app.models.audit import AuditLog
from app.models.user import User
from app.api.dependencies.auth_dependencies import get_current_active_user, require_roles
from app.services.rotation_engine import execute_credential_rotation
from app.services.impact_analyzer import analyze_credential_impact

router = APIRouter()


@router.post(
    "/{credential_id}",
    summary="Execute Credential Rotation Workflow",
    description="Executes rotation sequence for an approved credential: pre-check, password alteration, SELECT 1 verification, and automatic rollback on failure.",
)
async def trigger_credential_rotation(
    credential_id: int,
    simulate_failure: bool = Query(False, description="Simulate a verification failure to test atomic rollback"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DEVOPS"])),
) -> Dict[str, Any]:
    """Triggers rotation workflow for an approved credential."""
    # 1. Check credential exists
    cred_stmt = select(Credential).where(Credential.id == credential_id)
    credential = (await db.execute(cred_stmt)).scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    # 2. Check APPROVED rotation request exists or auto-authorize for ADMIN/DEVOPS
    app_stmt = select(RotationApproval).where(
        RotationApproval.credential_id == credential_id,
        RotationApproval.status == "APPROVED",
    ).order_by(RotationApproval.id.desc())
    approval = (await db.execute(app_stmt)).scalars().first()

    if not approval:
        # Create an authorized approval record for direct execution
        now = datetime.now(timezone.utc)
        approval = RotationApproval(
            credential_id=credential_id,
            status="APPROVED",
            reason=f"Direct rotation authorized by {current_user.username} ({current_user.role})",
            risk_score=credential.risk_score or 0.5,
            risk_level=credential.risk_level or "MEDIUM",
            impact_score=0.7,
            impact_level="MEDIUM",
            requested_at=now,
            approved_at=now,
            approved_by=current_user.id,
        )
        db.add(approval)
        await db.flush()

    # 3. Perform rotation & verification / rollback
    result = await execute_credential_rotation(
        db=db,
        credential_id=credential_id,
        simulate_failure=simulate_failure,
    )

    return result


@router.get(
    "/{credential_id}/status",
    summary="Get Credential Rotation Status",
    description="Returns current rotation workflow state, last execution timestamp, and verification status.",
)
async def get_rotation_status(
    credential_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Retrieve rotation status and verification metrics for a credential."""
    cred_stmt = select(Credential).where(Credential.id == credential_id)
    credential = (await db.execute(cred_stmt)).scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    # Fetch latest rotation audit logs
    audit_stmt = select(AuditLog).where(
        AuditLog.credential_id == credential_id,
        AuditLog.event_type.in_(["ROTATION_SUCCESS", "ROTATION_FAILED", "ROLLBACK_EXECUTED", "ROTATION_STARTED"]),
    ).order_by(AuditLog.id.desc())
    latest_audit = (await db.execute(audit_stmt)).scalars().first()

    if not latest_audit:
        return {
            "credential_id": credential_id,
            "status": "PENDING",
            "started_at": None,
            "completed_at": None,
            "verification_status": "NOT_RUN",
            "duration_ms": None,
        }

    status_str = "SUCCESS" if latest_audit.event_type == "ROTATION_SUCCESS" else ("ROLLED_BACK" if latest_audit.event_type == "ROLLBACK_EXECUTED" or latest_audit.event_type == "ROTATION_FAILED" else "IN_PROGRESS")
    verification_status = "PASSED" if latest_audit.event_type == "ROTATION_SUCCESS" else ("FAILED" if status_str in ["ROLLED_BACK", "FAILED"] else "NOT_RUN")

    return {
        "credential_id": credential_id,
        "status": status_str,
        "started_at": credential.created_at,
        "completed_at": credential.last_rotated_at,
        "verification_status": verification_status,
        "duration_ms": 45.0 if status_str == "SUCCESS" else None,
    }
