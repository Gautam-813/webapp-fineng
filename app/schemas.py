from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class ProductCategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    product_count: Optional[int] = None

    class Config:
        from_attributes = True


class ProductImageOut(BaseModel):
    id: int
    image_url: str
    alt_text: Optional[str] = None
    sort_order: int

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id: int
    name: str
    slug: str
    short_description: Optional[str] = None
    description: Optional[str] = None
    price: Decimal
    currency: str
    category: Optional[ProductCategoryOut] = None
    status: str
    platform: Optional[str] = None
    version: Optional[str] = None
    download_url: Optional[str] = None
    product_file_name: Optional[str] = None
    product_file_size: Optional[int] = None
    product_file_uploaded_at: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    images: list[ProductImageOut] = []
    featured: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class ProductListOut(BaseModel):
    id: int
    name: str
    slug: str
    short_description: Optional[str] = None
    price: Decimal
    currency: str
    category_name: Optional[str] = None
    category_slug: Optional[str] = None
    status: str
    platform: Optional[str] = None
    version: Optional[str] = None
    thumbnail_url: Optional[str] = None
    featured: bool = False

    class Config:
        from_attributes = True


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1)


class CartItemOut(BaseModel):
    item_id: int
    product_id: int
    name: str
    thumbnail_url: Optional[str] = None
    unit_price: Decimal
    quantity: int
    total: Decimal


class CartOut(BaseModel):
    cart_id: int
    items: list[CartItemOut]
    subtotal: Decimal


class CheckoutItem(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)


class CheckoutRequest(BaseModel):
    customer_name: str = Field(min_length=1, max_length=255)
    customer_email: EmailStr
    items: list[CheckoutItem] = Field(min_length=1)


class CheckoutResponse(BaseModel):
    order_id: int
    confirmation_url: str


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    subject: Optional[str] = None
    message: str = Field(min_length=1)
    service_type: str = "general"


class ContactOut(BaseModel):
    message: str


class ProjectRequestIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    project_type: Optional[str] = None
    budget_range: Optional[str] = None
    timeline: Optional[str] = None
    description: str = Field(min_length=1)


class ProjectRequestOut(BaseModel):
    message: str


class OrderItemOut(BaseModel):
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    customer_name: str
    customer_email: str
    status: str
    total_amount: Decimal
    currency: str
    items: list[OrderItemOut] = []
    created_at: datetime

    class Config:
        from_attributes = True


class AdminStats(BaseModel):
    total_products: int
    active_products: int
    total_orders: int
    confirmed_orders: int
    total_inquiries: int
    project_requests: int
    revenue: Decimal
