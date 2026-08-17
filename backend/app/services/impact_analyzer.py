"""
SecureRotate AI - Credential Rotation Impact Analysis Service
Calculates potential operational impact score, identifies critical downstream microservices,
and determines overall rotation risk level.
"""

from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dependency import Dependency


async def analyze_credential_impact(
    db: AsyncSession,
    credential_id: int,
) -> Dict[str, Any]:
    """
    Analyzes all active downstream dependencies for a given credential.
    
    Returns:
    - dependency_count: Total count of active dependent services
    - maximum_impact_score: Highest single impact score among dependencies
    - average_impact_score: Mean impact score across active dependencies
    - critical_dependencies: List of service names marked CRITICAL
    - overall_impact_level: Classification (LOW, MEDIUM, HIGH, CRITICAL)
    """
    stmt = select(Dependency).where(
        Dependency.credential_id == credential_id,
        Dependency.is_active == True,
    )
    result = await db.execute(stmt)
    dependencies: List[Dependency] = list(result.scalars().all())

    if not dependencies:
        return {
            "credential_id": credential_id,
            "dependency_count": 0,
            "maximum_impact_score": 0.0,
            "average_impact_score": 0.0,
            "critical_dependencies": [],
            "overall_impact_level": "LOW",
        }

    scores = [
        dep.impact_score if dep.impact_score is not None else 0.50
        for dep in dependencies
    ]

    max_score = round(max(scores), 2)
    avg_score = round(sum(scores) / len(scores), 2)

    critical_services = [
        dep.service_name
        for dep in dependencies
        if (dep.criticality or "").strip().upper() == "CRITICAL"
        or (dep.impact_score is not None and dep.impact_score >= 0.90)
    ]

    # Classification logic based on average impact score
    if avg_score < 0.40:
        overall_level = "LOW"
    elif avg_score < 0.70:
        overall_level = "MEDIUM"
    elif avg_score < 0.90:
        overall_level = "HIGH"
    else:
        overall_level = "CRITICAL"

    # Rule: Any CRITICAL downstream dependency elevates overall impact to at least HIGH
    if critical_services and overall_level in ["LOW", "MEDIUM"]:
        overall_level = "HIGH"

    return {
        "credential_id": credential_id,
        "dependency_count": len(dependencies),
        "maximum_impact_score": max_score,
        "average_impact_score": avg_score,
        "critical_dependencies": critical_services,
        "overall_impact_level": overall_level,
    }
