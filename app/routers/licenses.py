from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db
from app.models import License, LicenseCheck, Product
from app.security import rate_limit


router = APIRouter(prefix="/api/licenses/v1", tags=["licenses"])


class EAValidateIn(BaseModel):
    license_key: str = Field(min_length=6, max_length=255)
    product_code: str = Field(min_length=1, max_length=255)
    mt_account_number: str = Field(min_length=1, max_length=64)
    platform: str | None = Field(default=None, max_length=50)
    client_version: str | None = Field(default=None, max_length=50)
    broker_server: str | None = Field(default=None, max_length=255)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _normalize_key(value: str) -> str:
    return value.strip().upper()


def _normalize_account(value: str | int) -> str:
    return str(value).strip()


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _validation_response(allowed: bool, status: str, message: str) -> dict:
    settings = get_settings()
    return {
        "allowed": allowed,
        "status": status,
        "message": message,
        "next_check_after_seconds": settings.license_check_interval_seconds,
        "offline_grace_seconds": settings.license_offline_grace_seconds,
        "server_time": _now().isoformat(),
    }


def _record_check(
    db: Session,
    request: Request,
    data: EAValidateIn,
    license_record: License | None,
    result: str,
    message: str,
) -> None:
    if license_record:
        license_record.last_checked_at = _now()
        license_record.last_check_status = result
        license_record.last_check_message = message[:255]

    db.add(
        LicenseCheck(
            license_id=license_record.id if license_record else None,
            product_code=data.product_code.strip().lower(),
            mt_account_number=_normalize_account(data.mt_account_number),
            platform=(data.platform or "").strip() or None,
            client_version=(data.client_version or "").strip() or None,
            result=result,
            message=message[:255],
            ip_address=_client_ip(request),
        )
    )
    db.commit()


@router.post("/ea/validate", dependencies=[Depends(rate_limit("license_ea_validate", 240, 3600))])
def validate_ea_license(data: EAValidateIn, request: Request, db: Session = Depends(get_db)):
    license_key = _normalize_key(data.license_key)
    product_code = data.product_code.strip().lower()
    mt_account_number = _normalize_account(data.mt_account_number)

    license_record = (
        db.query(License)
        .options(joinedload(License.product), joinedload(License.user))
        .filter(func.upper(License.license_key) == license_key)
        .first()
    )
    if not license_record:
        message = "License key was not found"
        _record_check(db, request, data, None, "not_found", message)
        return _validation_response(False, "not_found", message)

    if (license_record.activation_type or "ea_account") != "ea_account":
        message = "License is not valid for EA account activation"
        _record_check(db, request, data, license_record, "wrong_activation_type", message)
        return _validation_response(False, "blocked", message)

    product: Product | None = license_record.product
    if not product or product.slug.lower() != product_code:
        message = "License does not match this product"
        _record_check(db, request, data, license_record, "product_mismatch", message)
        return _validation_response(False, "blocked", message)

    status = (license_record.status or "active").lower()
    if status != "active":
        message = f"License is {status}"
        _record_check(db, request, data, license_record, status, message)
        return _validation_response(False, status, message)

    if license_record.expires_at and _ensure_aware(license_record.expires_at) <= _now():
        license_record.status = "expired"
        message = "License has expired"
        _record_check(db, request, data, license_record, "expired", message)
        return _validation_response(False, "expired", message)

    allowed_account = _normalize_account(license_record.allowed_mt_account_number or "")
    if not allowed_account:
        message = "MT account number is not assigned in the account portal"
        _record_check(db, request, data, license_record, "account_not_assigned", message)
        return _validation_response(False, "account_not_assigned", message)

    if allowed_account != mt_account_number:
        message = "MT account number does not match this license"
        _record_check(db, request, data, license_record, "account_mismatch", message)
        return _validation_response(False, "account_mismatch", message)

    if license_record.allowed_broker_server:
        requested_server = (data.broker_server or "").strip().lower()
        if requested_server and requested_server != license_record.allowed_broker_server.strip().lower():
            message = "Broker server does not match this license"
            _record_check(db, request, data, license_record, "broker_mismatch", message)
            return _validation_response(False, "broker_mismatch", message)

    if not license_record.activated_at:
        license_record.activated_at = _now()

    message = "License active"
    _record_check(db, request, data, license_record, "active", message)
    response = _validation_response(True, "active", message)
    response["expires_at"] = license_record.expires_at.isoformat() if license_record.expires_at else None
    response["product_code"] = product.slug
    return response
