import uuid
import secrets
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from app.database import get_db
from app.config import get_settings
from app.models import Cart, License, Product, ProductCategory, ProductImage, Order, OrderItem, ContactInquiry, CustomProjectRequest, User
from app.schemas import ProductOut, AdminStats
from app.routers.auth import pwd_context, require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

UPLOAD_DIR = Path("app/static/uploads/products")
PRODUCT_FILE_DIR = Path("storage/product_files")
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
ALLOWED_PRODUCT_FILE_EXTENSIONS = {
    ".ex4",
    ".ex5",
    ".mq4",
    ".mq5",
    ".zip",
    ".rar",
    ".7z",
    ".pdf",
    ".txt",
    ".set",
}
VALID_USER_ROLES = {"customer", "admin"}
VALID_USER_STATUSES = {"active", "suspended", "disabled"}
VALID_LICENSE_STATUSES = {"active", "expired", "revoked", "suspended"}
VALID_LICENSE_ACTIVATION_TYPES = {"ea_account", "device"}


def _save_product_upload(file: UploadFile) -> str:
    suffix = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if not suffix:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, WebP, and GIF images are allowed")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename
    max_bytes = get_settings().max_upload_size_bytes
    total = 0

    try:
        with destination.open("wb") as buffer:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Image upload exceeds the {get_settings().max_upload_size_mb} MB limit",
                    )
                buffer.write(chunk)
    except HTTPException:
        if destination.exists():
            destination.unlink()
        raise

    if total == 0:
        if destination.exists():
            destination.unlink()
        raise HTTPException(status_code=400, detail="Uploaded image is empty")

    return f"/static/uploads/products/{filename}"


def _safe_filename(filename: str) -> str:
    name = Path(filename or "product-file").name
    stem = Path(name).stem or "product-file"
    suffix = Path(name).suffix.lower()
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", stem).strip(".-") or "product-file"
    return f"{safe_stem[:80]}{suffix}"


def _product_file_storage_path(product_id: int, filename: str) -> Path:
    safe_name = _safe_filename(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_PRODUCT_FILE_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_PRODUCT_FILE_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported product file type. Allowed: {allowed}")
    return PRODUCT_FILE_DIR / str(product_id) / f"{uuid.uuid4().hex}_{safe_name}"


def _delete_existing_product_file(product: Product) -> None:
    if not product.product_file_path:
        return
    path = Path(product.product_file_path)
    root = PRODUCT_FILE_DIR.resolve()
    try:
        resolved = path.resolve()
    except OSError:
        return
    if root in resolved.parents and resolved.exists() and resolved.is_file():
        resolved.unlink()


def _save_product_file_upload(product: Product, file: UploadFile) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Product file name is required")
    destination = _product_file_storage_path(product.id, file.filename)
    destination.parent.mkdir(parents=True, exist_ok=True)

    max_bytes = get_settings().max_product_file_size_bytes
    total = 0
    try:
        with destination.open("wb") as buffer:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Product file upload exceeds the {get_settings().max_product_file_size_mb} MB limit",
                    )
                buffer.write(chunk)
    except HTTPException:
        if destination.exists():
            destination.unlink()
        raise

    if total == 0:
        if destination.exists():
            destination.unlink()
        raise HTTPException(status_code=400, detail="Uploaded product file is empty")

    _delete_existing_product_file(product)
    product.product_file_path = str(destination)
    product.product_file_name = Path(file.filename).name
    product.product_file_size = total
    product.product_file_uploaded_at = _now()
    product.download_url = None
    return {
        "product_file_name": product.product_file_name,
        "product_file_size": product.product_file_size,
        "product_file_uploaded_at": product.product_file_uploaded_at.isoformat(),
    }


def _customer_orders_query(db: Session, user: User):
    return (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(
            or_(
                Order.user_id == user.id,
                func.lower(Order.customer_email) == user.email.lower(),
            )
        )
    )


def _normalize_user_status(user: User) -> str:
    return user.status or "active"


def _active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == "admin", User.status == "active").count()


def _is_last_active_admin(db: Session, user: User) -> bool:
    return user.role == "admin" and _normalize_user_status(user) == "active" and _active_admin_count(db) <= 1


def _validate_user_payload(data: dict, creating: bool = False) -> dict:
    email = (data.get("email") or "").strip().lower()
    full_name = (data.get("full_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    role = (data.get("role") or "customer").strip().lower()
    status = (data.get("status") or "active").strip().lower()
    password = data.get("password") or ""

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")
    if not full_name:
        raise HTTPException(status_code=400, detail="Full name is required")
    if role not in VALID_USER_ROLES:
        raise HTTPException(status_code=400, detail="Role must be customer or admin")
    if status not in VALID_USER_STATUSES:
        raise HTTPException(status_code=400, detail="Status must be active, suspended, or disabled")
    if creating and len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if password and len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    return {
        "email": email,
        "full_name": full_name,
        "phone": phone or None,
        "role": role,
        "status": status,
        "password": password,
    }


def _serialize_order(order: Order) -> dict:
    return {
        "id": order.id,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "status": order.status,
        "total_amount": str(order.total_amount),
        "currency": order.currency,
        "items": [
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "total_price": str(item.total_price),
            }
            for item in order.items
        ],
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def _customer_summary(db: Session, user: User) -> dict:
    orders = _customer_orders_query(db, user).order_by(Order.created_at.desc()).all()
    total_value = sum((order.total_amount or Decimal("0")) for order in orders)
    paid_value = sum((order.total_amount or Decimal("0")) for order in orders if order.status == "paid")
    latest_order = orders[0] if orders else None
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role,
        "status": _normalize_user_status(user),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "order_count": len(orders),
        "confirmed_orders": len([order for order in orders if order.status == "confirmed"]),
        "paid_orders": len([order for order in orders if order.status == "paid"]),
        "total_order_value": str(total_value),
        "paid_order_value": str(paid_value),
        "latest_order_at": latest_order.created_at.isoformat() if latest_order and latest_order.created_at else None,
    }


def _user_management_stats(db: Session) -> dict:
    paid_value = db.query(func.sum(Order.total_amount)).filter(Order.status == "paid").scalar() or Decimal("0")
    active_users = db.query(User).filter(or_(User.status == "active", User.status.is_(None))).count()
    total_users = db.query(User).count()
    return {
        "total_users": total_users,
        "active_users": active_users,
        "restricted_users": max(total_users - active_users, 0),
        "paid_value": str(paid_value),
    }


def _order_management_stats(db: Session) -> dict:
    paid_revenue = db.query(func.sum(Order.total_amount)).filter(Order.status == "paid").scalar() or Decimal("0")
    return {
        "total_orders": db.query(Order).count(),
        "confirmed_orders": db.query(Order).filter(Order.status == "confirmed").count(),
        "pending_orders": db.query(Order).filter(Order.status == "pending").count(),
        "paid_revenue": str(paid_revenue),
    }


def _inquiry_management_stats(db: Session) -> dict:
    active_statuses = ("in_progress", "reviewing", "contacted")
    contact_new = db.query(ContactInquiry).filter(ContactInquiry.status == "new").count()
    project_new = db.query(CustomProjectRequest).filter(CustomProjectRequest.status == "new").count()
    contact_active = db.query(ContactInquiry).filter(ContactInquiry.status.in_(active_statuses)).count()
    project_active = db.query(CustomProjectRequest).filter(CustomProjectRequest.status.in_(active_statuses)).count()
    return {
        "contact_total": db.query(ContactInquiry).count(),
        "project_total": db.query(CustomProjectRequest).count(),
        "new_total": contact_new + project_new,
        "active_total": contact_active + project_active,
    }


def _product_management_stats(db: Session) -> dict:
    active_products = db.query(Product).filter(Product.status == "active").count()
    total_products = db.query(Product).count()
    featured_products = db.query(Product).filter(Product.featured.is_(True)).count()
    return {
        "total_products": total_products,
        "active_products": active_products,
        "hidden_products": max(total_products - active_products, 0),
        "featured_products": featured_products,
    }


def _serialize_product_list(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "short_description": product.short_description,
        "price": str(product.price),
        "currency": product.currency,
        "category_id": product.category_id,
        "category_name": product.category.name if product.category else None,
        "category_slug": product.category.slug if product.category else None,
        "status": product.status,
        "platform": product.platform,
        "version": product.version,
        "thumbnail_url": product.thumbnail_url,
        "product_file_name": product.product_file_name,
        "product_file_size": product.product_file_size,
        "product_file_uploaded_at": product.product_file_uploaded_at.isoformat() if product.product_file_uploaded_at else None,
        "featured": product.featured,
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    clean_value = value.strip()
    if not clean_value:
        return None
    try:
        return datetime.fromisoformat(clean_value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expiry date")


def _generate_license_key() -> str:
    return f"TFE-{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}"


def _serialize_license(license_record: License, include_checks: bool = False) -> dict:
    product = license_record.product
    user = license_record.user
    data = {
        "id": license_record.id,
        "license_key": license_record.license_key,
        "status": license_record.status,
        "activation_type": license_record.activation_type or "ea_account",
        "allowed_mt_account_number": license_record.allowed_mt_account_number,
        "allowed_broker_server": license_record.allowed_broker_server,
        "device_fingerprint": license_record.device_fingerprint,
        "expires_at": license_record.expires_at.isoformat() if license_record.expires_at else None,
        "activated_at": license_record.activated_at.isoformat() if license_record.activated_at else None,
        "mt_account_updated_at": license_record.mt_account_updated_at.isoformat() if license_record.mt_account_updated_at else None,
        "last_checked_at": license_record.last_checked_at.isoformat() if license_record.last_checked_at else None,
        "last_check_status": license_record.last_check_status,
        "last_check_message": license_record.last_check_message,
        "created_at": license_record.created_at.isoformat() if license_record.created_at else None,
        "updated_at": license_record.updated_at.isoformat() if license_record.updated_at else None,
        "user": {
            "id": user.id if user else None,
            "email": user.email if user else None,
            "full_name": user.full_name if user else None,
        },
        "product": {
            "id": product.id if product else None,
            "name": product.name if product else None,
            "slug": product.slug if product else None,
            "platform": product.platform if product else None,
        },
        "order_id": license_record.order_id,
    }
    if include_checks:
        checks = sorted(license_record.checks, key=lambda item: item.checked_at or datetime.min, reverse=True)[:25]
        data["checks"] = [
            {
                "id": check.id,
                "product_code": check.product_code,
                "mt_account_number": check.mt_account_number,
                "platform": check.platform,
                "client_version": check.client_version,
                "result": check.result,
                "message": check.message,
                "ip_address": check.ip_address,
                "checked_at": check.checked_at.isoformat() if check.checked_at else None,
            }
            for check in checks
        ]
    return data


def _validate_license_payload(data: dict, creating: bool = False) -> dict:
    user_id = int(data.get("user_id") or 0)
    product_id = int(data.get("product_id") or 0)
    order_id = data.get("order_id")
    status = (data.get("status") or "active").strip().lower()
    activation_type = (data.get("activation_type") or "ea_account").strip().lower()
    license_key = (data.get("license_key") or "").strip().upper()

    if not user_id:
        raise HTTPException(status_code=400, detail="Customer is required")
    if not product_id:
        raise HTTPException(status_code=400, detail="Product is required")
    if status not in VALID_LICENSE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid license status")
    if activation_type not in VALID_LICENSE_ACTIVATION_TYPES:
        raise HTTPException(status_code=400, detail="Invalid activation type")
    if creating and not license_key:
        license_key = _generate_license_key()

    return {
        "user_id": user_id,
        "product_id": product_id,
        "order_id": int(order_id) if order_id else None,
        "license_key": license_key,
        "status": status,
        "activation_type": activation_type,
        "allowed_mt_account_number": (data.get("allowed_mt_account_number") or "").strip() or None,
        "allowed_broker_server": (data.get("allowed_broker_server") or "").strip() or None,
        "device_fingerprint": (data.get("device_fingerprint") or "").strip() or None,
        "expires_at": _parse_datetime(data.get("expires_at")),
    }


def _serialize_contact_inquiry(inquiry: ContactInquiry) -> dict:
    return {
        "id": inquiry.id,
        "name": inquiry.name,
        "email": inquiry.email,
        "phone": inquiry.phone,
        "company": inquiry.company,
        "subject": inquiry.subject,
        "message": inquiry.message,
        "service_type": inquiry.service_type,
        "status": inquiry.status,
        "created_at": inquiry.created_at.isoformat() if inquiry.created_at else None,
        "updated_at": inquiry.updated_at.isoformat() if inquiry.updated_at else None,
    }


def _serialize_project_request(project_request: CustomProjectRequest) -> dict:
    return {
        "id": project_request.id,
        "name": project_request.name,
        "email": project_request.email,
        "phone": project_request.phone,
        "company": project_request.company,
        "project_type": project_request.project_type,
        "budget_range": project_request.budget_range,
        "timeline": project_request.timeline,
        "description": project_request.description,
        "status": project_request.status,
        "created_at": project_request.created_at.isoformat() if project_request.created_at else None,
        "updated_at": project_request.updated_at.isoformat() if project_request.updated_at else None,
    }


def _paginate_query(query, page: int, page_size: int):
    total = query.count()
    pages = max((total + page_size - 1) // page_size, 1)
    if page > pages:
        page = pages
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total, page, pages


@router.get("/stats", response_model=AdminStats)
def get_stats(db: Session = Depends(get_db)):
    total_products = db.query(Product).count()
    active_products = db.query(Product).filter(Product.status == "active").count()
    total_orders = db.query(Order).count()
    confirmed_orders = db.query(Order).filter(Order.status == "confirmed").count()
    total_inquiries = db.query(ContactInquiry).count()
    project_requests = db.query(CustomProjectRequest).count()
    revenue = db.query(func.sum(Order.total_amount)).filter(Order.status == "paid").scalar() or Decimal("0")
    return AdminStats(
        total_products=total_products,
        active_products=active_products,
        total_orders=total_orders,
        confirmed_orders=confirmed_orders,
        total_inquiries=total_inquiries,
        project_requests=project_requests,
        revenue=revenue,
    )


@router.get("/licenses")
def list_licenses(
    status: str | None = Query(None),
    activation_type: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(License).options(joinedload(License.product), joinedload(License.user))
    if status:
        query = query.filter(License.status == status)
    if activation_type:
        query = query.filter(License.activation_type == activation_type)
    if search:
        like = f"%{search.strip().lower()}%"
        query = query.outerjoin(User, License.user_id == User.id).outerjoin(Product, License.product_id == Product.id).filter(
            or_(
                func.lower(License.license_key).like(like),
                func.lower(License.allowed_mt_account_number).like(like),
                func.lower(License.status).like(like),
                func.lower(User.email).like(like),
                func.lower(User.full_name).like(like),
                func.lower(Product.name).like(like),
                func.lower(Product.slug).like(like),
            )
        )

    items, total, page, pages = _paginate_query(query.order_by(License.created_at.desc()), page, page_size)
    all_licenses = db.query(License).all()
    return {
        "items": [_serialize_license(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "stats": {
            "total_licenses": len(all_licenses),
            "active_licenses": len([item for item in all_licenses if (item.status or "active") == "active"]),
            "assigned_accounts": len([item for item in all_licenses if item.allowed_mt_account_number]),
            "recent_checks": len([item for item in all_licenses if item.last_checked_at]),
        },
    }


@router.post("/licenses", status_code=201)
def create_license(data: dict, db: Session = Depends(get_db)):
    payload = _validate_license_payload(data, creating=True)
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    product = db.query(Product).filter(Product.id == payload["product_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if payload["order_id"] and not db.query(Order).filter(Order.id == payload["order_id"]).first():
        raise HTTPException(status_code=404, detail="Order not found")
    existing = db.query(License).filter(func.upper(License.license_key) == payload["license_key"]).first()
    if existing:
        raise HTTPException(status_code=409, detail="License key already exists")

    license_record = License(**payload, created_at=_now(), updated_at=_now())
    if payload["allowed_mt_account_number"]:
        license_record.mt_account_updated_at = _now()
    db.add(license_record)
    db.commit()
    db.refresh(license_record)
    return _serialize_license(license_record)


@router.get("/licenses/{license_id}")
def get_license(license_id: int, db: Session = Depends(get_db)):
    license_record = (
        db.query(License)
        .options(joinedload(License.product), joinedload(License.user), joinedload(License.checks))
        .filter(License.id == license_id)
        .first()
    )
    if not license_record:
        raise HTTPException(status_code=404, detail="License not found")
    return _serialize_license(license_record, include_checks=True)


@router.put("/licenses/{license_id}")
def update_license(license_id: int, data: dict, db: Session = Depends(get_db)):
    license_record = db.query(License).filter(License.id == license_id).first()
    if not license_record:
        raise HTTPException(status_code=404, detail="License not found")

    payload = _validate_license_payload(data)
    if not db.query(User).filter(User.id == payload["user_id"]).first():
        raise HTTPException(status_code=404, detail="Customer not found")
    if not db.query(Product).filter(Product.id == payload["product_id"]).first():
        raise HTTPException(status_code=404, detail="Product not found")
    existing = (
        db.query(License)
        .filter(func.upper(License.license_key) == payload["license_key"], License.id != license_record.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="License key already exists")

    old_account = license_record.allowed_mt_account_number
    for key, value in payload.items():
        setattr(license_record, key, value)
    if old_account != payload["allowed_mt_account_number"]:
        license_record.mt_account_updated_at = _now() if payload["allowed_mt_account_number"] else None
    license_record.updated_at = _now()
    db.commit()
    db.refresh(license_record)
    return _serialize_license(license_record)


@router.delete("/licenses/{license_id}", status_code=204)
def delete_license(license_id: int, db: Session = Depends(get_db)):
    license_record = db.query(License).filter(License.id == license_id).first()
    if not license_record:
        raise HTTPException(status_code=404, detail="License not found")
    db.delete(license_record)
    db.commit()
    return None


@router.get("/customers")
def list_customers(
    role: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    if search:
        like = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(User.full_name).like(like),
                func.lower(User.email).like(like),
                func.lower(User.phone).like(like),
                func.lower(User.role).like(like),
                func.lower(User.status).like(like),
            )
        )

    total = query.count()
    pages = max((total + page_size - 1) // page_size, 1)
    if page > pages:
        page = pages

    users = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [_customer_summary(db, user) for user in users],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "stats": _user_management_stats(db),
    }


@router.post("/customers", status_code=201)
def create_customer(data: dict, db: Session = Depends(get_db)):
    payload = _validate_user_payload(data, creating=True)
    existing = db.query(User).filter(func.lower(User.email) == payload["email"]).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")

    user = User(
        email=payload["email"],
        full_name=payload["full_name"],
        phone=payload["phone"],
        role=payload["role"],
        status=payload["status"],
        password_hash=pwd_context.hash(payload["password"]),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _customer_summary(db, user)


@router.get("/customers/{user_id}")
def get_customer(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")

    orders = _customer_orders_query(db, user).order_by(Order.created_at.desc()).all()
    data = _customer_summary(db, user)
    data["orders"] = [_serialize_order(order) for order in orders]
    return data


@router.put("/customers/{user_id}")
def update_customer(
    user_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    payload = _validate_user_payload(data)
    existing = (
        db.query(User)
        .filter(func.lower(User.email) == payload["email"], User.id != user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")

    if user.id == current_user.id and (payload["role"] != user.role or payload["status"] != _normalize_user_status(user)):
        raise HTTPException(status_code=400, detail="You cannot change your own role or status")
    if _is_last_active_admin(db, user) and (payload["role"] != "admin" or payload["status"] != "active"):
        raise HTTPException(status_code=400, detail="At least one active admin account is required")

    user.email = payload["email"]
    user.full_name = payload["full_name"]
    user.phone = payload["phone"]
    user.role = payload["role"]
    user.status = payload["status"]
    if payload["password"]:
        user.password_hash = pwd_context.hash(payload["password"])

    db.commit()
    db.refresh(user)
    return _customer_summary(db, user)


@router.delete("/customers/{user_id}", status_code=204)
def delete_customer(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account")
    if _is_last_active_admin(db, user):
        raise HTTPException(status_code=400, detail="At least one active admin account is required")

    order_count = _customer_orders_query(db, user).count()
    license_count = db.query(License).filter(License.user_id == user.id).count()
    if order_count or license_count:
        raise HTTPException(status_code=409, detail="This user has order or license history. Suspend or disable the account instead.")

    db.query(Cart).filter(Cart.user_id == user.id).update({Cart.user_id: None}, synchronize_session=False)
    db.delete(user)
    db.commit()
    return None


@router.get("/products")
def list_products(
    status: str | None = Query(None),
    category_id: int | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Product).outerjoin(ProductCategory).options(joinedload(Product.category))
    if status:
        query = query.filter(Product.status == status)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if search:
        like = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Product.name).like(like),
                func.lower(Product.slug).like(like),
                func.lower(Product.short_description).like(like),
                func.lower(Product.description).like(like),
                func.lower(Product.platform).like(like),
                func.lower(Product.version).like(like),
                func.lower(Product.status).like(like),
                func.lower(ProductCategory.name).like(like),
                func.lower(ProductCategory.slug).like(like),
            )
        )
    products, total, page, pages = _paginate_query(query.order_by(Product.created_at.desc()), page, page_size)
    return {
        "items": [_serialize_product_list(product) for product in products],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "stats": _product_management_stats(db),
    }


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).options(joinedload(Product.category), joinedload(Product.images)).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/products/{product_id}/thumbnail")
def upload_product_thumbnail(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    image_url = _save_product_upload(file)
    product.thumbnail_url = image_url
    return {"thumbnail_url": image_url}


@router.post("/products/{product_id}/file")
def upload_product_file(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    data = _save_product_file_upload(product, file)
    db.commit()
    db.refresh(product)
    return data


@router.delete("/products/{product_id}/file", status_code=204)
def delete_product_file(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    _delete_existing_product_file(product)
    product.product_file_path = None
    product.product_file_name = None
    product.product_file_size = None
    product.product_file_uploaded_at = None
    product.download_url = None
    db.commit()
    return None


@router.post("/products/{product_id}/images", status_code=201)
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    alt_text: str = Form(""),
    sort_order: int = Form(0),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    image_url = _save_product_upload(file)
    image = ProductImage(
        product_id=product.id,
        image_url=image_url,
        alt_text=alt_text.strip() or None,
        sort_order=sort_order,
    )
    db.add(image)
    db.flush()
    return {
        "id": image.id,
        "image_url": image.image_url,
        "alt_text": image.alt_text,
        "sort_order": image.sort_order,
    }


@router.put("/products/{product_id}/images/{image_id}")
def update_product_image(
    product_id: int,
    image_id: int,
    data: dict,
    db: Session = Depends(get_db),
):
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id,
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Product image not found")

    if "alt_text" in data:
        image.alt_text = (data.get("alt_text") or "").strip() or None
    if "sort_order" in data:
        image.sort_order = int(data.get("sort_order") or 0)
    return {
        "id": image.id,
        "image_url": image.image_url,
        "alt_text": image.alt_text,
        "sort_order": image.sort_order,
    }


@router.delete("/products/{product_id}/images/{image_id}", status_code=204)
def delete_product_image(product_id: int, image_id: int, db: Session = Depends(get_db)):
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id,
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Product image not found")

    db.delete(image)
    return None


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(data: dict, db: Session = Depends(get_db)):
    product = Product(**{k: v for k, v in data.items() if hasattr(Product, k) and k not in ("id", "created_at", "updated_at")})
    db.add(product)
    db.flush()
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: dict, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for key, value in data.items():
        if hasattr(product, key) and key not in ("id", "created_at"):
            setattr(product, key, value)
    return product


@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    return None


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    categories = db.query(ProductCategory).order_by(ProductCategory.name.asc()).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "description": c.description,
            "product_count": db.query(Product).filter(Product.category_id == c.id).count(),
        }
        for c in categories
    ]


@router.post("/categories", status_code=201)
def create_category(data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    slug = (data.get("slug") or "").strip().lower()
    if not name or not slug:
        raise HTTPException(status_code=400, detail="Name and slug are required")
    existing = db.query(ProductCategory).filter(ProductCategory.slug == slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Category slug already exists")
    cat = ProductCategory(name=name, slug=slug, description=data.get("description", ""))
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name, "slug": cat.slug}


@router.put("/categories/{category_id}")
def update_category(category_id: int, data: dict, db: Session = Depends(get_db)):
    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    name = (data.get("name") or "").strip()
    slug = (data.get("slug") or "").strip().lower()
    if not name or not slug:
        raise HTTPException(status_code=400, detail="Name and slug are required")

    existing = (
        db.query(ProductCategory)
        .filter(ProductCategory.slug == slug, ProductCategory.id != category_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Category slug already exists")

    category.name = name
    category.slug = slug
    category.description = data.get("description", "")
    db.commit()
    db.refresh(category)
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "product_count": db.query(Product).filter(Product.category_id == category.id).count(),
    }


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    product_count = db.query(Product).filter(Product.category_id == category_id).count()
    if product_count:
        raise HTTPException(status_code=409, detail="Move products out of this category before deleting it")

    db.delete(category)
    db.commit()
    return None


@router.get("/orders")
def list_orders(
    status: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Order).options(joinedload(Order.items))
    if status:
        query = query.filter(Order.status == status)
    if search:
        clean_search = search.strip().lower().lstrip("#")
        like = f"%{clean_search}%"
        filters = [
            func.lower(Order.customer_name).like(like),
            func.lower(Order.customer_email).like(like),
            func.lower(Order.status).like(like),
            func.lower(Order.currency).like(like),
            Order.items.any(func.lower(OrderItem.product_name).like(like)),
        ]
        if clean_search.isdigit():
            filters.append(Order.id == int(clean_search))
        query = query.filter(or_(*filters))

    total = query.count()
    pages = max((total + page_size - 1) // page_size, 1)
    if page > pages:
        page = pages

    orders = (
        query.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [_serialize_order(order) for order in orders],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "stats": _order_management_stats(db),
    }


@router.put("/orders/{order_id}/status")
def update_order_status(order_id: int, data: dict, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if "status" in data:
        order.status = data["status"]
        db.commit()
        db.refresh(order)
    return {"message": "Order status updated", "status": order.status}


@router.get("/inquiries")
def list_inquiries(
    status: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(ContactInquiry)
    if status:
        query = query.filter(ContactInquiry.status == status)
    if search:
        like = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(ContactInquiry.name).like(like),
                func.lower(ContactInquiry.email).like(like),
                func.lower(ContactInquiry.phone).like(like),
                func.lower(ContactInquiry.company).like(like),
                func.lower(ContactInquiry.subject).like(like),
                func.lower(ContactInquiry.service_type).like(like),
                func.lower(ContactInquiry.message).like(like),
                func.lower(ContactInquiry.status).like(like),
            )
        )
    items, total, page, pages = _paginate_query(query.order_by(ContactInquiry.created_at.desc()), page, page_size)
    return {
        "items": [_serialize_contact_inquiry(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "stats": _inquiry_management_stats(db),
    }


@router.put("/inquiries/{inquiry_id}")
def update_inquiry_status(inquiry_id: int, data: dict, db: Session = Depends(get_db)):
    inquiry = db.query(ContactInquiry).filter(ContactInquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    if "status" in data:
        inquiry.status = data["status"]
        db.commit()
        db.refresh(inquiry)
    return {"message": "Inquiry updated", "status": inquiry.status}


@router.get("/project-requests")
def list_project_requests(
    status: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(CustomProjectRequest)
    if status:
        query = query.filter(CustomProjectRequest.status == status)
    if search:
        like = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(CustomProjectRequest.name).like(like),
                func.lower(CustomProjectRequest.email).like(like),
                func.lower(CustomProjectRequest.phone).like(like),
                func.lower(CustomProjectRequest.company).like(like),
                func.lower(CustomProjectRequest.project_type).like(like),
                func.lower(CustomProjectRequest.budget_range).like(like),
                func.lower(CustomProjectRequest.timeline).like(like),
                func.lower(CustomProjectRequest.description).like(like),
                func.lower(CustomProjectRequest.status).like(like),
            )
        )
    items, total, page, pages = _paginate_query(query.order_by(CustomProjectRequest.created_at.desc()), page, page_size)
    return {
        "items": [_serialize_project_request(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "stats": _inquiry_management_stats(db),
    }


@router.put("/project-requests/{request_id}")
def update_project_request_status(request_id: int, data: dict, db: Session = Depends(get_db)):
    project_request = db.query(CustomProjectRequest).filter(CustomProjectRequest.id == request_id).first()
    if not project_request:
        raise HTTPException(status_code=404, detail="Project request not found")
    if "status" in data:
        project_request.status = data["status"]
        db.commit()
        db.refresh(project_request)
    return {"message": "Project request updated", "status": project_request.status}
