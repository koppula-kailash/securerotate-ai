"""
SecureRotate AI - Risk Engine Schemas
Defines request validation and response models for risk scoring and ML prediction.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RiskPredictionRequest(BaseModel):
    """Input features for machine learning risk evaluation."""
    days_until_expiry: int = Field(..., ge=0, description="Days remaining before expiry")
    credential_age_days: int = Field(30, ge=0, description="Age of current credential in days")
    dependency_count: int = Field(0, ge=0, description="Number of downstream services dependent on this credential")
    privilege_level: str = Field("LOW", description="Privilege level: LOW, MEDIUM, HIGH, ADMIN")
    environment: str = Field("Production", description="Deployment environment: Production, Staging, Testing, Development")
    access_frequency_per_day: int = Field(10, ge=0, description="Estimated queries/connections per day")


class RiskPredictionResponse(BaseModel):
    """Output prediction from the AI risk engine."""
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    recommendation: str
    feature_importance: Optional[Dict[str, float]] = None

    model_config = ConfigDict(from_attributes=True)


class RiskOverviewResponse(BaseModel):
    """Aggregated risk profile across all managed credentials."""
    total_credentials: int
    low_risk_count: int
    medium_risk_count: int
    high_risk_count: int
    critical_risk_count: int
    average_risk_score: float

    model_config = ConfigDict(from_attributes=True)
