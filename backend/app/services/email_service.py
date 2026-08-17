"""
SecureRotate AI - Dedicated Email Notification Service
Handles safe, non-blocking SMTP email dispatches for:
1. Login success alerts
2. Successful credential rotation alerts (WITHOUT plaintext passwords)
3. Failed rotation and rollback alerts
4. Expiry warning alerts (7-day, 3-day, 1-day, expired)

All functions strictly guarantee:
- Non-blocking execution: Email failures NEVER fail or interrupt the parent business operation.
- Zero password/secret exposure in emails, logs, or traces.
- Complete audit logging (LOGIN_EMAIL_SENT, ROTATION_EMAIL_SENT, EXPIRY_EMAIL_SENT, etc.).
"""

import logging
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.audit import AuditLog

logger = logging.getLogger("securerotate.email")


def _get_smtp_settings() -> Dict[str, Any]:
    """Extracts SMTP configurations with fallback alias support."""
    host = getattr(settings, "SMTP_HOST", None)
    port = int(getattr(settings, "SMTP_PORT", 587))
    user = getattr(settings, "SMTP_USERNAME", None) or getattr(settings, "SMTP_USER", None)
    password = getattr(settings, "SMTP_PASSWORD", None)
    from_email = (
        getattr(settings, "SMTP_FROM_EMAIL", None)
        or getattr(settings, "SMTP_FROM", None)
        or "alerts@securerotate.ai"
    )
    
    use_tls_val = getattr(settings, "SMTP_USE_TLS", None)
    if use_tls_val is not None:
        use_tls = bool(use_tls_val)
    else:
        use_tls = bool(getattr(settings, "SMTP_TLS", True))

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_email": from_email,
        "use_tls": use_tls,
    }


def send_raw_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends an email using standard Python smtplib.
    Never raises an exception; returns True on success and False on failure.
    """
    if not to_email or "@" not in str(to_email):
        logger.warning(f"Invalid email address provided: {to_email}")
        return False

    smtp_conf = _get_smtp_settings()
    host = smtp_conf["host"]

    if not host:
        logger.info(
            f"[MOCK EMAIL / LOG ONLY] (SMTP_HOST not configured)\n"
            f"To: {to_email}\nSubject: {subject}\n\n{body}"
        )
        return True

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_conf["from_email"]
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP(host, smtp_conf["port"], timeout=5) as server:
            if smtp_conf["use_tls"]:
                server.starttls()
            if smtp_conf["user"] and smtp_conf["password"]:
                server.login(smtp_conf["user"], smtp_conf["password"])
            server.send_message(msg)

        logger.info(f"Live SMTP email sent successfully to {to_email} with subject '{subject}'")
        return True
    except Exception as e:
        logger.warning(f"Live SMTP email delivery to {to_email} failed: {e}")
        return False


async def log_email_audit(
    event_type: str,
    action: str,
    status: str,
    details: str,
    user_id: Optional[int] = None,
    credential_id: Optional[int] = None,
) -> None:
    """Safely logs email audit events asynchronously without blocking caller."""
    try:
        async with AsyncSessionLocal() as session:
            entry = AuditLog(
                user_id=user_id,
                credential_id=credential_id,
                event_type=event_type,
                action=action,
                status=status,
                details=details,
            )
            session.add(entry)
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to record email audit log: {e}")


# =========================================================================
# FEATURE 1: LOGIN SUCCESS EMAIL
# =========================================================================
async def send_login_success_email(
    to_email: str,
    username: str,
    role: str,
    user_id: Optional[int] = None,
    timestamp: Optional[str] = None,
) -> bool:
    """
    Dispatches login success email to registered user upon successful authentication.
    """
    if not to_email:
        return False

    time_str = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = "SecureRotate AI — Successful Login"
    body = f"""Hello {username},

You have successfully logged into SecureRotate AI.

Time:
{time_str}

Role:
{role}

If this login was not performed by you, please contact the administrator.

SecureRotate AI
"""
    success = send_raw_email(to_email, subject, body)
    
    event_type = "LOGIN_EMAIL_SENT" if success else "LOGIN_EMAIL_FAILED"
    status_str = "SUCCESS" if success else "FAILED"
    details = f"Login notification email {'dispatched' if success else 'failed'} for user '{username}' ({to_email})."
    
    await log_email_audit(
        event_type=event_type,
        action="SEND_LOGIN_EMAIL",
        status=status_str,
        details=details,
        user_id=user_id,
    )
    return success


# =========================================================================
# FEATURE 3: SUCCESSFUL ROTATION EMAIL
# =========================================================================
async def send_rotation_success_email(
    to_email: str,
    credential_name: str,
    database_name: str,
    environment: str,
    latency_ms: float,
    rotated_at: Optional[str] = None,
    next_expiry: Optional[str] = None,
    risk_level: Optional[str] = "LOW",
    credential_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> bool:
    """
    Dispatches post-rotation success email to credential owner.
    Strictly excludes raw database passwords.
    """
    if not to_email:
        return False

    time_str = rotated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    expiry_str = next_expiry or "In 90 Days"
    latency_str = f"{latency_ms:.2f}" if isinstance(latency_ms, (int, float)) else str(latency_ms)

    subject = "SecureRotate AI — Credential Rotation Successful"
    body = f"""Hello,

The following credential was successfully rotated:

Credential:
{credential_name}

Database:
{database_name}

Environment:
{environment}

Rotation Status:
SUCCESS

Verification:
PASSED

Verification Latency:
{latency_str} ms

Rotated At:
{time_str}

Next Expiry:
{expiry_str}

Risk After Rotation:
{risk_level}

For security reasons, the newly generated database password is NOT included in email.

Please sign in to SecureRotate AI to securely access/manage the credential according to your role.

SecureRotate AI
"""
    success = send_raw_email(to_email, subject, body)
    
    event_type = "ROTATION_EMAIL_SENT" if success else "ROTATION_EMAIL_FAILED"
    status_str = "SUCCESS" if success else "FAILED"
    details = f"Rotation success email {'sent' if success else 'failed'} to owner {to_email} for credential '{credential_name}'."
    
    await log_email_audit(
        event_type=event_type,
        action="SEND_ROTATION_EMAIL",
        status=status_str,
        details=details,
        user_id=user_id,
        credential_id=credential_id,
    )
    return success


# =========================================================================
# FEATURE 4: FAILED ROTATION EMAIL
# =========================================================================
async def send_rotation_failed_email(
    to_email: str,
    credential_name: str,
    timestamp: Optional[str] = None,
    credential_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> bool:
    """
    Dispatches failed rotation and rollback notice to credential owner.
    """
    if not to_email:
        return False

    time_str = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = "SecureRotate AI — Credential Rotation Failed and Rolled Back"
    body = f"""The credential rotation attempt failed.

Credential:
{credential_name}

Status:
FAILED

Verification:
FAILED

Rollback:
SUCCESSFUL

Previous credential:
RESTORED

Time:
{time_str}

No new credential should be considered active.

Please review SecureRotate AI for details.

SecureRotate AI
"""
    success = send_raw_email(to_email, subject, body)
    
    event_type = "ROTATION_EMAIL_SENT" if success else "ROTATION_EMAIL_FAILED"
    status_str = "SUCCESS" if success else "FAILED"
    details = f"Rotation failure notice {'sent' if success else 'failed'} to owner {to_email} for credential '{credential_name}'."
    
    await log_email_audit(
        event_type=event_type,
        action="SEND_ROTATION_EMAIL",
        status=status_str,
        details=details,
        user_id=user_id,
        credential_id=credential_id,
    )
    return success


# =========================================================================
# FEATURE 5: EXPIRY ALERT EMAIL
# =========================================================================
async def send_expiry_alert_email(
    to_email: str,
    credential_name: str,
    days_remaining: int,
    risk_level: str,
    recommendation: str,
    credential_id: Optional[int] = None,
) -> bool:
    """
    Dispatches proactive expiry warning alert to credential owner.
    """
    if not to_email:
        return False

    if days_remaining <= 0:
        subject = "SecureRotate AI — Credential Expired"
        expires_str = "Expired"
    elif days_remaining == 1:
        subject = "SecureRotate AI — Credential Expires in 1 Day"
        expires_str = "1 day"
    else:
        subject = f"SecureRotate AI — Credential Expires in {days_remaining} Days"
        expires_str = f"{days_remaining} days"

    body = f"""Hello,

A database credential is approaching expiration:

Credential:
{credential_name}

Expires:
{expires_str}

Risk:
{risk_level}

Recommendation:
{recommendation}

Please sign in to SecureRotate AI to manage or rotate this credential.

SecureRotate AI
"""
    success = send_raw_email(to_email, subject, body)
    
    event_type = "EXPIRY_EMAIL_SENT" if success else "EXPIRY_EMAIL_FAILED"
    status_str = "SUCCESS" if success else "FAILED"
    details = f"Expiry alert email ({expires_str}) {'sent' if success else 'failed'} to owner {to_email} for '{credential_name}'."
    
    await log_email_audit(
        event_type=event_type,
        action="SEND_EXPIRY_EMAIL",
        status=status_str,
        details=details,
        credential_id=credential_id,
    )
    return success
