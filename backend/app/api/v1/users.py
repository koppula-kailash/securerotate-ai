"""
SecureRotate AI - User Management API Router (ADMIN Only)
Allows administrators to list, create, update roles, and activate/deactivate user accounts.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.auth import UserResponse, UserCreate, UserUpdate
from app.services.auth_service import hash_password
from app.api.dependencies.auth_dependencies import require_roles, get_current_active_user

router = APIRouter()


@router.get(
    "",
    response_model=List[UserResponse],
    summary="List All Users (Admin Only)",
    description="Retrieves all user accounts.",
)
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_roles(["ADMIN"])),
) -> List[UserResponse]:
    """Retrieve all user accounts."""
    stmt = select(User).order_by(User.id.asc())
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create User (Admin Only)",
    description="Creates a new user account with specified role.",
)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_roles(["ADMIN"])),
) -> UserResponse:
    """Create a new user account (Admin only)."""
    # Check if username or email already exists
    stmt = select(User).where(
        (User.username == payload.username) | (User.email == payload.email)
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or Email already exists.",
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
        is_active=payload.is_active,
    )

    db.add(new_user)
    await db.flush()

    audit_entry = AuditLog(
        user_id=admin_user.id,
        credential_id=None,
        event_type="USER_CREATED",
        action="CREATE",
        status="SUCCESS",
        details=f"Admin '{admin_user.username}' created user '{new_user.username}' with role '{new_user.role}'.",
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update User Account (Admin Only)",
    description="Updates role, active status, or email for a user.",
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_roles(["ADMIN"])),
) -> UserResponse:
    """Update user account parameters (Admin only)."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if payload.role:
        role = payload.role.upper()
        if role in ["ADMIN", "DEVOPS", "AUDITOR"]:
            user.role = role

    if payload.is_active is not None:
        user.is_active = payload.is_active

    if payload.email:
        user.email = payload.email

    if payload.username:
        user.username = payload.username

    if payload.password:
        user.password_hash = hash_password(payload.password)

    audit_entry = AuditLog(
        user_id=admin_user.id,
        credential_id=None,
        event_type="USER_UPDATED",
        action="UPDATE",
        status="SUCCESS",
        details=f"Admin '{admin_user.username}' updated user '{user.username}' (ID: {user_id}). Role={user.role}, Active={user.is_active}.",
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(user)

    return user


@router.delete(
    "/{user_id}",
    summary="Deactivate/Delete User (Admin Only)",
    description="Deactivates a user account.",
)
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_roles(["ADMIN"])),
) -> Dict[str, str]:
    """Deactivate user account."""
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own admin account.",
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = False

    audit_entry = AuditLog(
        user_id=admin_user.id,
        credential_id=None,
        event_type="USER_DEACTIVATED",
        action="DELETE",
        status="SUCCESS",
        details=f"Admin '{admin_user.username}' deactivated user '{user.username}' (ID: {user_id}).",
    )
    db.add(audit_entry)
    await db.commit()

    return {"message": f"User '{user.username}' deactivated successfully."}
