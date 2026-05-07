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

from pydantic import BaseModel

class CheckoutRequest(BaseModel):
    plan: str

@router.post("/stripe/checkout")
async def create_checkout(
    data: CheckoutRequest,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    plan = data.plan

    if plan not in PRICES or not PRICES[plan]:
        raise HTTPException(status_code=400, detail="Plano inválido")

    # Busca ou cria restaurante temporário
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.owner_id == owner.id
    ).first()

    if not restaurant:
        import re
        slug_base = re.sub(r'[^a-z0-9]', '', owner.email.split('@')[0].lower())
        slug = slug_base
        counter = 1
        while db.query(models.Restaurant).filter(models.Restaurant.slug == slug).first():
            slug = f"{slug_base}{counter}"
            counter += 1

        restaurant = models.Restaurant(
            owner_id=owner.id,
            name="Meu Restaurante",
            slug=slug,
            plan="trial",
            status="trial",
        )
        db.add(restaurant)
        db.commit()
        db.refresh(restaurant)

    try:
        print(f"SUCCESS URL: {FRONTEND_URL}/painel-admin.html?payment=success")
        print(f"CANCEL URL: {FRONTEND_URL}/planos.html?payment=cancelled")
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": PRICES[plan], "quantity": 1}],
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
        print(f"STRIPE ERROR: {e.user_message} | {e.code} | {str(e)}")
        raise HTTPException(status_code=400, detail=str(e.user_message))

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
