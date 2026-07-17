import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Product, Order, OrderItem
from app.schemas import CheckoutRequest, CheckoutResponse

router = APIRouter(prefix="/api", tags=["checkout"])


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(
    req: CheckoutRequest,
    db: Session = Depends(get_db),
):
    order_items_data = []
    subtotal = Decimal("0")

    for item in req.items:
        product = db.query(Product).filter(
            Product.id == item.product_id,
            Product.status == "active",
        ).first()
        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"Product with id {item.product_id} not found or unavailable",
            )
        line_total = product.price * item.quantity
        subtotal += line_total
        order_items_data.append({
            "product_id": product.id,
            "product_name": product.name,
            "quantity": item.quantity,
            "unit_price": product.price,
            "total_price": line_total,
        })

    order = Order(
        customer_name=req.customer_name,
        customer_email=req.customer_email,
        status="confirmed",
        subtotal=subtotal,
        total_amount=subtotal,
        currency="USD",
    )
    db.add(order)
    db.flush()

    for oi in order_items_data:
        db.add(OrderItem(order_id=order.id, **oi))

    confirmation_url = f"/order/confirmation?order_id={order.id}"

    return CheckoutResponse(order_id=order.id, confirmation_url=confirmation_url)
