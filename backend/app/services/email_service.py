"""
SecureRotate AI - Dedicated Email Notification Service

Handles safe, non-blocking email dispatches for:

1. Login success alerts
2. Successful credential rotation alerts
3. Failed rotation and rollback alerts
4. Expiry warning alerts

Email provider:
- Resend HTTPS API

Security guarantees:
- Email failures never interrupt the parent business operation.
- Passwords and secrets are never included in emails.
- Passwords and secrets are never logged.
- Email audit events are recorded independently.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from zoneinfo import ZoneInfo

import resend

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.audit import AuditLog


logger = logging.getLogger("securerotate.email")


# =========================================================================
# TIMEZONE CONFIGURATION
# =========================================================================

# Backend/database timestamps remain stored in UTC.
# Only timestamps displayed in emails are converted to IST.
DISPLAY_TIMEZONE = ZoneInfo("Asia/Kolkata")
DISPLAY_TIMEZONE_NAME = "IST"


def _format_email_datetime(
    timestamp: Optional[str] = None,
) -> str:
    """
    Convert a timestamp to the configured email display timezone.

    Backend/database timestamps remain UTC.
    Email timestamps are displayed in IST.

    Supports:
    - ISO timestamps with Z
    - ISO timestamps with +00:00
    - ISO timestamps without timezone information
    - datetime objects
    - None
    """

    try:
        if timestamp is None:
            dt = datetime.now(timezone.utc)

        elif isinstance(timestamp, datetime):
            dt = timestamp

        else:
            timestamp_str = str(timestamp).strip()

            # Convert trailing Z into a Python-compatible UTC offset.
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1] + "+00:00"

            dt = datetime.fromisoformat(timestamp_str)

        # If the timestamp has no timezone information,
        # treat it as UTC because the application stores UTC.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Convert UTC-aware datetime to IST.
        local_dt = dt.astimezone(DISPLAY_TIMEZONE)

        return local_dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        ) + f" {DISPLAY_TIMEZONE_NAME}"

    except (ValueError, TypeError, OverflowError):
        # Never allow email formatting problems to interrupt
        # the parent business operation.
        logger.warning(
            "Unable to format email timestamp; "
            "falling back to UTC."
        )

        return datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )


# =========================================================================
# RESEND CONFIGURATION
# =========================================================================

def _get_resend_settings() -> Dict[str, Any]:
    """
    Returns the Resend configuration.

    The API key is only used internally and is never returned,
    logged, or included in email content.
    """

    api_key = getattr(
        settings,
        "RESEND_API_KEY",
        None,
    )

    from_email = (
        getattr(
            settings,
            "RESEND_FROM_EMAIL",
            None,
        )
        or "onboarding@resend.dev"
    )

    return {
        "api_key": api_key,
        "from_email": from_email,
    }


# =========================================================================
# LOW-LEVEL EMAIL DISPATCH
# =========================================================================

async def send_raw_email(
    to_email: str,
    subject: str,
    body: str,
) -> bool:
    """
    Sends an email through the Resend HTTPS API.

    Never raises an exception.

    Returns:
        True  = Resend accepted the email
        False = email delivery/submission failed

    No passwords, API keys, or secrets are logged.
    """

    # ---------------------------------------------------------------------
    # Validate recipient
    # ---------------------------------------------------------------------

    if not to_email or "@" not in str(to_email):
        logger.warning(
            "Invalid email address provided."
        )
        return False

    # ---------------------------------------------------------------------
    # Load Resend configuration
    # ---------------------------------------------------------------------

    resend_conf = _get_resend_settings()

    api_key = resend_conf["api_key"]
    from_email = resend_conf["from_email"]

    if not api_key:
        logger.warning(
            "RESEND_API_KEY is not configured."
        )
        return False

    # ---------------------------------------------------------------------
    # Send through Resend HTTPS API
    # ---------------------------------------------------------------------

    try:
        resend.api_key = api_key

        response = await resend.Emails.send_async(
            {
                "from": from_email,
                "to": [to_email],
                "subject": subject,
                "text": body,
            }
        )

        logger.info(
            "Email submitted successfully through Resend "
            "to %s with subject '%s'.",
            to_email,
            subject,
        )

        return bool(response)

    except Exception as error:
        # Never log exception message because third-party errors
        # could potentially contain sensitive request information.
        logger.warning(
            "Resend email delivery to %s failed: %s",
            to_email,
            type(error).__name__,
        )

        return False


# =========================================================================
# EMAIL AUDIT LOGGING
# =========================================================================

async def log_email_audit(
    event_type: str,
    action: str,
    status: str,
    details: str,
    user_id: Optional[int] = None,
    credential_id: Optional[int] = None,
) -> None:
    """
    Safely records email audit events asynchronously.

    Failure to write an email audit event never interrupts
    the parent business operation.
    """

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

    except Exception as error:

        logger.error(
            "Failed to record email audit log: %s",
            type(error).__name__,
        )


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
    Dispatches login success email to registered user
    after successful authentication.
    """

    if not to_email:
        return False

    time_str = _format_email_datetime(timestamp)

    subject = (
        "SecureRotate AI — Successful Login"
    )

    body = f"""Hello {username},

You have successfully logged into SecureRotate AI.

Time:
{time_str}

Role:
{role}

If this login was not performed by you, please contact the administrator.

SecureRotate AI
"""

    success = await send_raw_email(
        to_email=to_email,
        subject=subject,
        body=body,
    )

    event_type = (
        "LOGIN_EMAIL_SENT"
        if success
        else "LOGIN_EMAIL_FAILED"
    )

    status_str = (
        "SUCCESS"
        if success
        else "FAILED"
    )

    details = (
        f"Login notification email "
        f"{'dispatched' if success else 'failed'} "
        f"for user '{username}' ({to_email})."
    )

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

    The generated database password is NEVER included.
    """

    if not to_email:
        return False

    # Convert rotation timestamp to IST for email display.
    time_str = _format_email_datetime(rotated_at)

    # Convert expiry timestamp to IST for email display.
    if next_expiry:
        expiry_str = _format_email_datetime(next_expiry)
    else:
        expiry_str = "In 90 Days"

    latency_str = (
        f"{latency_ms:.2f}"
        if isinstance(
            latency_ms,
            (int, float),
        )
        else str(latency_ms)
    )

    subject = (
        "SecureRotate AI — "
        "Credential Rotation Successful"
    )

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

    success = await send_raw_email(
        to_email=to_email,
        subject=subject,
        body=body,
    )

    event_type = (
        "ROTATION_EMAIL_SENT"
        if success
        else "ROTATION_EMAIL_FAILED"
    )

    status_str = (
        "SUCCESS"
        if success
        else "FAILED"
    )

    details = (
        f"Rotation success email "
        f"{'sent' if success else 'failed'} "
        f"to owner {to_email} "
        f"for credential '{credential_name}'."
    )

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
    Dispatches failed rotation and rollback notice
    to credential owner.
    """

    if not to_email:
        return False

    time_str = _format_email_datetime(timestamp)

    subject = (
        "SecureRotate AI — "
        "Credential Rotation Failed and Rolled Back"
    )

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

    success = await send_raw_email(
        to_email=to_email,
        subject=subject,
        body=body,
    )

    event_type = (
        "ROTATION_EMAIL_SENT"
        if success
        else "ROTATION_EMAIL_FAILED"
    )

    status_str = (
        "SUCCESS"
        if success
        else "FAILED"
    )

    details = (
        f"Rotation failure notice "
        f"{'sent' if success else 'failed'} "
        f"to owner {to_email} "
        f"for credential '{credential_name}'."
    )

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
    Dispatches proactive expiry warning alert
    to credential owner.
    """

    if not to_email:
        return False

    # ---------------------------------------------------------------------
    # Determine expiry subject
    # ---------------------------------------------------------------------

    if days_remaining <= 0:

        subject = (
            "SecureRotate AI — Credential Expired"
        )

        expires_str = "Expired"

    elif days_remaining == 1:

        subject = (
            "SecureRotate AI — "
            "Credential Expires in 1 Day"
        )

        expires_str = "1 day"

    else:

        subject = (
            f"SecureRotate AI — "
            f"Credential Expires in {days_remaining} Days"
        )

        expires_str = (
            f"{days_remaining} days"
        )

    # ---------------------------------------------------------------------
    # Email body
    # ---------------------------------------------------------------------

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

    # ---------------------------------------------------------------------
    # Dispatch
    # ---------------------------------------------------------------------

    success = await send_raw_email(
        to_email=to_email,
        subject=subject,
        body=body,
    )

    # ---------------------------------------------------------------------
    # Audit
    # ---------------------------------------------------------------------

    event_type = (
        "EXPIRY_EMAIL_SENT"
        if success
        else "EXPIRY_EMAIL_FAILED"
    )

    status_str = (
        "SUCCESS"
        if success
        else "FAILED"
    )

    details = (
        f"Expiry alert email ({expires_str}) "
        f"{'sent' if success else 'failed'} "
        f"to owner {to_email} "
        f"for '{credential_name}'."
    )

    await log_email_audit(
        event_type=event_type,
        action="SEND_EXPIRY_EMAIL",
        status=status_str,
        details=details,
        credential_id=credential_id,
    )

    return success