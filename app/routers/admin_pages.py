from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from app.routers.auth import get_current_user, require_admin
from app.models import User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/admin/login")
def admin_login(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.get("/admin", dependencies=[Depends(require_admin)])
def admin_dashboard(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "user": current_user})


@router.get("/admin/products", dependencies=[Depends(require_admin)])
def admin_products(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("admin/products.html", {"request": request, "user": current_user})


@router.get("/admin/categories", dependencies=[Depends(require_admin)])
def admin_categories(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("admin/categories.html", {"request": request, "user": current_user})


@router.get("/admin/customers", dependencies=[Depends(require_admin)])
def admin_customers(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("admin/customers.html", {"request": request, "user": current_user})


@router.get("/admin/products/new", dependencies=[Depends(require_admin)])
def admin_product_new(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("admin/product_form.html", {"request": request, "user": current_user, "product": None})


@router.get("/admin/products/{product_id}/edit", dependencies=[Depends(require_admin)])
def admin_product_edit(request: Request, product_id: int, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("admin/product_form.html", {"request": request, "user": current_user, "product_id": product_id, "product": None})


@router.get("/admin/orders", dependencies=[Depends(require_admin)])
def admin_orders(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("admin/orders.html", {"request": request, "user": current_user})


@router.get("/admin/inquiries", dependencies=[Depends(require_admin)])
def admin_inquiries(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("admin/inquiries.html", {"request": request, "user": current_user})
