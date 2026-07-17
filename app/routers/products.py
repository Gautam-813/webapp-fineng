from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import Case
from app.database import get_db
from app.models import Product, ProductCategory
from app.schemas import ProductOut, ProductListOut, ProductCategoryOut

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


@router.get("/products", response_model=list[ProductListOut])
def list_products(
    category: str | None = Query(None),
    search: str | None = Query(None),
    sort: str | None = Query(None),
    featured: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Product).filter(Product.status == "active")

    if featured is not None:
        query = query.filter(Product.featured == featured)

    if category:
        query = query.join(ProductCategory).filter(ProductCategory.slug == category)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            Product.name.ilike(pattern) | Product.short_description.ilike(pattern)
        )

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "name":
        query = query.order_by(Product.name.asc())
    else:
        query = query.order_by(Product.created_at.desc())

    products = query.all()
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
            platform=p.platform,
            version=p.version,
            thumbnail_url=p.thumbnail_url,
            featured=p.featured,
        )
        for p in products
    ]


@router.get("/products/{slug}", response_model=ProductOut)
def get_product(slug: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.slug == slug, Product.status == "active").first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
