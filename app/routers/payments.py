from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order, Payment
from app.config import get_settings

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/webhook")
async def payment_webhook(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    if not settings.stripe_webhook_secret:
        return {"status": "received", "note": "Webhook secret not configured"}

    try:
        import stripe
        event = stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret
        )
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = int(session.get("metadata", {}).get("order_id", 0))
        if order_id:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order and order.status == "pending":
                order.status = "paid"
                order.payment_reference = session.get("id", "")
                db.add(Payment(
                    order_id=order.id,
                    provider="stripe",
                    provider_payment_id=session.get("id", ""),
                    status="succeeded",
                    amount=order.total_amount,
                    currency=order.currency,
                ))

    elif event["type"] == "checkout.session.expired":
        session = event["data"]["object"]
        order_id = int(session.get("metadata", {}).get("order_id", 0))
        if order_id:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order and order.status == "pending":
                order.status = "failed"

    return {"status": "received"}
