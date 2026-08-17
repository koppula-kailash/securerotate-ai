"""
SecureRotate AI - Rotation Approval API Router
Handles human-in-the-loop authorization workflows for database credential rotation requests.
"""

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.credential import Credential
from app.models.dependency import Dependency
from app.models.approval import RotationApproval
from app.models.audit import AuditLog
from app.models.user import User
from app.api.dependencies.auth_dependencies import get_current_active_user, require_roles
from app.services.ml_risk_service import predict_credential_risk
from app.services.impact_analyzer import analyze_credential_impact
from app.schemas.approval import (
    RotationApprovalCreate,
    RotationApprovalReject,
    RotationApprovalResponse,
)

router = APIRouter()


# -----------------------------------------------------------------------------
# Rotation Request Creation Endpoint
# -----------------------------------------------------------------------------

@router.post(
    "/rotation-requests",
    response_model=RotationApprovalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Rotation Request",
    description="Submits a rotation approval request, evaluates risk & impact, and logs audit event.",
)
async def create_rotation_request(
    payload: RotationApprovalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DEVOPS"])),
) -> RotationApprovalResponse:
    """Create PENDING rotation approval after risk & impact evaluation."""
    cred_stmt = select(Credential).where(Credential.id == payload.credential_id)
    credential = (await db.execute(cred_stmt)).scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    now = datetime.now(timezone.utc)

    # 1. Evaluate current AI risk
    days_until_expiry = 30
    if credential.expires_at:
        exp = credential.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        days_until_expiry = max(1, int((exp - now).total_seconds() / 86400.0))

    dep_count_stmt = select(func.count(Dependency.id)).where(
        Dependency.credential_id == payload.credential_id,
        Dependency.is_active == True,
    )
    dep_count = (await db.execute(dep_count_stmt)).scalar() or 0

    risk_info = predict_credential_risk(
        days_until_expiry=days_until_expiry,
        credential_age_days=30,
        dependency_count=dep_count,
        privilege_level=credential.privilege_level,
        environment=credential.environment,
        access_frequency_per_day=credential.access_frequency or 10,
    )

    # 2. Evaluate dependency impact
    impact_info = await analyze_credential_impact(db, payload.credential_id)

    # 3. Create PENDING approval record
    approval = RotationApproval(
        credential_id=payload.credential_id,
        status="PENDING",
        reason=payload.reason or f"Rotation requested for {credential.name}",
        risk_score=risk_info["risk_score"],
        risk_level=risk_info["risk_level"],
        impact_score=impact_info["maximum_impact_score"],
        impact_level=impact_info["overall_impact_level"],
        requested_at=now,
    )
    db.add(approval)
    await db.flush()

    # 4. Create Audit Log entry
    audit_entry = AuditLog(
        user_id=current_user.id,
        credential_id=payload.credential_id,
        event_type="ROTATION_REQUESTED",
        action="REQUEST_ROTATION",
        status="SUCCESS",
        details=f"Rotation request ID {approval.id} submitted for credential '{credential.name}'.",
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(approval)

    return approval


# -----------------------------------------------------------------------------
# Approval Management Endpoints
# -----------------------------------------------------------------------------

@router.get(
    "/approvals",
    response_model=List[RotationApprovalResponse],
    summary="List Rotation Approvals",
    description="Returns list of all rotation approval workflows sorted by creation date.",
)
async def list_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[RotationApprovalResponse]:
    """Retrieve all rotation approval requests."""
    stmt = select(RotationApproval).order_by(RotationApproval.id.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/approvals/{approval_id}",
    response_model=RotationApprovalResponse,
    summary="Get Single Approval Request",
    description="Retrieves status and details of a single rotation approval request.",
)
async def get_approval(
    approval_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RotationApprovalResponse:
    """Retrieve single approval request by ID."""
    stmt = select(RotationApproval).where(RotationApproval.id == approval_id)
    approval = (await db.execute(stmt)).scalar_one_or_none()

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    return approval


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=RotationApprovalResponse,
    summary="Approve Rotation Request",
    description="Authorizes pending rotation request and sets approval timestamp.",
)
async def approve_rotation_request(
    approval_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DEVOPS"])),
) -> RotationApprovalResponse:
    """Approve PENDING rotation request (ADMIN and DEVOPS)."""
    stmt = select(RotationApproval).where(RotationApproval.id == approval_id)
    approval = (await db.execute(stmt)).scalar_one_or_none()

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    if approval.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve request with status '{approval.status}'. Request must be PENDING.",
        )

    now = datetime.now(timezone.utc)
    approval.status = "APPROVED"
    approval.approved_at = now
    approval.approved_by = current_user.id

    # Create Audit Log
    audit_entry = AuditLog(
        user_id=current_user.id,
        credential_id=approval.credential_id,
        event_type="ROTATION_APPROVED",
        action="APPROVE_ROTATION",
        status="SUCCESS",
        details=f"Rotation request ID {approval_id} APPROVED by '{current_user.username}'.",
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(approval)

    return approval


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=RotationApprovalResponse,
    summary="Reject Rotation Request",
    description="Rejects pending rotation request with required rejection reason.",
)
async def reject_rotation_request(
    approval_id: int,
    payload: RotationApprovalReject,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN"])),
) -> RotationApprovalResponse:
    """Reject PENDING rotation request with reason (ADMIN only)."""
    stmt = select(RotationApproval).where(RotationApproval.id == approval_id)
    approval = (await db.execute(stmt)).scalar_one_or_none()

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    if approval.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject request with status '{approval.status}'. Request must be PENDING.",
        )

    approval.status = "REJECTED"
    approval.rejection_reason = payload.rejection_reason

    # Create Audit Log
    audit_entry = AuditLog(
        user_id=current_user.id,
        credential_id=approval.credential_id,
        event_type="ROTATION_REJECTED",
        action="REJECT_ROTATION",
        status="SUCCESS",
        details=f"Rotation request ID {approval_id} REJECTED by '{current_user.username}'. Reason: '{payload.rejection_reason}'.",
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(approval)

    return approval

