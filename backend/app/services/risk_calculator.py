"""
SecureRotate AI - Unified Risk Calculation Service
Provides unified continuous risk scoring (0.0 to 1.0) and classification (LOW, MEDIUM, HIGH, CRITICAL).
Synchronized with ML risk engine for 100% telemetry consistency across Dashboard, Vault, and Risk Engine views.
"""

from datetime import datetime, timezone
from typing import Tuple, Optional
from app.services.ml_risk_service import predict_credential_risk


def calculate_risk_score(
    environment: str,
    privilege_level: str,
    expires_at: Optional[datetime] = None,
    dependency_count: int = 0,
    access_frequency: int = 10,
    historical_failures: int = 0,
) -> Tuple[float, str]:
    """
    Calculate credential risk using the unified ML & heuristic risk engine.
    
    Returns:
        (risk_score, risk_level)
        risk_score: 0.00 to 1.00
        risk_level: LOW, MEDIUM, HIGH, CRITICAL
    """
    now = datetime.now(timezone.utc)
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        delta_days = (expires_at - now).total_seconds() / 86400.0
        days_until_expiry = int(delta_days) if delta_days >= 0 else int(delta_days) - 1
    else:
        days_until_expiry = 90

    result = predict_credential_risk(
        days_until_expiry=days_until_expiry,
        credential_age_days=30,
        dependency_count=dependency_count,
        privilege_level=privilege_level,
        environment=environment,
        historical_rotation_failures=historical_failures,
        access_frequency_per_day=access_frequency,
    )

    return result["risk_score"], result["risk_level"]