class PricingAnalyzer:
    """Pricing intelligence foundation."""

    def calculate(self, listings):
        prices = [x.get("price") for x in listings if isinstance(x, dict) and x.get("price") is not None]
        return {
            "average": sum(prices) / len(prices) if prices else None,
            "samples": len(prices)
        }
