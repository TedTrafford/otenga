from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..auth import get_current_active_user, require_role, get_password_hash
from ..models import User, UserRole, UserStatus, AuditLog
from ..schemas import UserOut, UserUpdate, AuditLogOut

router = APIRouter()


@router.get("/", response_model=List[UserOut])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.get("/pending", response_model=List[UserOut])
async def list_pending_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    """Return accounts that have verified email and are awaiting approval."""
    return (
        db.query(User)
        .filter(User.status == UserStatus.pending)
        .order_by(User.created_at.desc())
        .all()
    )


@router.get("/unverified", response_model=List[UserOut])
async def list_unverified_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    """Return accounts that registered but haven't verified their email yet."""
    return (
        db.query(User)
        .filter(User.status == UserStatus.email_pending)
        .order_by(User.created_at.desc())
        .all()
    )


@router.post("/{user_id}/verify-email", response_model=UserOut)
async def admin_verify_email(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    """Superuser manually marks an email as verified and moves the account to pending approval."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status != UserStatus.email_pending:
        raise HTTPException(status_code=400, detail="User email is already verified")

    user.email_verified             = True
    user.status                     = UserStatus.pending
    user.verification_token         = None
    user.verification_token_expires = None

    log = AuditLog(
        user_id=current_user.id,
        action="admin_verify_email",
        resource_type="user",
        resource_id=user_id,
        details={"verified_username": user.username},
    )
    db.add(log)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.id != user_id and current_user.role != UserRole.superuser:
        raise HTTPException(status_code=403, detail="Access denied")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/approve", response_model=UserOut)
async def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    """Approve a pending registration."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status != UserStatus.pending:
        raise HTTPException(status_code=400, detail="User is not in pending state")

    user.status = UserStatus.active
    log = AuditLog(
        user_id=current_user.id,
        action="approve_user",
        resource_type="user",
        resource_id=user_id,
        details={"approved_username": user.username},
    )
    db.add(log)
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/disable", response_model=UserOut)
async def disable_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    """Disable an active account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")

    user.status = UserStatus.disabled
    log = AuditLog(
        user_id=current_user.id,
        action="disable_user",
        resource_type="user",
        resource_id=user_id,
        details={"disabled_username": user.username},
    )
    db.add(log)
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/enable", response_model=UserOut)
async def enable_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    """Re-enable a disabled account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.status = UserStatus.active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    """Permanently delete a user (typically used to reject pending requests)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    db.delete(user)
    log = AuditLog(
        user_id=current_user.id,
        action="delete_user",
        resource_type="user",
        resource_id=user_id,
        details={"deleted_username": user.username},
    )
    db.add(log)
    db.commit()
    return {"detail": "User deleted"}


@router.get("/audit/logs", response_model=List[AuditLogOut])
async def get_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return logs
