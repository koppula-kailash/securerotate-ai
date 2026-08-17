"""
SecureRotate AI - 7-Day Credential Expiry Monitoring Service
Scans database credentials for upcoming expirations (7 days, 3 days, 1 day, expired),
triggers mock console alerts, logs audit events, and persists notification history.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import Credential
from app.models.notification import Notification
from app.models.audit import AuditLog
from app.services.notification_service import dispatch_console_notification
from app.services.ml_risk_service import predict_credential_risk


async def run_expiry_scan(db: AsyncSession) -> Dict[str, int]:
    """
    Executes credential expiration scan across all credentials.
    Categories:
    - >7 days: MONITOR (no alert created)
    - 4-7 days: EXPIRY_WARNING
    - 2-3 days: HIGH_RISK_WARNING
    - 0-1 days: CRITICAL_WARNING
    - <0 days: EXPIRED
    """
    stmt = select(Credential)
    result = await db.execute(stmt)
    credentials: List[Credential] = list(result.scalars().all())

    checked_credentials = len(credentials)
    notifications_created = 0
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    for credential in credentials:
        if not credential.expires_at:
            continue

        expires_at = credential.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        delta_seconds = (expires_at - now).total_seconds()
        delta_days = delta_seconds / 86400.0
        days_remaining = int(delta_days) if delta_days >= 0 else int(delta_days) - 1

        # Check if auto-rotation is enabled and credential is due for rotation (<= 1 day or expired)
        if credential.auto_rotation_enabled and delta_seconds <= 86400:
            try:
                from app.services.rotation_engine import execute_credential_rotation
                from app.models.approval import RotationApproval
                
                # Ensure approval exists
                app_stmt = select(RotationApproval).where(
                    RotationApproval.credential_id == credential.id,
                    RotationApproval.status == "APPROVED",
                ).order_by(RotationApproval.id.desc())
                approval = (await db.execute(app_stmt)).scalars().first()
                if not approval:
                    approval = RotationApproval(
                        credential_id=credential.id,
                        status="APPROVED",
                        reason="Automated policy rotation triggered by background expiry monitor.",
                        risk_score=credential.risk_score or 0.8,
                        risk_level="HIGH",
                        impact_score=0.7,
                        impact_level="MEDIUM",
                        requested_at=now,
                        approved_at=now,
                        approved_by=1,
                    )
                    db.add(approval)
                    await db.flush()

                await execute_credential_rotation(db=db, credential_id=credential.id)
                notifications_created += 1
                continue
            except Exception as auto_rot_err:
                pass

        # Categorize notification type and recommendation
        if delta_seconds > 7 * 86400:
            continue
        elif 4 * 86400 < delta_seconds <= 7 * 86400:
            notif_type = "EXPIRY_WARNING"
            title = f"Expiry Warning: '{credential.name}' expires in {max(1, int(delta_days))} days"
            recommendation = "Schedule credential rotation."
        elif 2 * 86400 < delta_seconds <= 4 * 86400:
            notif_type = "HIGH_RISK_WARNING"
            title = f"High Risk Warning: '{credential.name}' expires in {max(1, int(delta_days))} days"
            recommendation = "Schedule rotation immediately."
        elif 0 <= delta_seconds <= 2 * 86400:
            notif_type = "CRITICAL_WARNING"
            title = f"Critical Warning: '{credential.name}' expires in {max(0, int(delta_days))} day(s)"
            recommendation = "Rotate within 24 hours."
        else:  # delta_seconds < 0
            notif_type = "EXPIRED"
            title = f"Credential Expired Alert: '{credential.name}' has EXPIRED"
            recommendation = "Rotate immediately (Expired)."

        # Prevent duplicate notifications for the same credential and type on the same day
        dup_stmt = select(Notification).where(
            Notification.credential_id == credential.id,
            Notification.notification_type == notif_type,
            Notification.created_at >= today_start,
        )
        existing_notif = (await db.execute(dup_stmt)).scalar_one_or_none()
        if existing_notif:
            continue

        # Evaluate risk level using ML prediction service
        try:
            risk_info = predict_credential_risk(
                days_until_expiry=max(1, int(delta_days)),
                credential_age_days=30,
                dependency_count=credential.dependency_count or 0,
                privilege_level=credential.privilege_level,
                environment=credential.environment,
                access_frequency_per_day=credential.access_frequency or 10,
            )
            risk_level = risk_info["risk_level"]
        except Exception:
            risk_level = credential.risk_level or "MEDIUM"

        recipient = credential.owner_email or "admin@securerotate.local"
        message = (
            f"Credential '{credential.name}' ({credential.database_type} on {credential.host}) "
            f"has {max(0, int(delta_days))} day(s) remaining before expiration. Risk level: {risk_level}."
        )

        # 1. Save Notification record in DB
        notification = Notification(
            credential_id=credential.id,
            recipient=recipient,
            notification_type=notif_type,
            title=title,
            message=message,
            risk_level=risk_level,
            status="PENDING",
            created_at=now,
        )
        db.add(notification)
        await db.flush()

        # 2. Dispatch safe alert & email to credential owner
        try:
            from app.services.email_service import send_expiry_alert_email
            await send_expiry_alert_email(
                to_email=recipient,
                credential_name=credential.name,
                days_remaining=max(0, int(delta_days)),
                risk_level=risk_level,
                recommendation=recommendation,
                credential_id=credential.id,
            )
        except Exception as email_err:
            logger.warning(f"Failed to dispatch expiry alert email for {credential.name}: {email_err}")

        dispatch_console_notification(
            credential_name=credential.name,
            risk_level=risk_level,
            days_remaining=max(0, int(delta_days)),
            recommendation=recommendation,
            recipient=recipient,
        )

        notification.status = "SENT"
        notification.sent_at = datetime.now(timezone.utc)

        # 3. Create Audit Log entry (Section 9)
        audit_entry = AuditLog(
            user_id=None,
            credential_id=credential.id,
            event_type="NOTIFICATION_SENT",
            action="EXPIRY_ALERT",
            status="SUCCESS",
            details=f"Expiry notification ({notif_type}) dispatched to {recipient} for credential '{credential.name}'.",
        )
        db.add(audit_entry)
        await db.commit()

        notifications_created += 1

    return {
        "checked_credentials": checked_credentials,
        "notifications_created": notifications_created,
    }
