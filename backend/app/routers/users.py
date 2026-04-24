from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..auth import get_current_active_user, require_role
from ..models import User, UserRole, UserStatus, AuditLog
from ..schemas import UserOut, UserUpdate, AuditLogOut

router = APIRouter()


@router.get("/", response_model=List[UserOut])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    return db.query(User).order_by(User.created_at.desc()).all()



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
