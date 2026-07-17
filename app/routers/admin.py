import shutil
import uuid
from decimal import Decimal
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.database import get_db
from app.models import Product, ProductCategory, ProductImage, Order, ContactInquiry, CustomProjectRequest
from app.schemas import ProductOut, ProductListOut, AdminStats
from app.routers.auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

UPLOAD_DIR = Path("app/static/uploads/products")
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _save_product_upload(file: UploadFile) -> str:
    suffix = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if not suffix:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, WebP, and GIF images are allowed")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return f"/static/uploads/products/{filename}"


@router.get("/stats", response_model=AdminStats)
def get_stats(db: Session = Depends(get_db)):
    total_products = db.query(Product).count()
    total_orders = db.query(Order).count()
    total_inquiries = db.query(ContactInquiry).count()
    revenue = db.query(func.sum(Order.total_amount)).filter(Order.status == "paid").scalar() or Decimal("0")
    return AdminStats(
        total_products=total_products,
        total_orders=total_orders,
        total_inquiries=total_inquiries,
        revenue=revenue,
    )


@router.get("/products", response_model=list[ProductListOut])
def list_products(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if status:
        query = query.filter(Product.status == status)
    products = query.order_by(Product.created_at.desc()).all()
    return [
        ProductListOut(
            id=p.id,
            name=p.name,
            slug=p.slug,
            short_description=p.short_description,
            price=p.price,
            currency=p.currency,
            category_name=p.category.name if p.category else None,
            category_slug=p.category.slug if p.category else None,
            status=p.status,
            platform=p.platform,
            version=p.version,
            thumbnail_url=p.thumbnail_url,
            featured=p.featured,
        )
        for p in products
    ]


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
    categories = db.query(ProductCategory).all()
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
    existing = db.query(ProductCategory).filter(ProductCategory.slug == data.get("slug")).first()
    if existing:
        raise HTTPException(status_code=409, detail="Category slug already exists")
    cat = ProductCategory(name=data["name"], slug=data["slug"], description=data.get("description", ""))
    db.add(cat)
    return {"id": cat.id, "name": cat.name, "slug": cat.slug}


@router.get("/orders")
def list_orders(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Order).options(joinedload(Order.items))
    if status:
        query = query.filter(Order.status == status)
    orders = query.order_by(Order.created_at.desc()).all()
    return [
        {
            "id": o.id,
            "customer_name": o.customer_name,
            "customer_email": o.customer_email,
            "status": o.status,
            "total_amount": str(o.total_amount),
            "currency": o.currency,
            "items": [{"product_name": i.product_name, "quantity": i.quantity, "unit_price": str(i.unit_price), "total_price": str(i.total_price)} for i in o.items],
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in orders
    ]


@router.put("/orders/{order_id}/status")
def update_order_status(order_id: int, data: dict, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if "status" in data:
        order.status = data["status"]
    return {"message": "Order status updated", "status": order.status}


@router.get("/inquiries")
def list_inquiries(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(ContactInquiry)
    if status:
        query = query.filter(ContactInquiry.status == status)
    return query.order_by(ContactInquiry.created_at.desc()).all()


@router.put("/inquiries/{inquiry_id}")
def update_inquiry_status(inquiry_id: int, data: dict, db: Session = Depends(get_db)):
    inquiry = db.query(ContactInquiry).filter(ContactInquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    if "status" in data:
        inquiry.status = data["status"]
    return {"message": "Inquiry updated", "status": inquiry.status}


@router.get("/project-requests")
def list_project_requests(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(CustomProjectRequest)
    if status:
        query = query.filter(CustomProjectRequest.status == status)
    return query.order_by(CustomProjectRequest.created_at.desc()).all()
