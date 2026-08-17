"""
SecureRotate AI - System & Database Health Monitoring Endpoint
"""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.db.session import check_database_connection

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    database: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API & MySQL Database Health",
    description="Verifies the operational status of the FastAPI backend and live MySQL connection.",
)
async def get_health(response: Response) -> HealthResponse:
    """
    Executes a database connectivity check.
    Returns sanitized status. Passwords, connection details, and stack traces are strictly excluded.
    """
    is_connected = await check_database_connection()

    if is_connected:
        return HealthResponse(status="healthy", database="connected")
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unhealthy", database="disconnected")
