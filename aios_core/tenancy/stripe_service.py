import os
import stripe
from typing import Dict, Any, Optional
from datetime import datetime

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

class StripeService:
    def __init__(self):
        self.prices = {
            "pro": os.getenv("STRIPE_PRICE_PRO", "price_pro_mock"),
            "enterprise": os.getenv("STRIPE_PRICE_ENT", "price_ent_mock")
        }

    def create_customer(self, email: str, name: str) -> str:
        customer = stripe.Customer.create(email=email, name=name)
        return customer.id

    def create_checkout_session(self, customer_id: str, price_id: str, success_url: str, cancel_url: str) -> str:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url

    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            
            if event["type"] == "checkout.session.completed":
                session = event["data"]["object"]
                return {"status": "success", "action": "subscription_created", "customer": session["customer"]}
            
            elif event["type"] == "customer.subscription.deleted":
                sub = event["data"]["object"]
                return {"status": "success", "action": "subscription_canceled", "customer": sub["customer"]}
                
            return {"status": "ignored", "type": event["type"]}
        except stripe.error.SignatureVerificationError:
            return {"status": "error", "message": "Invalid signature"}

stripe_service = StripeService()
