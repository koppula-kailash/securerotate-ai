"""
SecureRotate AI - Authentication API Router
Provides register, login, me, and logout endpoints with Argon2 hashing and JWT token generation.
"""

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.auth import UserRegister, LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.api.dependencies.auth_dependencies import get_current_active_user

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User Account",
    description="Registers a new user account with secure Argon2 password hashing.",
)
async def register(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user with Argon2 password hashing."""

    stmt = select(User).where(
        or_(
            User.username == payload.username,
            User.email == payload.email,
        )
    )

    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if existing.username == payload.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already registered.",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered.",
        )

    role = payload.role.upper()

    if role not in ["ADMIN", "DEVOPS", "AUDITOR"]:
        role = "AUDITOR"

    hashed_pw = hash_password(payload.password)

    new_user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hashed_pw,
        role=role,
        is_active=True,
    )

    db.add(new_user)
    await db.flush()

    audit_entry = AuditLog(
        user_id=new_user.id,
        credential_id=None,
        event_type="USER_REGISTERED",
        action="REGISTER",
        status="SUCCESS",
        details=(
            f"User '{new_user.username}' ({new_user.email}) "
            f"registered with role '{new_user.role}'."
        ),
    )

    db.add(audit_entry)

    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User Login",
    description="Authenticates user with username/email and password. Returns JWT access token.",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate using username, email, or username_or_email.
    Password verification is performed using Argon2 through pwdlib.
    """

    identifier = (
        payload.username_or_email
        or payload.username
        or payload.email
    )

    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username/email is required.",
        )

    identifier_str = identifier.strip()

    stmt = select(User).where(
        or_(
            User.username == identifier_str,
            User.email == identifier_str,
        )
    )

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(
        payload.password,
        user.password_hash,
    ):
        audit_entry = AuditLog(
            user_id=user.id if user else None,
            credential_id=None,
            event_type="LOGIN_FAILED",
            action="LOGIN",
            status="FAILED",
            details=(
                f"Failed login attempt for "
                f"identifier '{identifier_str}'."
            ),
        )

        db.add(audit_entry)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated.",
        )

    token_payload = {
        "user_id": user.id,
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }

    access_token = create_access_token(
        data=token_payload
    )

    audit_entry = AuditLog(
        user_id=user.id,
        credential_id=None,
        event_type="LOGIN_SUCCESS",
        action="LOGIN",
        status="SUCCESS",
        details=(
            f"User '{user.username}' logged in successfully. Login notification dispatched to {user.email}."
        ),
    )

    db.add(audit_entry)
    await db.commit()

    # Non-blocking dispatch of login success email
    try:
        from app.services.email_service import send_login_success_email
        if user.email:
            await send_login_success_email(
                to_email=user.email,
                username=user.username,
                role=user.role,
                user_id=user.id,
            )
    except Exception as e:
        pass

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current Authenticated User",
    description="Returns profile details for the currently authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Retrieve profile of currently authenticated user."""

    return current_user


@router.post(
    "/logout",
    summary="User Logout",
    description="Logs logout event in security audit trail.",
)
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Records logout event in audit trail."""

    audit_entry = AuditLog(
        user_id=current_user.id,
        credential_id=None,
        event_type="LOGOUT",
        action="LOGOUT",
        status="SUCCESS",
        details=(
            f"User '{current_user.username}' logged out."
        ),
    )

    db.add(audit_entry)
    await db.commit()

    return {"message": "Logged out successfully"}