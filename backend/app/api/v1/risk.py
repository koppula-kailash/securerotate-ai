"""
SecureRotate AI - AI Risk Engine API Router
Provides AI risk evaluation for specific credentials and aggregated system risk metrics overview.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.credential import Credential
from app.models.dependency import Dependency
from app.models.audit import AuditLog
from app.models.user import User
from app.api.dependencies.auth_dependencies import get_current_active_user
from app.services.ml_risk_service import predict_credential_risk, generate_recommendation_text

router = APIRouter()


@router.get(
    "/credentials/{credential_id}",
    summary="Evaluate Credential Risk via AI Model",
    description="Runs trained ML model, applies CRITICAL business rule, generates explanations, updates DB, and logs audit event.",
)
async def evaluate_credential_risk(
    credential_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Evaluates ML risk prediction, updates credential record, logs audit entry, and returns recommendation."""
    stmt = select(Credential).where(Credential.id == credential_id)
    credential = (await db.execute(stmt)).scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    now = datetime.now(timezone.utc)

    # 1. Calculate days_until_expiry
    if credential.expires_at:
        expires_at = credential.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        delta_days = (expires_at - now).total_seconds() / 86400.0
        days_until_expiry = max(1, int(delta_days))
    else:
        days_until_expiry = 90

    # 2. Calculate credential_age_days
    created_at = credential.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_delta = (now - created_at).total_seconds() / 86400.0
    credential_age_days = max(1, int(age_delta))

    # 3. Count active dependencies
    dep_stmt = select(func.count(Dependency.id)).where(
        Dependency.credential_id == credential_id,
        Dependency.is_active == True,
    )
    dependency_count = (await db.execute(dep_stmt)).scalar() or 0

    # 4. Count historical rotation failures from audit logs
    fail_stmt = select(func.count(AuditLog.id)).where(
        AuditLog.credential_id == credential_id,
        AuditLog.event_type == "ROTATION_FAILED",
    )
    historical_failures = (await db.execute(fail_stmt)).scalar() or 0

    # 5. Predict risk using ML service
    prediction = predict_credential_risk(
        days_until_expiry=days_until_expiry,
        credential_age_days=credential_age_days,
        dependency_count=dependency_count,
        privilege_level=credential.privilege_level,
        environment=credential.environment,
        historical_rotation_failures=historical_failures,
        access_frequency_per_day=credential.access_frequency or 10,
    )

    # 6. Generate human-readable recommendation text
    recommendation_text = generate_recommendation_text(
        credential_name=credential.name,
        risk_level=prediction["risk_level"],
        risk_score=prediction["risk_score"],
        days_until_expiry=days_until_expiry,
        environment=credential.environment,
        dependency_count=dependency_count,
        privilege_level=credential.privilege_level,
        historical_failures=historical_failures,
    )

    # 7. Update database credential record
    credential.risk_score = prediction["risk_score"]
    credential.risk_level = prediction["risk_level"]
    credential.updated_at = now

    # 8. Audit Logging
    audit_entry = AuditLog(
        user_id=None,
        credential_id=credential_id,
        event_type="RISK_CALCULATED",
        action="RISK_EVALUATION",
        status="SUCCESS",
        details=f"AI Risk evaluated for '{credential.name}': score={prediction['risk_score']}, level={prediction['risk_level']}, recommendation={prediction['recommendation']}.",
    )
    db.add(audit_entry)
    await db.commit()

    return {
        "credential_id": credential_id,
        "credential_name": credential.name,
        "risk_score": prediction["risk_score"],
        "risk_level": prediction["risk_level"],
        "risk_probability": prediction["risk_probability"],
        "confidence": prediction["confidence"],
        "reasons": prediction["reasons"],
        "recommendation": prediction["recommendation"],
        "recommendation_text": recommendation_text,
        "days_until_expiry": days_until_expiry,
        "dependency_count": dependency_count,
        "historical_failures": historical_failures,
        "environment": credential.environment,
        "privilege_level": credential.privilege_level,
    }


@router.get(
    "/overview",
    summary="Get System Risk Overview",
    description="Returns aggregated risk statistics across all managed database credentials.",
)
async def get_risk_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Retrieve simple system risk summary metrics."""
    stmt = select(Credential)
    result = await db.execute(stmt)
    credentials = list(result.scalars().all())

    total_credentials = len(credentials)
    if total_credentials == 0:
        return {
            "total_credentials": 0,
            "low_risk": 0,
            "medium_risk": 0,
            "high_risk": 0,
            "critical_risk": 0,
            "average_risk_score": 0.0,
        }

    low_risk = sum(1 for c in credentials if (c.risk_level or "").upper() == "LOW")
    medium_risk = sum(1 for c in credentials if (c.risk_level or "").upper() == "MEDIUM")
    high_risk = sum(1 for c in credentials if (c.risk_level or "").upper() == "HIGH")
    critical_risk = sum(1 for c in credentials if (c.risk_level or "").upper() == "CRITICAL")

    scores = [c.risk_score for c in credentials if c.risk_score is not None]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

    return {
        "total_credentials": total_credentials,
        "low_risk": low_risk,
        "medium_risk": medium_risk,
        "high_risk": high_risk,
        "critical_risk": critical_risk,
        "average_risk_score": avg_score,
    }
