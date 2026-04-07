import secrets
from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth import authenticate_user, create_access_token, get_password_hash, get_current_active_user
from ..models import User, UserRole, UserStatus, AuditLog
from ..schemas import LoginRequest, Token, UserOut, RegisterRequest
from ..config import settings
from ..email_service import send_verification_email

router = APIRouter()

AVATAR_COLORS = ["#00D4FF", "#7C3AED", "#06FFA5", "#FF4D6D", "#FFB800", "#EC4899"]


@router.post("/login", response_model=Token)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if user.status == UserStatus.email_pending:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address first. Check your inbox for a verification link.",
        )
    if user.status == UserStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is awaiting approval by an administrator.",
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


@router.post("/register", response_model=UserOut, status_code=201)
async def public_register(user_data: RegisterRequest, db: Session = Depends(get_db)):
    """Public sign-up. Creates a viewer with email_pending status and sends a verification email."""
    existing = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    token   = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    color   = AVATAR_COLORS[db.query(User).count() % len(AVATAR_COLORS)]

    user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        password_hash=get_password_hash(user_data.password),
        role=UserRole.viewer,
        status=UserStatus.email_pending,
        is_active=True,
        avatar_color=color,
        email_verified=False,
        verification_token=token,
        verification_token_expires=expires,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Fire-and-forget — errors are logged but don't fail the request
    try:
        send_verification_email(user.email, user.username, token)
    except Exception as exc:
        print(f"[register] email error: {exc}")

    return user


@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify an email address using the token from the verification link."""
    user = db.query(User).filter(User.verification_token == token).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")

    now = datetime.now(timezone.utc)
    if user.verification_token_expires:
        exp = user.verification_token_expires
        # Handle naive datetimes returned by MySQL
        if exp.tzinfo is None:
            from datetime import timezone as tz
            exp = exp.replace(tzinfo=tz.utc)
        if now > exp:
            raise HTTPException(
                status_code=400,
                detail="This verification link has expired. Please register again.",
            )

    user.email_verified            = True
    user.status                    = UserStatus.pending   # now awaits superuser approval
    user.verification_token        = None
    user.verification_token_expires = None
    db.commit()

    return {
        "detail": "Email verified successfully! Your account is now pending approval by an administrator."
    }


@router.post("/resend-verification")
async def resend_verification(email: str, db: Session = Depends(get_db)):
    """Resend the verification email for an email_pending account."""
    user = db.query(User).filter(User.email == email).first()
    if not user or user.status != UserStatus.email_pending:
        # Return 200 regardless to avoid email enumeration
        return {"detail": "If that email is registered and unverified, a new link has been sent."}

    token   = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    user.verification_token          = token
    user.verification_token_expires  = expires
    db.commit()

    try:
        send_verification_email(user.email, user.username, token)
    except Exception as exc:
        print(f"[resend] email error: {exc}")

    return {"detail": "If that email is registered and unverified, a new link has been sent."}


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
