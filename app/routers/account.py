from decimal import Decimal
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import ContactInquiry, CustomProjectRequest, Order, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/account", tags=["account"])


class ProfileUpdateIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)


def _account_order_filter(current_user: User):
    return or_(
        Order.user_id == current_user.id,
        func.lower(Order.customer_email) == current_user.email.lower(),
    )


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
