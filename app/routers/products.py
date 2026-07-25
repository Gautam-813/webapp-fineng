from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import Product, ProductCategory
from app.schemas import ProductOut, ProductCategoryOut

router = APIRouter(prefix="/api", tags=["products"])


@router.get("/categories", response_model=list[ProductCategoryOut])
def list_categories(db: Session = Depends(get_db)):
    categories = db.query(ProductCategory).all()
    result = []
    for cat in categories:
        count = (
            db.query(Product)
            .filter(Product.category_id == cat.id, Product.status == "active")
            .count()
        )
        result.append(
            ProductCategoryOut(
                id=cat.id,
                name=cat.name,
                slug=cat.slug,
                description=cat.description,
                product_count=count,
            )
        )
    return result


def _serialize_product(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "short_description": product.short_description,
        "price": str(product.price),
        "currency": product.currency,
        "category_name": product.category.name if product.category else None,
        "category_slug": product.category.slug if product.category else None,
        "status": product.status,
        "platform": product.platform,
        "version": product.version,
        "thumbnail_url": product.thumbnail_url,
        "featured": product.featured,
    }


def _product_catalog_stats(db: Session) -> dict:
    active_products = db.query(Product).filter(Product.status == "active").count()
    featured_products = db.query(Product).filter(Product.status == "active", Product.featured.is_(True)).count()
    categories_with_products = (
        db.query(Product.category_id)
        .filter(Product.status == "active", Product.category_id.isnot(None))
        .distinct()
        .count()
    )
    return {
        "active_products": active_products,
        "featured_products": featured_products,
        "categories_with_products": categories_with_products,
    }


@router.get("/products")
def list_products(
    category: str | None = Query(None),
    platform: str | None = Query(None),
    search: str | None = Query(None),
    sort: str | None = Query(None),
    featured: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=6, le=48),
    db: Session = Depends(get_db),
):
    query = db.query(Product).outerjoin(ProductCategory).filter(Product.status == "active")

    if featured is not None:
        query = query.filter(Product.featured == featured)

    if category:
        query = query.filter(ProductCategory.slug == category)

    if platform:
        query = query.filter(Product.platform.ilike(f"%{platform.strip()}%"))

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Product.name.ilike(pattern),
                Product.slug.ilike(pattern),
                Product.short_description.ilike(pattern),
                Product.description.ilike(pattern),
                Product.platform.ilike(pattern),
                Product.version.ilike(pattern),
                ProductCategory.name.ilike(pattern),
            )
        )

    if sort == "featured":
        query = query.order_by(Product.featured.desc(), Product.created_at.desc())
    elif sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "name":
        query = query.order_by(Product.name.asc())
    else:
        query = query.order_by(Product.created_at.desc())

    total = query.count()
    pages = max((total + page_size - 1) // page_size, 1)
    if page > pages:
        page = pages

    products = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_serialize_product(product) for product in products],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "stats": _product_catalog_stats(db),
    }


@router.get("/products/{slug}", response_model=ProductOut)
def get_product(slug: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.slug == slug, Product.status == "active").first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
