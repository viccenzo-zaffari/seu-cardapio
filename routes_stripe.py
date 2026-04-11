from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_owner
import models
import stripe
import os

router = APIRouter(tags=["stripe"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRICES = {
    "mensal": os.getenv("STRIPE_PRICE_MENSAL"),
    "anual": os.getenv("STRIPE_PRICE_ANUAL"),
}

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://seu-cardapio-up.netlify.app")


# ── Criar sessão de checkout ──────────────────────────

@router.post("/stripe/checkout")
async def create_checkout(
    request: Request,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    body = await request.json()
    plan = body.get("plan")

    if plan not in PRICES or not PRICES[plan]:
        raise HTTPException(status_code=400, detail="Plano inválido")

    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.owner_id == owner.id
    ).first()

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": PRICES[plan],
                "quantity": 1,
            }],
            customer_email=owner.email,
            metadata={
                "owner_id": str(owner.id),
                "restaurant_id": str(restaurant.id),
                "plan": plan,
            },
            success_url=f"{FRONTEND_URL}/painel-admin.html?payment=success",
            cancel_url=f"{FRONTEND_URL}/planos.html?payment=cancelled",
        )
        return {"checkout_url": session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Webhook do Stripe ─────────────────────────────────

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception:
        raise HTTPException(status_code=400, detail="Webhook inválido")

    # Pagamento confirmado — ativa o plano
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        restaurant_id = session["metadata"].get("restaurant_id")
        plan = session["metadata"].get("plan")
        subscription_id = session.get("subscription")

        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.id == restaurant_id
        ).first()

        if restaurant:
            restaurant.plan = plan
            restaurant.status = "active"
            restaurant.stripe_subscription_id = subscription_id
            db.commit()

    # Assinatura cancelada ou pagamento falhou — suspende
    if event["type"] in ["customer.subscription.deleted", "invoice.payment_failed"]:
        subscription_id = event["data"]["object"].get("id") or event["data"]["object"].get("subscription")

        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.stripe_subscription_id == subscription_id
        ).first()

        if restaurant:
            restaurant.status = "suspended"
            db.commit()

    # Renovação bem-sucedida — mantém ativo
    if event["type"] == "invoice.paid":
        subscription_id = event["data"]["object"].get("subscription")

        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.stripe_subscription_id == subscription_id
        ).first()

        if restaurant:
            restaurant.status = "active"
            db.commit()

    return {"ok": True}


# ── Portal do cliente (gerenciar assinatura) ──────────

@router.post("/stripe/portal")
async def customer_portal(
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.owner_id == owner.id
    ).first()

    if not restaurant or not restaurant.stripe_subscription_id:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")

    try:
        subscription = stripe.Subscription.retrieve(restaurant.stripe_subscription_id)
        customer_id = subscription.customer

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{FRONTEND_URL}/painel-admin.html",
        )
        return {"portal_url": session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))