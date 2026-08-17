"""
SecureRotate AI - Dependency Management & Impact Analysis API Router
Provides CRUD endpoints for application dependencies and rotation impact assessment endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.credential import Credential
from app.models.dependency import Dependency
from app.models.audit import AuditLog
from app.models.user import User
from app.api.dependencies.auth_dependencies import get_current_active_user, require_roles
from app.schemas.dependency import (
    DependencyCreate,
    DependencyUpdate,
    DependencyResponse,
    ImpactAnalysisResponse,
)

router = APIRouter()


def default_impact_score_from_criticality(criticality: str) -> float:
    """Derives default impact score from criticality level when score is not explicitly provided."""
    crit_upper = (criticality or "").strip().upper()
    if crit_upper == "LOW":
        return 0.25
    elif crit_upper == "MEDIUM":
        return 0.50
    elif crit_upper == "HIGH":
        return 0.75
    elif crit_upper == "CRITICAL":
        return 1.00
    return 0.50


# -----------------------------------------------------------------------------
# Dependency CRUD Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/dependencies",
    response_model=DependencyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Application Dependency",
    description="Registers a new downstream service dependency for a target database credential.",
)
async def create_dependency(
    payload: DependencyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DEVOPS"])),
) -> DependencyResponse:
    """Create dependency record and log audit event."""
    # Verify target credential exists
    cred_stmt = select(Credential).where(Credential.id == payload.credential_id)
    credential = (await db.execute(cred_stmt)).scalar_one_or_none()
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    impact_score = payload.impact_score
    if impact_score is None:
        impact_score = default_impact_score_from_criticality(payload.criticality)

    new_dependency = Dependency(
        credential_id=payload.credential_id,
        service_name=payload.service_name,
        service_type=payload.service_type,
        environment=payload.environment,
        criticality=payload.criticality.upper(),
        impact_score=impact_score,
        is_active=payload.is_active,
    )

    db.add(new_dependency)
    await db.flush()

    # Update dependency_count on parent Credential
    dep_count_stmt = select(Dependency).where(
        Dependency.credential_id == payload.credential_id,
        Dependency.is_active == True,
    )
    active_deps = (await db.execute(dep_count_stmt)).scalars().all()
    credential.dependency_count = len(active_deps)

    audit_entry = AuditLog(
        user_id=None,
        credential_id=payload.credential_id,
        event_type="DEPENDENCY_CREATED",
        action="CREATE",
        status="SUCCESS",
        details=f"Dependency '{new_dependency.service_name}' ({new_dependency.service_type}) created for credential ID {payload.credential_id}.",
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(new_dependency)

    return new_dependency


@router.get(
    "/dependencies",
    response_model=List[DependencyResponse],
    summary="List All Dependencies",
    description="Returns a list of all registered application dependencies.",
)
async def list_dependencies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[DependencyResponse]:
    """Retrieve all dependencies across credentials."""
    stmt = select(Dependency).order_by(Dependency.id.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/dependencies/{dependency_id}",
    response_model=DependencyResponse,
    summary="Get Single Dependency",
    description="Returns single dependency details by ID.",
)
async def get_dependency(
    dependency_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DependencyResponse:
    """Retrieve single dependency by ID."""
    stmt = select(Dependency).where(Dependency.id == dependency_id)
    dependency = (await db.execute(stmt)).scalar_one_or_none()

    if not dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency not found",
        )

    return dependency


@router.put(
    "/dependencies/{dependency_id}",
    response_model=DependencyResponse,
    summary="Update Dependency",
    description="Updates existing dependency properties and recalculates default impact score if criticality changes.",
)
async def update_dependency(
    dependency_id: int,
    payload: DependencyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DEVOPS"])),
) -> DependencyResponse:
    """Update dependency fields."""
    stmt = select(Dependency).where(Dependency.id == dependency_id)
    dependency = (await db.execute(stmt)).scalar_one_or_none()

    if not dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "criticality" and value is not None:
            setattr(dependency, field, value.upper())
        else:
            setattr(dependency, field, value)

    # Recalculate impact_score if criticality changed and score was not explicitly set
    if "criticality" in update_data and "impact_score" not in update_data:
        dependency.impact_score = default_impact_score_from_criticality(dependency.criticality)

    # Update parent credential's dependency_count
    dep_count_stmt = select(Dependency).where(
        Dependency.credential_id == dependency.credential_id,
        Dependency.is_active == True,
    )
    active_deps = (await db.execute(dep_count_stmt)).scalars().all()
    
    cred_stmt = select(Credential).where(Credential.id == dependency.credential_id)
    credential = (await db.execute(cred_stmt)).scalar_one_or_none()
    if credential:
        credential.dependency_count = len(active_deps)

    audit_entry = AuditLog(
        user_id=current_user.id,
        credential_id=dependency.credential_id,
        event_type="DEPENDENCY_UPDATED",
        action="UPDATE",
        status="SUCCESS",
        details=f"Dependency '{dependency.service_name}' (ID: {dependency_id}) updated successfully.",
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(dependency)

    return dependency


@router.delete(
    "/dependencies/{dependency_id}",
    summary="Delete Dependency",
    description="Deletes target service dependency and records audit log event.",
)
async def delete_dependency(
    dependency_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DEVOPS"])),
):
    """Delete dependency by ID."""
    stmt = select(Dependency).where(Dependency.id == dependency_id)
    dependency = (await db.execute(stmt)).scalar_one_or_none()

    if not dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency not found",
        )

    cred_id = dependency.credential_id
    service_name = dependency.service_name

    audit_entry = AuditLog(
        user_id=current_user.id,
        credential_id=cred_id,
        event_type="DEPENDENCY_DELETED",
        action="DELETE",
        status="SUCCESS",
        details=f"Dependency '{service_name}' (ID: {dependency_id}) deleted.",
    )
    db.add(audit_entry)
    await db.flush()

    await db.delete(dependency)

    # Update parent credential's dependency_count
    dep_count_stmt = select(Dependency).where(
        Dependency.credential_id == cred_id,
        Dependency.is_active == True,
        Dependency.id != dependency_id,
    )
    active_deps = (await db.execute(dep_count_stmt)).scalars().all()
    
    cred_stmt = select(Credential).where(Credential.id == cred_id)
    credential = (await db.execute(cred_stmt)).scalar_one_or_none()
    if credential:
        credential.dependency_count = len(active_deps)

    await db.commit()

    return {"message": "Dependency deleted successfully"}


# -----------------------------------------------------------------------------
# Credential-Scoped Dependency & Impact Analysis Endpoints
# -----------------------------------------------------------------------------

@router.get(
    "/credentials/{credential_id}/dependencies",
    response_model=List[DependencyResponse],
    summary="Get Credential Dependencies",
    description="Retrieves all downstream applications/services associated with a specific credential.",
)
async def get_credential_dependencies(
    credential_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[DependencyResponse]:
    """Retrieve all dependencies belonging to a specific credential."""
    cred_stmt = select(Credential).where(Credential.id == credential_id)
    credential = (await db.execute(cred_stmt)).scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    stmt = select(Dependency).where(
        Dependency.credential_id == credential_id
    ).order_by(Dependency.id.desc())
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/credentials/{credential_id}/impact",
    response_model=ImpactAnalysisResponse,
    summary="Get Rotation Impact Analysis",
    description="Analyzes downstream dependency count, impact scores, critical services, and overall rotation impact level.",
)
async def get_credential_impact_analysis(
    credential_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ImpactAnalysisResponse:

    """Calculate rotation impact analysis for a specific credential."""
    cred_stmt = select(Credential).where(Credential.id == credential_id)
    credential = (await db.execute(cred_stmt)).scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    impact_data = await analyze_credential_impact(db, credential_id)
    return ImpactAnalysisResponse(**impact_data)
