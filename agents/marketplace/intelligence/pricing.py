class PricingEngine:
    """OLX pricing analysis foundation."""

    def estimate_price(self, listing):
        return {
            "listing": listing,
            "estimated_price": None,
        }

    def compare_market(self, listing, market):
        return []
