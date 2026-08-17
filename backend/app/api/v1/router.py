"""
SecureRotate AI - API v1 Router Aggregation
Aggregates modular API endpoint routers.
"""

from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.credentials import router as credentials_router
from app.api.v1.dependencies import router as dependencies_router
from app.api.v1.risk import router as risk_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.approvals import router as approvals_router
from app.api.v1.rotation import router as rotation_router
from app.api.v1.audit import router as audit_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["User Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["User Management"])
api_router.include_router(credentials_router, prefix="/credentials", tags=["Credentials"])
api_router.include_router(dependencies_router, tags=["Dependencies & Impact Analysis"])
api_router.include_router(risk_router, prefix="/risk", tags=["AI Risk Engine"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications & Alerts"])
api_router.include_router(approvals_router, tags=["Rotation Approvals & Requests"])
api_router.include_router(rotation_router, prefix="/rotation", tags=["Password Rotation Engine"])
api_router.include_router(audit_router, tags=["Audit Logs"])
