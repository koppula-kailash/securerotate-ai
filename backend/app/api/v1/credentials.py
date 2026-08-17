"""
SecureRotate AI - Credential Management API Router
Implements CRUD operations for target database credentials with automated password encryption,
risk scoring, and audit logging.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.secret_provider import get_secret_provider
from app.services.risk_calculator import calculate_risk_score
from app.models.credential import Credential
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.models.dependency import Dependency
from app.models.approval import RotationApproval
from app.models.rotation_history import RotationHistory
from app.models.user import User
from app.api.dependencies.auth_dependencies import get_current_active_user, require_roles
from app.schemas.credential import (
    CredentialCreate,
    CredentialUpdate,
    CredentialResponse,
)

router = APIRouter()


@router.post(
    "",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Target Database Credential",
    description="Encrypts password, calculates risk score/level, stores record, and logs audit event.",
)
async def create_credential(
    payload: CredentialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DEVOPS"])),
) -> CredentialResponse:
    """Create a new database credential with Fernet password encryption and audit logging."""
    secret_provider = get_secret_provider("LOCAL")
    encrypted_pw = secret_provider.encrypt_secret(payload.password)

    owner_email = payload.owner_email.strip() if payload.owner_email else (current_user.email or "admin@securerotate.local")
    expires_at = payload.expires_at or (datetime.now(timezone.utc) + timedelta(days=90))

    risk_score, risk_level = calculate_risk_score(
        environment=payload.environment,
        privilege_level=payload.privilege_level,
        expires_at=expires_at,
    )

    new_credential = Credential(
        name=payload.name,
        database_type=payload.database_type,
        host=payload.host,
        port=payload.port,
        database_name=payload.database_name,
        username=payload.username,
        encrypted_password=encrypted_pw,
        environment=payload.environment,
        privilege_level=payload.privilege_level,
        risk_score=risk_score,
        risk_level=risk_level,
        status="ACTIVE",
        auto_rotation_enabled=payload.auto_rotation_enabled,
        owner_email=owner_email,
        expires_at=expires_at,
    )

    db.add(new_credential)
    await db.flush()  # Obtain new_credential.id for AuditLog FK link

    audit_entry = AuditLog(
        user_id=current_user.id,
        credential_id=new_credential.id,
        event_type="CREDENTIAL_CREATED",
        action="CREATE",
        status="SUCCESS",
        details=f"Credential '{new_credential.name}' created by user '{current_user.username}' with owner email '{owner_email}' and expiry '{expires_at.strftime('%Y-%m-%d')}'.",
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(new_credential)

    return new_credential


@router.get(
    "",
    response_model=List[CredentialResponse],
    summary="List All Managed Credentials",
    description="Returns a list of all database credentials. Passwords are strictly excluded.",
)
async def list_credentials(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[CredentialResponse]:
    """Retrieve all credentials with safe metadata only."""
    stmt = select(Credential).order_by(Credential.id.desc())
    result = await db.execute(stmt)
    credentials = result.scalars().all()
    return credentials


@router.get(
    "/dashboard-stats",
    summary="Get Dashboard Statistics",
    description="Returns aggregated stats for the dashboard: total DBs, healthy/warning/critical/expired counts, recent activity.",
)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Returns comprehensive dashboard statistics."""
    now = datetime.now(timezone.utc)

    # Fetch all credentials
    stmt = select(Credential).order_by(Credential.id.desc())
    result = await db.execute(stmt)
    credentials = list(result.scalars().all())

    total = len(credentials)
    healthy = 0
    warning = 0
    critical = 0
    expired = 0
    auto_rotation_count = 0
    upcoming_rotations = []

    for c in credentials:
        if c.auto_rotation_enabled:
            auto_rotation_count += 1

        days_val = None
        if c.expires_at:
            exp = c.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            days = (exp - now).total_seconds() / 86400.0
            days_val = max(0, int(days)) if days >= 0 else 0
            if days <= 0:
                expired += 1
            elif days <= 3:
                critical += 1
            elif days <= 7:
                warning += 1
            else:
                healthy += 1
        else:
            healthy += 1

        if days_val is not None and days_val <= 7:
            upcoming_rotations.append({
                "id": c.id,
                "name": c.name,
                "database_type": c.database_type,
                "environment": c.environment,
                "host": f"{c.host}:{c.port}",
                "days_remaining": days_val,
                "risk_level": c.risk_level or "MEDIUM",
                "auto_rotation_enabled": c.auto_rotation_enabled,
                "owner_email": c.owner_email or "admin@securerotate.local",
            })

    upcoming_rotations.sort(key=lambda x: x["days_remaining"])

    # Recent notifications
    notif_stmt = select(Notification).order_by(Notification.id.desc()).limit(5)
    recent_notifs = list((await db.execute(notif_stmt)).scalars().all())

    # Recent audit events
    audit_stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(10)
    recent_audits = list((await db.execute(audit_stmt)).scalars().all())

    # System health status
    if expired > 0:
        system_status = "CRITICAL"
    elif critical > 0:
        system_status = "AT_RISK"
    elif warning > 0:
        system_status = "WARNING"
    else:
        system_status = "HEALTHY"

    return {
        "total_databases": total,
        "healthy": healthy,
        "warning": warning,
        "critical": critical,
        "expired": expired,
        "auto_rotation_count": auto_rotation_count,
        "system_status": system_status,
        "upcoming_rotations": upcoming_rotations[:5],
        "recent_activity": [
            {
                "id": a.id,
                "event_type": a.event_type,
                "action": a.action,
                "status": a.status,
                "details": a.details,
                "timestamp": (
                    a.created_at.replace(tzinfo=timezone.utc).isoformat()
                    if a.created_at and a.created_at.tzinfo is None
                    else (a.created_at.isoformat() if a.created_at else None)
                ),
            }
            for a in recent_audits
        ],
    }


@router.get(
    "/{credential_id}",
    response_model=CredentialResponse,
    summary="Get Single Credential Metadata",
    description="Returns safe metadata for a single target credential by ID. Plaintext/encrypted passwords are excluded.",
)
async def get_credential(
    credential_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CredentialResponse:
    """Retrieve single credential metadata by ID."""
    stmt = select(Credential).where(Credential.id == credential_id)
    result = await db.execute(stmt)
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    return credential


@router.put(
    "/{credential_id}",
    response_model=CredentialResponse,
    summary="Update Credential",
    description="Updates existing credential parameters. Encrypts new password if provided and recalculates risk score.",
)
async def update_credential(
    credential_id: int,
    payload: CredentialUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DEVOPS"])),
) -> CredentialResponse:
    """Update target credential details and recalculate risk score."""
    stmt = select(Credential).where(Credential.id == credential_id)
    result = await db.execute(stmt)
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    # Handle password encryption if provided in update payload
    if "password" in update_data:
        raw_password = update_data.pop("password")
        if raw_password:
            secret_provider = get_secret_provider("LOCAL")
            credential.encrypted_password = secret_provider.encrypt_secret(raw_password)

    # Apply remaining updated fields to model instance
    for field, value in update_data.items():
        setattr(credential, field, value)

    # Recalculate risk score and level
    risk_score, risk_level = calculate_risk_score(
        environment=credential.environment,
        privilege_level=credential.privilege_level,
        expires_at=credential.expires_at,
    )
    credential.risk_score = risk_score
    credential.risk_level = risk_level
    credential.updated_at = datetime.now(timezone.utc)

    # Create audit log entry
    audit_entry = AuditLog(
        user_id=current_user.id,
        credential_id=credential.id,
        event_type="CREDENTIAL_UPDATED",
        action="UPDATE",
        status="SUCCESS",
        details=f"Credential '{credential.name}' updated successfully.",
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(credential)

    return credential


@router.delete(
    "/{credential_id}",
    summary="Delete Credential",
    description="Deletes target database credential and records audit log event.",
)
async def delete_credential(
    credential_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN"])),
):

    """Delete database credential by ID with pre-deletion audit logging."""
    stmt = select(Credential).where(Credential.id == credential_id)
    result = await db.execute(stmt)
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    # Create audit log entry before deletion
    audit_entry = AuditLog(
        user_id=current_user.id,
        credential_id=credential.id,
        event_type="CREDENTIAL_DELETED",
        action="DELETE",
        status="SUCCESS",
        details=f"Admin '{current_user.username}' deleted credential '{credential.name}' (ID: {credential_id}).",
    )
    db.add(audit_entry)
    await db.flush()

    await db.delete(credential)
    await db.commit()

    return {"message": "Credential deleted successfully"}


@router.post(
    "/seed-demo-data",
    summary="Seed Demo Data",
    description="Populates the database with 24 realistic demo credentials matching the hackathon demo breakdown (18 Healthy, 3 Warning, 2 Critical, 1 Expired).",
)
async def seed_demo_data(
    force: bool = False,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Seeds the database with 24 realistic demo databases and dependencies for hackathon presentation."""
    secret_provider = get_secret_provider("LOCAL")
    now = datetime.now(timezone.utc)

    # Check if data already exists
    existing = (await db.execute(select(Credential))).scalars().all()
    if len(existing) >= 20 and not force:
        return {"message": "Demo data already seeded", "credentials_count": len(existing)}

    if force:
        # Clear existing dependencies and credentials for clean slate
        await db.execute(Dependency.__table__.delete())
        await db.execute(RotationApproval.__table__.delete())
        await db.execute(AuditLog.__table__.delete())
        await db.execute(Notification.__table__.delete())
        await db.execute(RotationHistory.__table__.delete())
        await db.execute(Credential.__table__.delete())
        await db.commit()

    demo_credentials = [
        # === 2 CRITICAL (1-3 days) ===
        {
            "name": "Payment Gateway DB",
            "database_type": "MySQL",
            "host": "10.0.10.11",
            "port": 3306,
            "database_name": "payments_core_prod",
            "username": "pay_service_admin",
            "password": "demo_payment_pw_2026",
            "environment": "Production",
            "privilege_level": "ADMIN",
            "owner_email": "payments-dba@enterprise.io",
            "expires_at": now + timedelta(days=2),
            "dependency_count": 7,
            "access_frequency": 850,
        },
        {
            "name": "Subscription Billing DB",
            "database_type": "MySQL",
            "host": "10.0.10.12",
            "port": 3306,
            "database_name": "billing_ledger_prod",
            "username": "billing_exec_svc",
            "password": "demo_billing_pw_2026",
            "environment": "Production",
            "privilege_level": "HIGH",
            "owner_email": "finops-lead@enterprise.io",
            "expires_at": now + timedelta(days=1),
            "dependency_count": 5,
            "access_frequency": 620,
        },
        # === 3 WARNING (4-7 days) ===
        {
            "name": "Customer Identity DB",
            "database_type": "MySQL",
            "host": "10.0.10.14",
            "port": 3306,
            "database_name": "customer_directory_prod",
            "username": "cust_admin_user",
            "password": "demo_customer_pw_2026",
            "environment": "Production",
            "privilege_level": "HIGH",
            "owner_email": "iam-secops@enterprise.io",
            "expires_at": now + timedelta(days=7),
            "dependency_count": 3,
            "access_frequency": 320,
        },
        {
            "name": "Analytics & Telemetry DB",
            "database_type": "PostgreSQL",
            "host": "10.0.20.15",
            "port": 5432,
            "database_name": "analytics_telemetry_prod",
            "username": "analytics_pipeline",
            "password": "demo_analytics_pw_2026",
            "environment": "Production",
            "privilege_level": "MEDIUM",
            "owner_email": "data-eng@enterprise.io",
            "expires_at": now + timedelta(days=5),
            "dependency_count": 2,
            "access_frequency": 180,
        },
        {
            "name": "Order Processing DB",
            "database_type": "PostgreSQL",
            "host": "10.0.20.16",
            "port": 5432,
            "database_name": "orders_fulfillment_prod",
            "username": "order_fulfillment_mgr",
            "password": "demo_order_pw_2026",
            "environment": "Production",
            "privilege_level": "HIGH",
            "owner_email": "order-ops@enterprise.io",
            "expires_at": now + timedelta(days=6),
            "dependency_count": 4,
            "access_frequency": 420,
        },
        # === 1 EXPIRED (<0 days) ===
        {
            "name": "Legacy Warehouse DB",
            "database_type": "MySQL",
            "host": "10.0.30.99",
            "port": 3306,
            "database_name": "dw_legacy_archive",
            "username": "archive_warehouse_etl",
            "password": "demo_legacy_pw_2026",
            "environment": "Production",
            "privilege_level": "LOW",
            "owner_email": "legacy-admin@enterprise.io",
            "expires_at": now - timedelta(days=1),
            "dependency_count": 1,
            "access_frequency": 15,
        },
        # === 18 HEALTHY (>7 days) ===
        {
            "name": "HR Talent Vault",
            "database_type": "PostgreSQL",
            "host": "10.0.40.21",
            "port": 5432,
            "database_name": "hr_talent_test",
            "username": "hr_reader_svc",
            "password": "demo_hr_pw_2026",
            "environment": "Testing",
            "privilege_level": "LOW",
            "owner_email": "hr-compliance@enterprise.io",
            "expires_at": now + timedelta(days=27),
            "dependency_count": 1,
            "access_frequency": 45,
        },
        {
            "name": "Inventory Tracking DB",
            "database_type": "MySQL",
            "host": "10.0.40.22",
            "port": 3306,
            "database_name": "inventory_tracking_stg",
            "username": "inv_stock_worker",
            "password": "demo_inventory_pw_2026",
            "environment": "Staging",
            "privilege_level": "MEDIUM",
            "owner_email": "inventory-ops@enterprise.io",
            "expires_at": now + timedelta(days=45),
            "dependency_count": 2,
            "access_frequency": 95,
        },
        {
            "name": "IAM Auth Master DB",
            "database_type": "PostgreSQL",
            "host": "10.0.10.50",
            "port": 5432,
            "database_name": "iam_auth_prod",
            "username": "iam_auth_super",
            "password": "demo_auth_pw_2026",
            "environment": "Production",
            "privilege_level": "ADMIN",
            "owner_email": "iam-admin@enterprise.io",
            "expires_at": now + timedelta(days=60),
            "dependency_count": 6,
            "access_frequency": 890,
        },
        {
            "name": "System Audit Logging DB",
            "database_type": "MySQL",
            "host": "10.0.50.15",
            "port": 3306,
            "database_name": "sys_audit_logs_dev",
            "username": "sys_log_writer",
            "password": "demo_logs_pw_2026",
            "environment": "Development",
            "privilege_level": "LOW",
            "owner_email": "audit-team@enterprise.io",
            "expires_at": now + timedelta(days=90),
            "dependency_count": 1,
            "access_frequency": 30,
        },
        {
            "name": "Push Notifications DB",
            "database_type": "PostgreSQL",
            "host": "10.0.20.25",
            "port": 5432,
            "database_name": "push_notifications_prod",
            "username": "push_dispatcher_app",
            "password": "demo_notif_pw_2026",
            "environment": "Production",
            "privilege_level": "MEDIUM",
            "owner_email": "messaging-team@enterprise.io",
            "expires_at": now + timedelta(days=35),
            "dependency_count": 2,
            "access_frequency": 210,
        },
        {
            "name": "User Profiles & Preferences DB",
            "database_type": "MySQL",
            "host": "10.0.10.33",
            "port": 3306,
            "database_name": "user_pref_prod",
            "username": "user_pref_svc",
            "password": "demo_profile_pw_2026",
            "environment": "Production",
            "privilege_level": "HIGH",
            "owner_email": "user-platform@enterprise.io",
            "expires_at": now + timedelta(days=40),
            "dependency_count": 3,
            "access_frequency": 480,
        },
        {
            "name": "E-Commerce Product Catalog",
            "database_type": "PostgreSQL",
            "host": "10.0.20.40",
            "port": 5432,
            "database_name": "product_catalog_prod",
            "username": "catalog_indexer",
            "password": "demo_catalog_pw_2026",
            "environment": "Production",
            "privilege_level": "MEDIUM",
            "owner_email": "catalog-ops@enterprise.io",
            "expires_at": now + timedelta(days=50),
            "dependency_count": 3,
            "access_frequency": 390,
        },
        {
            "name": "AI Recommendation Store",
            "database_type": "PostgreSQL",
            "host": "10.0.40.45",
            "port": 5432,
            "database_name": "ai_recs_model_stg",
            "username": "recs_model_worker",
            "password": "demo_recs_pw_2026",
            "environment": "Staging",
            "privilege_level": "LOW",
            "owner_email": "ml-ops@enterprise.io",
            "expires_at": now + timedelta(days=55),
            "dependency_count": 1,
            "access_frequency": 75,
        },
        {
            "name": "Cart & Checkout DB",
            "database_type": "MySQL",
            "host": "10.0.10.42",
            "port": 3306,
            "database_name": "checkout_sessions_prod",
            "username": "checkout_session_mgr",
            "password": "demo_cart_pw_2026",
            "environment": "Production",
            "privilege_level": "HIGH",
            "owner_email": "ecommerce-ops@enterprise.io",
            "expires_at": now + timedelta(days=65),
            "dependency_count": 4,
            "access_frequency": 530,
        },
        {
            "name": "Search Engine Index Store",
            "database_type": "MySQL",
            "host": "10.0.50.28",
            "port": 3306,
            "database_name": "search_indexer_dev",
            "username": "search_crawler_bot",
            "password": "demo_search_pw_2026",
            "environment": "Development",
            "privilege_level": "LOW",
            "owner_email": "search-infra@enterprise.io",
            "expires_at": now + timedelta(days=80),
            "dependency_count": 1,
            "access_frequency": 40,
        },
        {
            "name": "Security Audit Archive DB",
            "database_type": "PostgreSQL",
            "host": "10.0.10.90",
            "port": 5432,
            "database_name": "compliance_vault_prod",
            "username": "compliance_auditor",
            "password": "demo_audit_pw_2026",
            "environment": "Production",
            "privilege_level": "ADMIN",
            "owner_email": "infosec-audit@enterprise.io",
            "expires_at": now + timedelta(days=75),
            "dependency_count": 2,
            "access_frequency": 110,
        },
        {
            "name": "Fraud Detection Engine DB",
            "database_type": "MySQL",
            "host": "10.0.10.58",
            "port": 3306,
            "database_name": "fraud_shield_prod",
            "username": "fraud_shield_eval",
            "password": "demo_fraud_pw_2026",
            "environment": "Production",
            "privilege_level": "HIGH",
            "owner_email": "fraud-monitoring@enterprise.io",
            "expires_at": now + timedelta(days=42),
            "dependency_count": 3,
            "access_frequency": 360,
        },
        {
            "name": "Partner & Vendor Portal DB",
            "database_type": "PostgreSQL",
            "host": "10.0.40.62",
            "port": 5432,
            "database_name": "vendor_collab_test",
            "username": "vendor_api_gateway",
            "password": "demo_vendor_pw_2026",
            "environment": "Testing",
            "privilege_level": "LOW",
            "owner_email": "partner-eng@enterprise.io",
            "expires_at": now + timedelta(days=30),
            "dependency_count": 1,
            "access_frequency": 50,
        },
        {
            "name": "Shipping & Logistics Hub",
            "database_type": "MySQL",
            "host": "10.0.10.65",
            "port": 3306,
            "database_name": "logistics_dispatch_prod",
            "username": "logistics_dispatcher",
            "password": "demo_ship_pw_2026",
            "environment": "Production",
            "privilege_level": "MEDIUM",
            "owner_email": "logistics-team@enterprise.io",
            "expires_at": now + timedelta(days=38),
            "dependency_count": 3,
            "access_frequency": 290,
        },
        {
            "name": "Dynamic Pricing Engine DB",
            "database_type": "PostgreSQL",
            "host": "10.0.20.72",
            "port": 5432,
            "database_name": "pricing_matrix_prod",
            "username": "pricing_engine_svc",
            "password": "demo_pricing_pw_2026",
            "environment": "Production",
            "privilege_level": "HIGH",
            "owner_email": "pricing-algo@enterprise.io",
            "expires_at": now + timedelta(days=48),
            "dependency_count": 2,
            "access_frequency": 310,
        },
        {
            "name": "Customer Support Tickets DB",
            "database_type": "MySQL",
            "host": "10.0.40.75",
            "port": 3306,
            "database_name": "support_tickets_stg",
            "username": "support_desk_bot",
            "password": "demo_support_pw_2026",
            "environment": "Staging",
            "privilege_level": "LOW",
            "owner_email": "support-infra@enterprise.io",
            "expires_at": now + timedelta(days=70),
            "dependency_count": 1,
            "access_frequency": 80,
        },
        {
            "name": "BI Reporting Data Mart",
            "database_type": "PostgreSQL",
            "host": "10.0.20.88",
            "port": 5432,
            "database_name": "bi_executive_datamart",
            "username": "bi_report_reader",
            "password": "demo_bi_pw_2026",
            "environment": "Production",
            "privilege_level": "MEDIUM",
            "owner_email": "bi-reporting@enterprise.io",
            "expires_at": now + timedelta(days=85),
            "dependency_count": 2,
            "access_frequency": 160,
        },
        {
            "name": "Mobile API Response Cache DB",
            "database_type": "MySQL",
            "host": "10.0.50.44",
            "port": 3306,
            "database_name": "mobile_cache_dev",
            "username": "mobile_cache_client",
            "password": "demo_cache_pw_2026",
            "environment": "Development",
            "privilege_level": "LOW",
            "owner_email": "mobile-leads@enterprise.io",
            "expires_at": now + timedelta(days=60),
            "dependency_count": 1,
            "access_frequency": 25,
        },
    ]

    created_creds = []
    for cred_data in demo_credentials:
        raw_pw = cred_data.pop("password")
        encrypted_pw = secret_provider.encrypt_secret(raw_pw)

        risk_score, risk_level = calculate_risk_score(
            environment=cred_data["environment"],
            privilege_level=cred_data["privilege_level"],
            expires_at=cred_data.get("expires_at"),
        )

        cred = Credential(
            encrypted_password=encrypted_pw,
            risk_score=risk_score,
            risk_level=risk_level,
            status="ACTIVE",
            auto_rotation_enabled=False,
            **cred_data,
        )
        db.add(cred)
        await db.flush()
        created_creds.append(cred)

        # Audit log
        db.add(AuditLog(
            credential_id=cred.id,
            event_type="CREDENTIAL_CREATED",
            action="CREATE",
            status="SUCCESS",
            details=f"Credential '{cred.name}' registered for {cred.environment}.",
        ))

    # Add rich downstream microservice dependencies for multiple databases
    demo_deps_map = {
        # Payment DB
        0: [
            {"service_name": "Payment Gateway API", "service_type": "REST API", "environment": "Production", "criticality": "CRITICAL", "impact_score": 1.0},
            {"service_name": "Invoice Processing Worker", "service_type": "Async Worker", "environment": "Production", "criticality": "CRITICAL", "impact_score": 0.95},
            {"service_name": "Billing Reconciliation Svc", "service_type": "Microservice", "environment": "Production", "criticality": "HIGH", "impact_score": 0.85},
            {"service_name": "Mobile Checkout Gateway", "service_type": "API Gateway", "environment": "Production", "criticality": "HIGH", "impact_score": 0.80},
            {"service_name": "Customer Portal Billing", "service_type": "Web Application", "environment": "Production", "criticality": "HIGH", "impact_score": 0.75},
            {"service_name": "Financial Ledger Exporter", "service_type": "Data Pipeline", "environment": "Production", "criticality": "MEDIUM", "impact_score": 0.65},
            {"service_name": "Tax Calculation Microservice", "service_type": "Microservice", "environment": "Production", "criticality": "MEDIUM", "impact_score": 0.60},
        ],
        # Billing DB
        1: [
            {"service_name": "Subscription Billing Engine", "service_type": "Background Worker", "environment": "Production", "criticality": "CRITICAL", "impact_score": 0.95},
            {"service_name": "Stripe Webhook Handler", "service_type": "Webhook Worker", "environment": "Production", "criticality": "CRITICAL", "impact_score": 0.90},
            {"service_name": "Invoice PDF Generator", "service_type": "Microservice", "environment": "Production", "criticality": "HIGH", "impact_score": 0.75},
            {"service_name": "Accounts Receivable Dashboard", "service_type": "Web App", "environment": "Production", "criticality": "MEDIUM", "impact_score": 0.60},
            {"service_name": "Dunning Email Notifier", "service_type": "Queue Consumer", "environment": "Production", "criticality": "MEDIUM", "impact_score": 0.50},
        ],
        # Customer DB
        2: [
            {"service_name": "Customer Web Portal", "service_type": "Web Application", "environment": "Production", "criticality": "CRITICAL", "impact_score": 0.95},
            {"service_name": "CRM Sync Service", "service_type": "Microservice", "environment": "Production", "criticality": "HIGH", "impact_score": 0.80},
            {"service_name": "Marketing Email Worker", "service_type": "Async Queue", "environment": "Production", "criticality": "MEDIUM", "impact_score": 0.55},
        ],
        # Analytics DB
        3: [
            {"service_name": "Executive KPI Dashboard", "service_type": "BI Tool", "environment": "Production", "criticality": "HIGH", "impact_score": 0.80},
            {"service_name": "Daily Nightly ETL Pipeline", "service_type": "Data Pipeline", "environment": "Production", "criticality": "MEDIUM", "impact_score": 0.65},
        ],
        # Order Processing DB
        4: [
            {"service_name": "Order Ingestion API", "service_type": "REST API", "environment": "Production", "criticality": "CRITICAL", "impact_score": 0.95},
            {"service_name": "Warehouse Fulfillment Dispatcher", "service_type": "Microservice", "environment": "Production", "criticality": "HIGH", "impact_score": 0.85},
            {"service_name": "Inventory Deduplication Worker", "service_type": "Background Worker", "environment": "Production", "criticality": "HIGH", "impact_score": 0.80},
            {"service_name": "Shipping Label Generator", "service_type": "Microservice", "environment": "Production", "criticality": "MEDIUM", "impact_score": 0.60},
        ],
    }

    # Populate dependencies across all credentials
    for idx, cred in enumerate(created_creds):
        deps = demo_deps_map.get(idx)
        if not deps:
            # Generate 2 standard microservice dependencies for remaining databases
            deps = [
                {"service_name": f"{cred.name} Core Service", "service_type": "Backend Service", "environment": cred.environment, "criticality": "HIGH" if "PROD" in cred.environment.upper() else "MEDIUM", "impact_score": 0.70},
                {"service_name": f"{cred.name} Reporter", "service_type": "Background Worker", "environment": cred.environment, "criticality": "LOW", "impact_score": 0.35},
            ]
        for d in deps:
            db.add(Dependency(credential_id=cred.id, is_active=True, **d))

    # Add initial notification for Payment Gateway DB
    if created_creds:
        first_cred = created_creds[0]
        db.add(Notification(
            credential_id=first_cred.id,
            recipient="DBA Team, Finance IT, Security Ops",
            notification_type="HIGH_RISK_WARNING",
            title=f"High Risk Warning: '{first_cred.name}' expires in 2 days",
            message=f"Credential '{first_cred.name}' ({first_cred.database_type} on {first_cred.host}) expires in 2 days. Production database with 7 downstream dependencies at risk.",
            risk_level="CRITICAL",
            status="SENT",
            sent_at=now,
        ))

    await db.commit()

    return {
        "message": "Demo data seeded successfully (24 enterprise databases)",
        "credentials_count": len(created_creds),
        "breakdown": {
            "total": 24,
            "healthy": 18,
            "warning": 3,
            "critical": 2,
            "expired": 1,
        },
    }

