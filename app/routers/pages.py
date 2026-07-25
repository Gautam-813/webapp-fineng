from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Product, ProductCategory

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    active_product_count = db.query(Product).filter(Product.status == "active").count()
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "active_product_count": active_product_count,
        },
    )


@router.get("/products")
def products_page(request: Request, db: Session = Depends(get_db)):
    products = (
        db.query(Product)
        .filter(Product.status == "active")
        .order_by(Product.created_at.desc())
        .limit(12)
        .all()
    )
    categories = db.query(ProductCategory).order_by(ProductCategory.name.asc()).all()
    active_product_count = db.query(Product).filter(Product.status == "active").count()
    return templates.TemplateResponse(
        "products.html",
        {
            "request": request,
            "products": products,
            "categories": categories,
            "active_product_count": active_product_count,
        },
    )


@router.get("/products/{slug}")
def product_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.slug == slug, Product.status == "active").first()
    if not product:
        return templates.TemplateResponse(
            "404.html",
            {"request": request},
            status_code=404,
        )
    related = (
        db.query(Product)
        .filter(
            Product.category_id == product.category_id,
            Product.id != product.id,
            Product.status == "active",
        )
        .limit(4)
        .all()
    )
    return templates.TemplateResponse(
        "product_detail.html",
        {
            "request": request,
            "product": product,
            "related_products": related,
        },
    )


@router.get("/cart")
def cart_page(request: Request):
    return templates.TemplateResponse("cart.html", {"request": request})


@router.get("/checkout")
def checkout_page(request: Request):
    return templates.TemplateResponse("checkout.html", {"request": request})


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/forgot-password")
def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})


@router.get("/account")
def account_page(request: Request):
    return templates.TemplateResponse("account.html", {"request": request, "account_active": "dashboard"})


@router.get("/account/orders")
def account_orders_page(request: Request):
    return templates.TemplateResponse("account_orders.html", {"request": request, "account_active": "orders"})


@router.get("/account/profile")
def account_profile_page(request: Request):
    return templates.TemplateResponse("account_profile.html", {"request": request, "account_active": "profile"})


@router.get("/account/support")
def account_support_page(request: Request):
    return templates.TemplateResponse("account_support.html", {"request": request, "account_active": "support"})


@router.get("/account/projects")
def account_projects_page(request: Request):
    return templates.TemplateResponse("account_projects.html", {"request": request, "account_active": "projects"})


@router.get("/about")
def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@router.get("/contact")
def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})


@router.get("/risk-disclaimer")
def risk_disclaimer(request: Request):
    return templates.TemplateResponse("risk_disclaimer.html", {"request": request})


@router.get("/terms")
def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})


@router.get("/privacy-policy")
def privacy_policy(request: Request):
    return templates.TemplateResponse("privacy_policy.html", {"request": request})


@router.get("/refund-policy")
def refund_policy(request: Request):
    return templates.TemplateResponse("refund_policy.html", {"request": request})


@router.get("/payment/success")
def payment_success(request: Request):
    return templates.TemplateResponse("payment_success.html", {"request": request})


@router.get("/order/confirmation")
def order_confirmation(request: Request, order_id: str | None = None):
    return templates.TemplateResponse(
        "payment_success.html",
        {
            "request": request,
            "order_id": order_id,
        },
    )


@router.get("/payment/cancelled")
def payment_cancelled(request: Request):
    return templates.TemplateResponse("payment_cancelled.html", {"request": request})
