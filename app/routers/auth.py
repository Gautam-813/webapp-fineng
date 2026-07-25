import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.database import get_db
from app.email_service import EmailDeliveryError, send_otp_email
from app.models import EmailOTP, User
from app.config import get_settings
from app.security import rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
COOKIE_NAME = "tfc_token"


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=1)


class VerifyRegistrationIn(BaseModel):
    email: EmailStr
    otp_code: str = Field(min_length=6, max_length=6)


class ResendOtpIn(BaseModel):
    email: EmailStr
    purpose: str = Field(pattern="^(registration|password_reset)$")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    email: EmailStr
    otp_code: str = Field(min_length=6, max_length=6)
    password: str = Field(min_length=6)


class AuthOut(BaseModel):
    message: str
    user: dict


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    status: str


def _create_token(user_id: int, role: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_registration_email(email: str) -> None:
    settings = get_settings()
    allowed_domains = settings.registration_domain_list
    if not allowed_domains:
        return
    domain = email.rsplit("@", 1)[-1].lower()
    if domain not in allowed_domains:
        raise HTTPException(status_code=400, detail="Registration currently requires a Gmail address")


def _generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_otp(code: str) -> str:
    return pwd_context.hash(code)


def _create_email_otp(db: Session, user: User | None, email: str, purpose: str) -> None:
    settings = get_settings()
    email = _normalize_email(email)
    latest = (
        db.query(EmailOTP)
        .filter(
            func.lower(EmailOTP.email) == email,
            EmailOTP.purpose == purpose,
            EmailOTP.consumed_at.is_(None),
        )
        .order_by(EmailOTP.created_at.desc())
        .first()
    )
    if latest and latest.created_at:
        elapsed = (_now() - _ensure_aware(latest.created_at)).total_seconds()
        if elapsed < settings.otp_resend_cooldown_seconds:
            wait_seconds = max(int(settings.otp_resend_cooldown_seconds - elapsed), 1)
            raise HTTPException(status_code=429, detail=f"Please wait {wait_seconds} seconds before requesting another code")

    db.query(EmailOTP).filter(
        func.lower(EmailOTP.email) == email,
        EmailOTP.purpose == purpose,
        EmailOTP.consumed_at.is_(None),
    ).update({"consumed_at": _now()})

    code = _generate_otp_code()
    otp = EmailOTP(
        user_id=user.id if user else None,
        email=email,
        purpose=purpose,
        code_hash=_hash_otp(code),
        max_attempts=settings.otp_max_attempts,
        expires_at=_now() + timedelta(minutes=settings.otp_expiry_minutes),
    )
    db.add(otp)
    db.flush()

    try:
        send_otp_email(email, code, purpose)
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


def _verify_email_otp(db: Session, email: str, purpose: str, code: str) -> EmailOTP:
    email = _normalize_email(email)
    otp = (
        db.query(EmailOTP)
        .filter(
            func.lower(EmailOTP.email) == email,
            EmailOTP.purpose == purpose,
            EmailOTP.consumed_at.is_(None),
        )
        .order_by(EmailOTP.created_at.desc())
        .first()
    )
    if not otp:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    if _ensure_aware(otp.expires_at) < _now():
        otp.consumed_at = _now()
        raise HTTPException(status_code=400, detail="Verification code has expired")

    if (otp.attempts or 0) >= (otp.max_attempts or get_settings().otp_max_attempts):
        otp.consumed_at = _now()
        raise HTTPException(status_code=429, detail="Too many incorrect verification attempts")

    if not pwd_context.verify(code, otp.code_hash):
        otp.attempts = (otp.attempts or 0) + 1
        raise HTTPException(status_code=400, detail="Invalid verification code")

    otp.consumed_at = _now()
    return otp


def _ensure_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _get_token_from_cookie(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    return token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _get_token_from_cookie(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if (user.status or "active") != "active":
        raise HTTPException(status_code=403, detail="Account is not active")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = _get_token_from_cookie(request)
    if not token:
        return None
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError, TypeError):
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if user and (user.status or "active") != "active":
        return None
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.post("/register", status_code=201, dependencies=[Depends(rate_limit("auth_register", 20, 900))])
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = _normalize_email(data.email)
    _validate_registration_email(email)
    existing = db.query(User).filter(func.lower(User.email) == email).first()
    if existing and (existing.status or "active") == "active":
        raise HTTPException(status_code=409, detail="Email already registered")
    if existing and existing.role != "customer":
        raise HTTPException(status_code=409, detail="Email already registered")

    if existing:
        user = existing
        user.full_name = data.full_name.strip()
        user.password_hash = pwd_context.hash(data.password)
        user.status = "pending_verification"
    else:
        user = User(
            email=email,
            full_name=data.full_name.strip(),
            password_hash=pwd_context.hash(data.password),
            role="customer",
            status="pending_verification",
        )
        db.add(user)
        db.flush()

    _create_email_otp(db, user, email, "registration")
    db.commit()
    db.refresh(user)
    return {"message": "Verification code sent", "email": user.email, "status": user.status}


@router.post("/register/verify", dependencies=[Depends(rate_limit("auth_verify_registration", 40, 900))])
def verify_registration(data: VerifyRegistrationIn, db: Session = Depends(get_db)):
    email = _normalize_email(data.email)
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user or user.role != "customer":
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    if (user.status or "active") == "active":
        return {"message": "Account already verified", "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role, "status": user.status}}

    _verify_email_otp(db, email, "registration", data.otp_code)
    user.status = "active"
    db.commit()
    db.refresh(user)
    return {"message": "Account verified successfully", "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role, "status": user.status}}


@router.post("/otp/resend", dependencies=[Depends(rate_limit("auth_resend_otp", 15, 900))])
def resend_otp(data: ResendOtpIn, db: Session = Depends(get_db)):
    email = _normalize_email(data.email)
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if data.purpose == "registration":
        _validate_registration_email(email)
        if not user or user.role != "customer" or (user.status or "active") == "active":
            raise HTTPException(status_code=400, detail="No pending registration found")
        _create_email_otp(db, user, email, "registration")
        db.commit()
        return {"message": "Verification code sent"}

    if user and user.password_hash and (user.status or "active") == "active":
        _create_email_otp(db, user, email, "password_reset")
        db.commit()
    return {"message": "If an account exists, a reset code has been sent"}


@router.post("/login", dependencies=[Depends(rate_limit("auth_login", 40, 300))])
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == data.email.lower()).first()
    if not user or not user.password_hash or not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if (user.status or "active") != "active":
        raise HTTPException(status_code=403, detail="Account is not active")
    token = _create_token(user.id, user.role)
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite=settings.cookie_samesite,
        max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        path="/",
    )
    return {"message": "Login successful", "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role, "status": user.status}}


@router.post("/forgot-password", dependencies=[Depends(rate_limit("auth_forgot_password", 20, 900))])
def forgot_password(data: ForgotPasswordIn, db: Session = Depends(get_db)):
    email = _normalize_email(data.email)
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user and user.password_hash and (user.status or "active") == "active":
        _create_email_otp(db, user, email, "password_reset")
        db.commit()
    return {"message": "If an account exists, a reset code has been sent"}


@router.post("/reset-password", dependencies=[Depends(rate_limit("auth_reset_password", 40, 900))])
def reset_password(data: ResetPasswordIn, db: Session = Depends(get_db)):
    email = _normalize_email(data.email)
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user or not user.password_hash or (user.status or "active") != "active":
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    _verify_email_otp(db, email, "password_reset", data.otp_code)
    user.password_hash = pwd_context.hash(data.password)
    db.commit()
    return {"message": "Password updated successfully"}


@router.post("/logout")
def logout(response: Response):
    settings = get_settings()
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        secure=settings.secure_cookies,
        samesite=settings.cookie_samesite,
    )
    return {"message": "Logged out"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "full_name": current_user.full_name, "role": current_user.role, "status": current_user.status}
