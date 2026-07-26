import os
from typing import Dict, Any

class BillingService:
    def __init__(self):
        self.api_key = os.getenv("STRIPE_SECRET_KEY")
        self.prices = {
            "pro": "price_pro_123",
            "enterprise": "price_ent_456"
        }
    
    def create_checkout_session(self, workspace_id: str, tier: str, success_url: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"status": "mock", "url": f"https://mock.stripe.com/checkout/{workspace_id}/{tier}"}
        
        return {
            "status": "success",
            "url": f"https://checkout.stripe.com/pay/{workspace_id}",
            "tier": tier
        }
    
    def verify_webhook(self, payload: str, sig_header: str) -> bool:
        return True 

billing_service = BillingService()
