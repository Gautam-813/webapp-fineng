from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Cart, CartItem, Product
from app.schemas import CartItemIn, CartItemUpdate, CartOut, CartItemOut

router = APIRouter(prefix="/api/cart", tags=["cart"])


def _get_or_create_cart(db: Session, session_id: str) -> Cart:
    cart = db.query(Cart).filter(
        Cart.session_id == session_id,
        Cart.status == "active",
    ).first()
    if not cart:
        cart = Cart(session_id=session_id, status="active")
        db.add(cart)
        db.flush()
    return cart


@router.get("", response_model=CartOut)
def get_cart(session_id: str, db: Session = Depends(get_db)):
    cart = _get_or_create_cart(db, session_id)
    items = []
    subtotal = 0
    for ci in cart.items:
        total = ci.unit_price * ci.quantity
        subtotal += total
        items.append(
            CartItemOut(
                item_id=ci.id,
                product_id=ci.product_id,
                name=ci.product.name if ci.product else "",
                thumbnail_url=ci.product.thumbnail_url if ci.product else None,
                unit_price=ci.unit_price,
                quantity=ci.quantity,
                total=total,
            )
        )
    return CartOut(cart_id=cart.id, items=items, subtotal=subtotal)


@router.post("/items", status_code=201)
def add_cart_item(
    item: CartItemIn,
    session_id: str,
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == item.product_id, Product.status == "active").first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cart = _get_or_create_cart(db, session_id)

    existing = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == item.product_id,
    ).first()

    if existing:
        existing.quantity += item.quantity
    else:
        db.add(CartItem(
            cart_id=cart.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=product.price,
        ))
    return {"message": "Item added to cart"}


@router.put("/items/{item_id}")
def update_cart_item(
    item_id: int,
    update: CartItemUpdate,
    session_id: str,
    db: Session = Depends(get_db),
):
    cart = _get_or_create_cart(db, session_id)
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id,
    ).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    cart_item.quantity = update.quantity
    return {"message": "Cart item updated"}


@router.delete("/items/{item_id}", status_code=204)
def remove_cart_item(item_id: int, session_id: str, db: Session = Depends(get_db)):
    cart = _get_or_create_cart(db, session_id)
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id,
    ).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(cart_item)
    return None


@router.delete("", status_code=204)
def clear_cart(session_id: str, db: Session = Depends(get_db)):
    cart = _get_or_create_cart(db, session_id)
    for item in cart.items:
        db.delete(item)
    return None
