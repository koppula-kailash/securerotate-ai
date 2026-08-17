"""
SecureRotate AI - Dependency & Impact Analysis Schemas
Pydantic validation models for application dependency management and rotation impact analysis.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DependencyCreate(BaseModel):
    """Schema for creating a new service dependency on a credential."""
    credential_id: int = Field(..., description="ID of the target credential")
    service_name: str = Field(..., description="Name of dependent service or microservice")
    service_type: str = Field(..., description="Type of service (e.g. Backend API, Data Processing, Dashboard)")
    environment: str = Field(..., description="Environment (e.g. Production, Staging, Development)")
    criticality: str = Field("MEDIUM", description="Criticality level (LOW, MEDIUM, HIGH, CRITICAL)")
    impact_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Explicit impact score (0.0 to 1.0)")
    is_active: bool = Field(True, description="Active status indicator")


class DependencyUpdate(BaseModel):
    """Schema for updating dependency details."""
    service_name: Optional[str] = Field(None, description="Name of dependent service")
    service_type: Optional[str] = Field(None, description="Type of service")
    environment: Optional[str] = Field(None, description="Environment")
    criticality: Optional[str] = Field(None, description="Criticality level")
    impact_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Explicit impact score (0.0 to 1.0)")
    is_active: Optional[bool] = Field(None, description="Active status indicator")


class DependencyResponse(BaseModel):
    """Safe response model for single dependency details."""
    id: int
    credential_id: int
    service_name: str
    service_type: str
    environment: str
    criticality: str
    impact_score: Optional[float] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImpactAnalysisResponse(BaseModel):
    """Rotation Impact Analysis report for a target credential."""
    credential_id: int
    dependency_count: int
    maximum_impact_score: float
    average_impact_score: float
    critical_dependencies: List[str]
    overall_impact_level: str

    model_config = ConfigDict(from_attributes=True)
