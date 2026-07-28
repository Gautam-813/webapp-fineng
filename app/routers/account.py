from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
from app.config import get_settings
from app.database import get_db
from app.models import ContactInquiry, CustomProjectRequest, License, Order, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/account", tags=["account"])


class ProfileUpdateIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)


class LicenseAccountUpdateIn(BaseModel):
    mt_account_number: str = Field(min_length=4, max_length=64)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _account_order_filter(current_user: User):
    return or_(
        Order.user_id == current_user.id,
        func.lower(Order.customer_email) == current_user.email.lower(),
    )


def _serialize_license(license_record: License) -> dict:
    product = license_record.product
    account_updated_at = license_record.mt_account_updated_at
    cooldown_days = get_settings().license_account_change_cooldown_days
    can_change_at = None
    can_change_account = True
    if license_record.allowed_mt_account_number and account_updated_at and cooldown_days > 0:
        can_change_at_dt = _ensure_aware(account_updated_at) + timedelta(days=cooldown_days)
        can_change_at = can_change_at_dt.isoformat()
        can_change_account = _now() >= can_change_at_dt

    return {
        "id": license_record.id,
        "license_key": license_record.license_key,
        "status": license_record.status,
        "activation_type": license_record.activation_type or "ea_account",
        "allowed_mt_account_number": license_record.allowed_mt_account_number,
        "allowed_broker_server": license_record.allowed_broker_server,
        "expires_at": license_record.expires_at.isoformat() if license_record.expires_at else None,
        "activated_at": license_record.activated_at.isoformat() if license_record.activated_at else None,
        "mt_account_updated_at": license_record.mt_account_updated_at.isoformat() if license_record.mt_account_updated_at else None,
        "last_checked_at": license_record.last_checked_at.isoformat() if license_record.last_checked_at else None,
        "last_check_status": license_record.last_check_status,
        "last_check_message": license_record.last_check_message,
        "can_change_account": can_change_account,
        "can_change_account_at": can_change_at,
        "download_available": bool(product and product.product_file_path),
        "download_url": f"/api/account/licenses/{license_record.id}/download" if product and product.product_file_path else None,
        "product_file_name": product.product_file_name if product else None,
        "product_file_size": product.product_file_size if product else None,
        "product": {
            "id": product.id if product else None,
            "name": product.name if product else "Unknown product",
            "slug": product.slug if product else None,
            "platform": product.platform if product else None,
            "version": product.version if product else None,
        },
    }


def _serialize_project_request(project_request: CustomProjectRequest) -> dict:
    return {
        "id": project_request.id,
        "project_type": project_request.project_type,
        "budget_range": project_request.budget_range,
        "timeline": project_request.timeline,
        "description": project_request.description,
        "status": project_request.status,
        "created_at": project_request.created_at.isoformat() if project_request.created_at else None,
        "updated_at": project_request.updated_at.isoformat() if project_request.updated_at else None,
    }


def _serialize_support_inquiry(inquiry: ContactInquiry) -> dict:
    return {
        "id": inquiry.id,
        "subject": inquiry.subject,
        "service_type": inquiry.service_type,
        "message": inquiry.message,
        "status": inquiry.status,
        "created_at": inquiry.created_at.isoformat() if inquiry.created_at else None,
        "updated_at": inquiry.updated_at.isoformat() if inquiry.updated_at else None,
    }


@router.get("/profile")
def account_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "role": current_user.role,
        "status": current_user.status,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.put("/profile")
def update_account_profile(
    data: ProfileUpdateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.full_name = data.full_name.strip()
    current_user.phone = data.phone.strip() if data.phone else None
    db.commit()
    db.refresh(current_user)
    return account_profile(current_user)


@router.get("/licenses")
def account_licenses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    licenses = (
        db.query(License)
        .options(joinedload(License.product))
        .filter(License.user_id == current_user.id)
        .order_by(License.created_at.desc())
        .all()
    )
    return {
        "items": [_serialize_license(item) for item in licenses],
        "stats": {
            "total_licenses": len(licenses),
            "active_licenses": len([item for item in licenses if (item.status or "active") == "active"]),
            "assigned_accounts": len([item for item in licenses if item.allowed_mt_account_number]),
        },
    }


@router.put("/licenses/{license_id}/mt-account")
def update_license_mt_account(
    license_id: int,
    data: LicenseAccountUpdateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    license_record = (
        db.query(License)
        .filter(License.id == license_id, License.user_id == current_user.id)
        .first()
    )
    if not license_record:
        raise HTTPException(status_code=404, detail="License not found")
    if (license_record.activation_type or "ea_account") != "ea_account":
        raise HTTPException(status_code=400, detail="This license does not use MT account binding")
    if (license_record.status or "active") not in {"active", "expired"}:
        raise HTTPException(status_code=400, detail="This license cannot be updated in its current status")

    cooldown_days = get_settings().license_account_change_cooldown_days
    if license_record.allowed_mt_account_number and license_record.mt_account_updated_at and cooldown_days > 0:
        can_change_at = _ensure_aware(license_record.mt_account_updated_at) + timedelta(days=cooldown_days)
        if _now() < can_change_at:
            raise HTTPException(
                status_code=429,
                detail=f"MT account can be changed after {can_change_at.date().isoformat()} or by contacting support",
            )

    license_record.allowed_mt_account_number = data.mt_account_number.strip()
    license_record.mt_account_updated_at = _now()
    db.commit()
    db.refresh(license_record)
    return _serialize_license(license_record)


@router.get("/licenses/{license_id}/download")
def download_license_product_file(
    license_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    license_record = (
        db.query(License)
        .options(joinedload(License.product))
        .filter(License.id == license_id, License.user_id == current_user.id)
        .first()
    )
    if not license_record:
        raise HTTPException(status_code=404, detail="License not found")
    if (license_record.status or "active") != "active":
        raise HTTPException(status_code=403, detail="License is not active")
    if license_record.expires_at and _ensure_aware(license_record.expires_at) <= _now():
        raise HTTPException(status_code=403, detail="License has expired")
    if not license_record.product or not license_record.product.product_file_path:
        raise HTTPException(status_code=404, detail="Product file is not available yet")

    file_path = Path(license_record.product.product_file_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Product file is missing")

    return FileResponse(
        path=file_path,
        filename=license_record.product.product_file_name or file_path.name,
        media_type="application/octet-stream",
    )


@router.get("/orders")
def account_orders(
    current_user: User = Depends(get_current_user),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=5, le=50),
    db: Session = Depends(get_db),
):
    account_filter = _account_order_filter(current_user)
    stats_orders = db.query(Order).filter(account_filter).all()

    base_query = db.query(Order).filter(account_filter)
    if status:
        base_query = base_query.filter(Order.status == status)

    total_value = sum((order.total_amount or Decimal("0")) for order in stats_orders)
    total = base_query.count()
    pages = max((total + page_size - 1) // page_size, 1)
    if page > pages:
        page = pages

    orders = (
        base_query.options(joinedload(Order.items))
        .order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            {
                "id": order.id,
                "customer_name": order.customer_name,
                "customer_email": order.customer_email,
                "status": order.status,
                "total_amount": str(order.total_amount),
                "currency": order.currency,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "items": [
                    {
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                        "total_price": str(item.total_price),
                    }
                    for item in order.items
                ],
            }
            for order in orders
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "stats": {
            "total_orders": len(stats_orders),
            "confirmed_orders": len([order for order in stats_orders if order.status == "confirmed"]),
            "paid_orders": len([order for order in stats_orders if order.status == "paid"]),
            "order_value": str(total_value),
        },
    }


@router.get("/projects")
def account_projects(
    current_user: User = Depends(get_current_user),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=5, le=50),
    db: Session = Depends(get_db),
):
    base_query = db.query(CustomProjectRequest).filter(
        func.lower(CustomProjectRequest.email) == current_user.email.lower()
    )
    stats_requests = base_query.all()
    if status:
        base_query = base_query.filter(CustomProjectRequest.status == status)

    total = base_query.count()
    pages = max((total + page_size - 1) // page_size, 1)
    if page > pages:
        page = pages

    project_requests = (
        base_query.order_by(CustomProjectRequest.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [_serialize_project_request(item) for item in project_requests],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "stats": {
            "total_projects": len(stats_requests),
            "new_projects": len([item for item in stats_requests if item.status == "new"]),
            "in_progress_projects": len([item for item in stats_requests if item.status == "in_progress"]),
            "completed_projects": len([item for item in stats_requests if item.status == "completed"]),
        },
    }


@router.get("/support")
def account_support(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=5, le=50),
    db: Session = Depends(get_db),
):
    base_query = db.query(ContactInquiry).filter(
        func.lower(ContactInquiry.email) == current_user.email.lower()
    )
    stats_inquiries = base_query.all()
    total = base_query.count()
    pages = max((total + page_size - 1) // page_size, 1)
    if page > pages:
        page = pages

    inquiries = (
        base_query.order_by(ContactInquiry.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [_serialize_support_inquiry(item) for item in inquiries],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "stats": {
            "total_support": len(stats_inquiries),
            "new_support": len([item for item in stats_inquiries if item.status == "new"]),
            "in_progress_support": len([item for item in stats_inquiries if item.status == "in_progress"]),
            "resolved_support": len([item for item in stats_inquiries if item.status in {"resolved", "closed"}]),
        },
    }
