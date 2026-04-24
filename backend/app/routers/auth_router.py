import re
import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt as jose_jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth import authenticate_user, create_access_token, get_password_hash, get_current_active_user
from ..models import User, UserRole, UserStatus, AuditLog
from ..schemas import LoginRequest, Token, UserOut
from ..config import settings

router = APIRouter()

# ── Role mapping: Laravel role string → Otenga UserRole ──────────────────────
_SUPERUSER_ROLES = {"superadmin", "super_admin", "admin", "administrator"}
_CREATOR_ROLES   = {"creator", "analyst", "data_analyst", "manager", "editor", "staff"}

def _map_laravel_role(raw_role) -> UserRole:
    """
    Accepts a string, a list, or None coming from the Laravel JWT 'role'/'roles' claim
    and returns the best-matching Otenga UserRole.
    """
    if raw_role is None:
        return UserRole.viewer
    roles = [raw_role] if isinstance(raw_role, str) else list(raw_role)
    roles_lower = {str(r).lower() for r in roles}
    if roles_lower & _SUPERUSER_ROLES:
        return UserRole.superuser
    if roles_lower & _CREATOR_ROLES:
        return UserRole.creator
    return UserRole.viewer


def _safe_username(name: str, email: str) -> str:
    """
    Derive a URL-safe username from the person's name or email prefix.
    Appends a short random suffix to avoid collisions.
    """
    base = re.sub(r"[^a-z0-9_]", "", name.lower().replace(" ", "_"))[:20]
    if not base:
        base = email.split("@")[0][:20]
    return f"{base}_{secrets.token_hex(3)}"

AVATAR_COLORS = ["#00D4FF", "#7C3AED", "#06FFA5", "#FF4D6D", "#FFB800", "#EC4899"]


@router.post("/login", response_model=Token)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if user.status == UserStatus.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled. Please contact an administrator.",
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is inactive")

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    log = AuditLog(user_id=user.id, action="login", resource_type="auth")
    db.add(log)
    db.commit()

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )



@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user


# ── SSO ───────────────────────────────────────────────────────────────────────

class SSORequest(BaseModel):
    token: str


@router.post("/sso", response_model=Token)
async def sso_login(body: SSORequest, db: Session = Depends(get_db)):
    """
    Exchange a Laravel-issued JWT for an Otenga session token.

    Flow:
      1. Laravel app redirects the user to <otenga>/sso?token=<laravel_jwt>
      2. Otenga frontend calls POST /api/v1/auth/sso  { "token": "<laravel_jwt>" }
      3. This endpoint validates the token, provisions the user if new,
         and returns a standard Otenga Token.

    The Laravel JWT must be signed with the same secret stored in LARAVEL_JWT_SECRET.
    Expected claims: email (required), name, phone_number / phone, role / roles.
    """
    if not settings.LARAVEL_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSO is not configured on this server.",
        )

    # ── 1. Decode & verify the Laravel JWT ───────────────────────────────────
    try:
        payload = jose_jwt.decode(
            body.token,
            settings.LARAVEL_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},  # Laravel tokens often omit audience
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired SSO token: {exc}",
        )

    email: str = payload.get("email") or payload.get("sub", "")
    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSO token is missing a valid email claim.",
        )

    full_name: str  = payload.get("name") or payload.get("full_name") or ""
    phone: str      = payload.get("phone_number") or payload.get("phone") or ""
    raw_role        = payload.get("role") or payload.get("roles")
    otenga_role     = _map_laravel_role(raw_role)

    # ── 2. Look up or create the user in BI_Otenga ───────────────────────────
    user = db.query(User).filter(User.email == email).first()

    AVATAR_COLORS = ["#00D4FF", "#7C3AED", "#06FFA5", "#FF4D6D", "#FFB800", "#EC4899"]

    if user is None:
        # First-time SSO login — auto-provision as active (no approval needed;
        # the Laravel app has already authenticated them).
        username = _safe_username(full_name, email)
        # Ensure username is unique
        while db.query(User).filter(User.username == username).first():
            username = _safe_username(full_name, email)

        color = AVATAR_COLORS[db.query(User).count() % len(AVATAR_COLORS)]
        user = User(
            username=username,
            email=email,
            full_name=full_name or None,
            # Random unusable password — SSO users authenticate via Laravel
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
            role=otenga_role,
            status=UserStatus.active,
            is_active=True,
            avatar_color=color,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Existing user — refresh name if it changed; keep their Otenga role
        # (a superuser may have manually upgraded them).
        changed = False
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            changed = True
        if changed:
            db.commit()
            db.refresh(user)

    if user.status == UserStatus.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled. Please contact an administrator.",
        )

    # ── 3. Issue Otenga JWT ───────────────────────────────────────────────────
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    log = AuditLog(user_id=user.id, action="sso_login", resource_type="auth")
    db.add(log)
    db.commit()

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.get("/sso/config")
async def sso_config():
    """Return SSO configuration so the frontend knows whether SSO is available."""
    return {
        "enabled": bool(settings.LARAVEL_JWT_SECRET),
        "laravel_app_url": settings.LARAVEL_APP_URL or None,
    }
